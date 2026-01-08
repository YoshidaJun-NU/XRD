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
# 関数：データ読み込み（エラー耐性を強化）
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
            # カンマ、タブ、スペースを正規化して分割
            parts = line.replace('\t', ',').replace(' ', ',').split(',')
            parts = [p for p in parts if p.strip()] # 空要素削除
            if len(parts) >= 2:
                try:
                    float(parts[0].strip())
                    float(parts[1].strip())
                    data_start_idx = i
                    break
                except ValueError:
                    continue
        
        uploaded_file.seek(0)
        # 全ての列を読み込み
        df = pd.read_csv(uploaded_file, skiprows=data_start_idx, header=None, sep=None, engine='python')
        # 数値データのみを抽出
        df = df.apply(pd.to_numeric, errors='coerce').dropna(axis=0, how='any')
        
        if df.empty:
            return None
            
        # 列名を "Column 0", "Column 1"... で統一
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
# サイドバー: 2. 列の選択（エラー対策版）
# ---------------------------------------------------------
x_col_name = ""
y_col_name = ""

if all_data:
    st.sidebar.header("2. Column Selection")
    
    # 全ファイルの中で「最大で何列あるか」を調べて選択肢を作る
    max_cols = max([d["df"].shape[1] for d in all_data])
    col_options = [f"Column {i}" for i in range(max_cols)]
    
    x_col_name = st.sidebar.selectbox("X軸に使用する列", col_options, index=0)
    y_col_name = st.sidebar.selectbox("Y軸に使用する列", col_options, index=1 if max_cols > 1 else 0)

    st.sidebar.subheader("表示するファイル")
    selected_data = []
    for d in all_data:
        # チェックボックス
        if st.sidebar.checkbox(d["name"], value=True, key=f"check_{d['name']}"):
            # 選択された列がこのファイルに存在するかチェック
            if x_col_name in d["df"].columns and y_col_name in d["df"].columns:
                selected_data.append(d)
            else:
                st.sidebar.warning(f"⚠️ {d['name']} には選択された列がありません（スキップされます）")
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
            # ここで安全にデータを取得
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

elif uploaded_files:
    st.warning("表示できるデータがありません。選択した列（Column）がファイル内に存在するか確認してください。")
else:
    st.info("サイドバーからデータをアップロードしてください。")

# ---------------------------------------------------------
# 画面下部: 使い方
# ---------------------------------------------------------
st.divider()
st.subheader("📖 使い方")
st.markdown("""
- **KeyErrorの対策**: アップロードされた全てのファイルの中で最も多い列数を基準に選択肢を表示します。
- **自動スキップ**: 選択した列が存在しないファイルがある場合、エラーで止まらずにそのファイルだけをスキップし、サイドバーに警告を表示します。
""")