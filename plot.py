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
# 関数：データ読み込み（全列保持）
# ---------------------------------------------------------
def load_xrd_data_full(uploaded_file):
    try:
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
        for i, line in enumerate(lines):
            parts = line.replace('\t', ',').split(',')
            if len(parts) >= 2:
                try:
                    float(parts[0].strip())
                    float(parts[1].strip())
                    data_start_idx = i
                    break
                except ValueError:
                    continue
        
        uploaded_file.seek(0)
        # 全ての列を読み込む
        df = pd.read_csv(uploaded_file, skiprows=data_start_idx, header=None, sep=None, engine='python')
        # 数値データのみを抽出
        df = df.apply(pd.to_numeric, errors='coerce').dropna(axis=0, how='any')
        # 列名が数字だと分かりにくいので "Col 0", "Col 1"... とする
        df.columns = [f"Column {i}" for i in range(df.shape[1])]
        return df
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {e}")
        return None

# ---------------------------------------------------------
# サイドバー: 1. データインポート
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
        df = load_xrd_data_full(f)
        if df is not None:
            all_data.append({"name": f.name, "df": df})

# ---------------------------------------------------------
# サイドバー: 2. 列の選択（新規追加機能）
# ---------------------------------------------------------
x_col_name = ""
y_col_name = ""

if all_data:
    st.sidebar.header("2. Column Selection")
    # 最初のファイルの列構成を基準に選択肢を作成
    sample_df = all_data[0]["df"]
    col_options = sample_df.columns.tolist()
    
    x_col_name = st.sidebar.selectbox("X軸に使用する列", col_options, index=0)
    y_col_name = st.sidebar.selectbox("Y軸に使用する列", col_options, index=1 if len(col_options) > 1 else 0)

    st.sidebar.subheader("表示するファイル")
    selected_data = []
    for d in all_data:
        if st.sidebar.checkbox(d["name"], value=True, key=f"check_{d['name']}"):
            selected_data.append(d)
else:
    selected_data = []

# ---------------------------------------------------------
# サイドバー: 3. 全体設定
# ---------------------------------------------------------
st.sidebar.header("3. Global Style")
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
# サイドバー: 4. 個別スタイル設定
# ---------------------------------------------------------
individual_styles = {}
if selected_data:
    st.sidebar.header("4. Individual Style")
    for i, d in enumerate(selected_data):
        with st.sidebar.expander(f"設定: {d['name']}"):
            default_hex = mcolors.to_hex(plt.cm.tab10(i % 10))
            col = st.color_picker("色", value=default_hex, key=f"cp_{i}")
            lw = st.slider("線の太さ", 0.5, 5.0, 1.5, key=f"lw_{i}")
            ls = st.selectbox("線種", ["-", "--", ":", "-."], key=f"ls_{i}")
            individual_styles[d['name']] = {"color": col, "lw": lw, "ls": ls}

# ---------------------------------------------------------
# メイン画面: グラフプレビュー (中央80%)
# ---------------------------------------------------------
if selected_data:
    _, main_col, _ = st.columns([0.1, 0.8, 0.1])
    
    with main_col:
        st.subheader("Graph Preview")
        
        plt.rcParams['font.family'] = font_family
        plt.rcParams['font.size'] = base_font_size
        plt.rcParams['xtick.direction'] = tick_dir
        plt.rcParams['ytick.direction'] = tick_dir

        fig, ax = plt.subplots(figsize=(10, 6))
        
        for i, d in enumerate(selected_data):
            style = individual_styles[d['name']]
            # 指定された列名を使用してプロット
            ax.plot(
                d["df"][x_col_name], 
                d["df"][y_col_name] + (i * y_offset),
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
        
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
        st.download_button("画像を保存 (PNG)", buf.getvalue(), "plot.png", "image/png")

else:
    st.info("サイドバーからXRDデータをアップロードしてください。")

# ---------------------------------------------------------
# 画面下部: 使い方
# ---------------------------------------------------------
st.divider()
st.subheader("📖 使い方")
st.markdown("""
1. **データの選択**: サイドバーの「Column Selection」で、X軸とY軸に使う列を指定してください。
   - 例えば、1列目に角度、2列目に強度がある場合は、X=Column 0, Y=Column 1 を選びます。
2. **プレビュー**: 中央の画面（幅80%）にグラフが表示されます。
3. **スタイル変更**: 個別設定で、各データの線の種類や色を調整できます。
""")