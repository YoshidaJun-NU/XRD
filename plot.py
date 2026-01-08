import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.colors as mcolors
import numpy as np
import io
import os

# ---------------------------------------------------------
# 設定とタイトル
# ---------------------------------------------------------
st.set_page_config(page_title="XRD/Data Plotter Pro", layout="wide")

st.title("Scientific Multi-Plotter")

# ---------------------------------------------------------
# サイドバー: 1. ファイルアップロードとデータ形式
# ---------------------------------------------------------
st.sidebar.header("1. Data Import")
uploaded_files = st.sidebar.file_uploader(
    "ファイルをアップロード (複数可)", 
    type=['csv', 'txt', '2ta', 'dat', 'xy'], 
    accept_multiple_files=True
)

use_header = st.sidebar.checkbox("File has Header row?", value=False)
header_row = 0
if use_header:
    header_row = st.sidebar.number_input("Header Row Index", min_value=0, value=0)

# ---------------------------------------------------------
# 2. データの読み込みと選択
# ---------------------------------------------------------
all_data = []
if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            # 各種エンコーディングを試行
            content = uploaded_file.read()
            uploaded_file.seek(0)
            df = None
            for enc in ['utf-8', 'cp932', 'shift_jis']:
                try:
                    uploaded_file.seek(0)
                    # 区切り文字を自動推定 (sep=None)
                    df = pd.read_csv(uploaded_file, sep=None, header=header_row if use_header else None, 
                                     engine='python', encoding=enc)
                    break
                except:
                    continue
            
            if df is not None:
                # 数値データのみを抽出
                df = df.apply(pd.to_numeric, errors='coerce').dropna()
                if not df.empty:
                    all_data.append({"name": uploaded_file.name, "df": df})
        except Exception as e:
            st.sidebar.error(f"Error loading {uploaded_file.name}: {e}")

# ファイル選択機能
if all_data:
    file_names = [d["name"] for d in all_data]
    selected_names = st.sidebar.multiselect("表示するファイルを選択", file_names, default=file_names)
    plot_data = [d for d in all_data if d["name"] in selected_names]
else:
    plot_data = []

# ---------------------------------------------------------
# サイドバー: 3. グラフスタイル設定 (全体)
# ---------------------------------------------------------
st.sidebar.header("2. Global Style")
with st.sidebar.expander("文字・フォント設定"):
    font_family = st.selectbox("Font Family", ["sans-serif", "serif", "monospace", "DejaVu Sans"])
    base_font_size = st.slider("Base Font Size", 8, 30, 14)
    label_font_size = st.slider("Label Font Size", 8, 30, 16)
    tick_direction = st.radio("Tick Direction", ["in", "out"], index=0, horizontal=True)

with st.sidebar.expander("軸と凡例"):
    x_label_text = st.text_input("X-axis Label", "2θ (deg.)")
    y_label_text = st.text_input("Y-axis Label", "Intensity (a.u.)")
    show_legend = st.checkbox("凡例を表示する", value=True)
    offset_val = st.number_input("Y-offset (積み上げ)", value=0.0, step=100.0)

# ---------------------------------------------------------
# サイドバー: 4. 個別プロット設定
# ---------------------------------------------------------
individual_styles = {}
if plot_data:
    st.sidebar.header("3. Individual Style")
    for i, item in enumerate(plot_data):
        with st.sidebar.expander(f"Style: {item['name']}"):
            # plt.cm.tab10(i % 10) を mcolors.to_hex で変換する
            
            default_color = mcolors.to_hex(plt.cm.tab10(i % 10))
            
            color = st.color_picker(f"Color", key=f"col_{i}", value=default_color)
            lw = st.slider(f"Line Width", 0.5, 5.0, 1.5, key=f"lw_{i}")
            ls = st.selectbox(f"Line Style", ["- (実線)", "-- (破線)", ": (点線)", "-. (一点鎖線)"], key=f"ls_{i}")
            individual_styles[item['name']] = {
                "color": color, 
                "lw": lw, 
                "ls": ls.split()[0]
            }

# ---------------------------------------------------------
# メイン画面: グラフプレビュー (中央80%幅)
# ---------------------------------------------------------
if plot_data:
    # 左右に1割ずつの余白を作り、中央に8割のメインカラムを配置
    spacer_left, main_col, spacer_right = st.columns([0.1, 0.8, 0.1])
    
    with main_col:
        st.subheader("Graph Preview")
        
        # Matplotlib設定の反映
        plt.rcParams['font.family'] = font_family
        plt.rcParams['font.size'] = base_font_size
        plt.rcParams['xtick.direction'] = tick_direction
        plt.rcParams['ytick.direction'] = tick_direction

        fig, ax = plt.subplots(figsize=(10, 6))
        
        for i, item in enumerate(plot_data):
            df = item["df"]
            style = individual_styles[item['name']]
            
            # データの1列目をX、2列目をYとしてプロット (積み上げオフセット適用)
            ax.plot(
                df.iloc[:, 0], 
                df.iloc[:, 1] + (i * offset_val),
                label=item["name"],
                color=style["color"],
                linewidth=style["lw"],
                linestyle=style["ls"]
            )
        
        ax.set_xlabel(x_label_text, fontsize=label_font_size)
        ax.set_ylabel(y_label_text, fontsize=label_font_size)
        ax.tick_params(top=True, right=True)
        
        if show_legend:
            ax.legend(frameon=False)
            
        st.pyplot(fig)

        # 保存用
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
        st.download_button("PNG画像をダウンロード", buf.getvalue(), "plot.png", "image/png")
else:
    st.info("サイドバーからファイルをアップロードしてください。")

# ---------------------------------------------------------
# 画面下部: 使い方の説明
# ---------------------------------------------------------
st.markdown("---")
st.subheader("📖 使い方")
st.markdown("""
1. **データの読み込み**: 画面左側のサイドバーからファイルをアップロードしてください。
2. **データの選択**: アップロードしたファイルの中から、プロットしたいものにチェックを入れます。
3. **スタイルの調整**:
    - **Global Style**: フォントサイズや目盛の向きなど、グラフ全体の雰囲気を設定します。
    - **Individual Style**: 各グラフ線の色や太さを個別に設定します。
    - **Y-offset**: 複数のグラフを縦に並べて比較したい場合に数値を入力します。
4. **保存**: プレビュー下のボタンから高解像度画像を保存できます。
""")