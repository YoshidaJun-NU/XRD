import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import io

# ---------------------------------------------------------
# ページ設定
# ---------------------------------------------------------
st.set_page_config(page_title="XRD Plotter Pro", layout="wide")
st.title("XRD Multi-Plotter")

# ---------------------------------------------------------
# 関数：データ開始行の自動検出
# ---------------------------------------------------------
def load_xrd_data(uploaded_file):
    """
    ファイル内の数値データが始まる行を自動で見つけ、Pandas DataFrameとして返す。
    """
    try:
        # 文字コードを試行しながら読み込み
        content = ""
        for enc in ['utf-8', 'cp932', 'shift_jis']:
            try:
                uploaded_file.seek(0)
                content = uploaded_file.read().decode(enc)
                break
            except:
                continue
        
        if not content:
            return None

        lines = content.splitlines()
        data_start_idx = 0
        
        # 数値が2つ並んでいる行をデータ開始行と判定
        for i, line in enumerate(lines):
            # カンマまたはタブで分割
            parts = line.replace('\t', ',').split(',')
            if len(parts) >= 2:
                try:
                    float(parts[0].strip())
                    float(parts[1].strip())
                    data_start_idx = i
                    break
                except ValueError:
                    continue
        
        # 判定された行から読み込み
        uploaded_file.seek(0)
        # 区切り文字を自動判定
        df = pd.read_csv(uploaded_file, skiprows=data_start_idx, header=None, sep=None, engine='python')
        # 数値以外の列が含まれる場合を考慮し、最初の2列を X, Y とする
        df = df.apply(pd.to_numeric, errors='coerce').dropna()
        df = df.iloc[:, :2]
        df.columns = ['x', 'y']
        return df
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {e}")
        return None

# ---------------------------------------------------------
# サイドバー: 1. ファイル読み込み（左側）
# ---------------------------------------------------------
st.sidebar.header("1. Data Import")
uploaded_files = st.sidebar.file_uploader(
    "ファイルをアップロード", 
    type=['csv', 'txt', '2ta', 'dat', 'xy'], 
    accept_multiple_files=True
)

all_data = []
if uploaded_files:
    for f in uploaded_files:
        df = load_xrd_data(f)
        if df is not None:
            all_data.append({"name": f.name, "df": df})

# ファイルの選択
selected_data = []
if all_data:
    st.sidebar.subheader("表示するデータを選択")
    for d in all_data:
        if st.sidebar.checkbox(d["name"], value=True):
            selected_data.append(d)

# ---------------------------------------------------------
# サイドバー: 2. 全体設定
# ---------------------------------------------------------
st.sidebar.header("2. Global Style")
with st.sidebar.expander("文字・フォント設定"):
    font_family = st.selectbox("Font Family", ["sans-serif", "serif", "monospace"])
    base_font_size = st.slider("基本文字サイズ", 8, 30, 14)
    label_font_size = st.slider("軸ラベルサイズ", 8, 40, 18)
    tick_dir = st.radio("目盛の向き", ["in", "out"], index=0, horizontal=True)

with st.sidebar.expander("軸・凡例の設定"):
    x_label = st.text_input("X軸ラベル", "2θ (deg.)")
    y_label = st.text_input("Y軸ラベル", "Intensity (a.u.)")
    show_legend = st.checkbox("凡例を表示する", value=True)
    y_offset = st.number_input("Y軸オフセット (積み上げ)", value=0.0, step=100.0)

# ---------------------------------------------------------
# サイドバー: 3. 個別スタイル設定
# ---------------------------------------------------------
individual_styles = {}
if selected_data:
    st.sidebar.header("3. Individual Style")
    for i, d in enumerate(selected_data):
        with st.sidebar.expander(f"設定: {d['name']}"):
            # HEXカラーコードの修正を適用
            default_hex = mcolors.to_hex(plt.cm.tab10(i % 10))
            col = st.color_picker("色", value=default_hex, key=f"cp_{i}")
            lw = st.slider("線の太さ", 0.5, 5.0, 1.5, key=f"lw_{i}")
            ls = st.selectbox("線種", ["-", "--", ":", "-."], key=f"ls_{i}")
            individual_styles[d['name']] = {"color": col, "lw": lw, "ls": ls}

# ---------------------------------------------------------
# メイン画面: グラフプレビュー (中央80%)
# ---------------------------------------------------------
if selected_data:
    # 左右に10%の余白を作り、中央80%のカラムを使用
    _, main_col, _ = st.columns([0.1, 0.8, 0.1])
    
    with main_col:
        st.subheader("Graph Preview")
        
        # Matplotlibのスタイル適用
        plt.rcParams['font.family'] = font_family
        plt.rcParams['font.size'] = base_font_size
        plt.rcParams['xtick.direction'] = tick_dir
        plt.rcParams['ytick.direction'] = tick_dir

        fig, ax = plt.subplots(figsize=(10, 6))
        
        for i, d in enumerate(selected_data):
            style = individual_styles[d['name']]
            # オフセットを適用してプロット
            ax.plot(
                d["df"]['x'], 
                d["df"]['y'] + (i * y_offset),
                label=d["name"],
                color=style["color"],
                linewidth=style["lw"],
                linestyle=style["ls"]
            )
        
        ax.set_xlabel(x_label, fontsize=label_font_size)
        ax.set_ylabel(y_label, fontsize=label_font_size)
        ax.tick_params(top=True, right=True)
        
        if show_legend:
            ax.legend(frameon=False)
        
        st.pyplot(fig)
        
        # 画像保存
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
        st.download_button("画像を保存 (PNG)", buf.getvalue(), "plot.png", "image/png")

else:
    st.info("サイドバーからXRDデータをアップロードしてください。")

# ---------------------------------------------------------
# 画面下部: 使い方
# ---------------------------------------------------------
st.divider()
with st.expander("📖 使い方 / 対応形式について"):
    st.markdown(f"""
    ### 読み込み可能な形式
    - **{uploaded_files[0].name if uploaded_files else 'I7_C1_...csv'}** のような、冒頭に条件が書かれたCSV形式に対応。
    - カンマ区切り、タブ区切り、スペース区切りのファイルを自動判別します。
    - 数値が2列並んでいる箇所をデータ開始位置として自動検出します。

    ### 操作方法
    1. **左側サイドバー**: ファイルを複数一括でアップロードできます。
    2. **表示選択**: 読み込んだファイル名の下のチェックボックスで、表示・非表示を切り替えられます。
    3. **スタイルの調整**: グラフ全体のフォントや、各データごとの色・線種・太さを変更できます。
    4. **積み上げ表示**: `Y軸オフセット` を入力すると、データを縦にずらして比較しやすくなります。
    """)