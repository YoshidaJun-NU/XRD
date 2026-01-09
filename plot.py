import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import io

# ---------------------------------------------------------
# 1. ページ設定
# ---------------------------------------------------------
st.set_page_config(page_title="XRD Plotter Pro", layout="wide")
st.title("📉 XRD Multi-Plotter Pro")

# ---------------------------------------------------------
# 2. 関数：データ読み込み
# ---------------------------------------------------------
def load_xrd_data_full(uploaded_file):
    try:
        content = ""
        for enc in ['utf-8', 'cp932', 'shift_jis']:
            try:
                uploaded_file.seek(0)
                content = uploaded_file.read().decode(enc)
                break
            except: continue
        
        if not content: return None

        lines = content.splitlines()
        data_start_idx = 0
        for i, line in enumerate(lines):
            parts = line.replace('\t', ',').replace(' ', ',').split(',')
            parts = [p for p in parts if p.strip()]
            if len(parts) >= 2:
                try:
                    float(parts[0].strip()); float(parts[1].strip())
                    data_start_idx = i
                    break
                except ValueError: continue
        
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, skiprows=data_start_idx, header=None, sep=None, engine='python')
        df = df.apply(pd.to_numeric, errors='coerce').dropna(axis=0, how='any')
        
        if df.empty: return None
        df.columns = [f"Column {i}" for i in range(df.shape[1])]
        return df
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {e}")
        return None

# ---------------------------------------------------------
# 3. サイドバー: データインポート & 列選択
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

x_col_name, y_col_name = "Column 0", "Column 1"
selected_data = []

if all_data:
    st.sidebar.header("2. Selection & Range")
    max_cols = max([d["df"].shape[1] for d in all_data])
    col_options = [f"Column {i}" for i in range(max_cols)]
    x_col_name = st.sidebar.selectbox("X軸に使用する列", col_options, index=0)
    y_col_name = st.sidebar.selectbox("Y軸に使用する列", col_options, index=1 if max_cols > 1 else 0)

    # 表示ファイルの選択
    for d in all_data:
        if st.sidebar.checkbox(d["name"], value=True, key=f"check_{d['name']}"):
            if x_col_name in d["df"].columns and y_col_name in d["df"].columns:
                selected_data.append(d)

# ---------------------------------------------------------
# 4. サイドバー: スタイル & 軸の表示範囲設定
# ---------------------------------------------------------
if selected_data:
    st.sidebar.header("3. Global & Axis Style")
    
    # --- 【新機能】表示範囲の設定 ---
    with st.sidebar.expander("軸の表示範囲 (Range)", expanded=True):
        # データ全体の最小・最大を取得
        all_x = pd.concat([d["df"][x_col_name] for d in selected_data])
        y_offset_val = st.number_input("積み上げオフセット (Y-offset)", value=0.0, step=100.0)
        
        all_y_list = []
        for i, d in enumerate(selected_data):
            all_y_list.append(d["df"][y_col_name] + (i * y_offset_val))
        all_y = pd.concat(all_y_list)

        x_min, x_max = float(all_x.min()), float(all_x.max())
        y_min, y_max = float(all_y.min()), float(all_y.max())

        # 範囲指定スライダー
        xlim = st.slider("X軸範囲", x_min, x_max, (x_min, x_max))
        ylim = st.slider("Y軸範囲", y_min * 0.9, y_max * 1.1, (y_min, y_max))

    with st.sidebar.expander("文字・フォント・目盛"):
        font_family = st.selectbox("Font Family", ["sans-serif", "serif", "monospace"])
        base_size = st.slider("基本サイズ", 8, 30, 14)
        label_size = st.slider("軸ラベルサイズ", 8, 40, 18)
        tick_dir = st.radio("目盛向き", ["in", "out"], index=0, horizontal=True)
        show_grid = st.checkbox("目盛り線を表示", value=False)

    # --- 個別スタイル設定 ---
    st.sidebar.header("4. Individual Plot Style")
    individual_styles = {}
    for i, d in enumerate(selected_data):
        with st.sidebar.expander(f"🎨 {d['name']}"):
            c1, c2 = st.columns(2)
            with c1:
                color = st.color_picker("色", value=mcolors.to_hex(plt.cm.tab10(i % 10)), key=f"c_{i}")
                lw = st.slider("太さ", 0.5, 10.0, 1.5, key=f"lw_{i}")
            with c2:
                ls = st.selectbox("線種", ["-", "--", ":", "-.", "None"], key=f"ls_{i}")
                marker = st.selectbox("点", ["None", "o", "s", "x", "."], key=f"m_{i}")
            
            individual_styles[d['name']] = {"color": color, "lw": lw, "ls": ls, "marker": marker}

# ---------------------------------------------------------
# 5. メイン表示エリア
# ---------------------------------------------------------
if selected_data:
    st.subheader("Graph Preview")
    
    # Plot設定
    plt.rcParams['font.family'] = font_family
    plt.rcParams['font.size'] = base_size
    plt.rcParams['xtick.direction'] = tick_dir
    plt.rcParams['ytick.direction'] = tick_dir

    fig, ax = plt.subplots(figsize=(10, 6))
    
    for i, d in enumerate(selected_data):
        style = individual_styles[d['name']]
        ax.plot(
            d["df"][x_col_name], 
            d["df"][y_col_name] + (i * y_offset_val),
            label=d["name"],
            color=style["color"],
            linewidth=style["lw"],
            linestyle=style["ls"],
            marker=style["marker"],
            markevery=max(1, len(d["df"])//20) if style["marker"] != "None" else None
        )
    
    # 軸・範囲の設定反映
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_xlabel("2θ (deg.)", fontsize=label_size)
    ax.set_ylabel("Intensity (a.u.)", fontsize=label_size)
    ax.tick_params(top=True, right=True)
    if show_grid: ax.grid(True, linestyle='--', alpha=0.6)
    if st.sidebar.checkbox("凡例を表示", value=True):
        ax.legend(frameon=False)
    
    st.pyplot(fig)
    
    # ダウンロード
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    st.download_button("💾 画像を保存 (PNG)", buf.getvalue(), "xrd_plot.png", "image/png")

elif uploaded_files:
    st.warning("表示データがありません。列設定を確認してください。")
else:
    st.info("サイドバーからXRDデータをアップロードしてください。")