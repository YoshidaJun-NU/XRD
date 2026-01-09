import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import io
from scipy.signal import find_peaks
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. ページ設定
# ---------------------------------------------------------
st.set_page_config(page_title="XRD Plotter Pro", layout="wide")
st.title("🔬 XRD Multi-Plotter Pro")

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
# 3. サイドバー: インポート & 設定
# ---------------------------------------------------------
st.sidebar.header("1. Data Import")
uploaded_files = st.sidebar.file_uploader("ファイルをアップロード", type=['csv', 'txt', '2ta', 'dat', 'xy'], accept_multiple_files=True)

all_data = []
if uploaded_files:
    for f in uploaded_files:
        df = load_xrd_data_full(f)
        if df is not None:
            all_data.append({"name": f.name, "df": df})

selected_data = []
if all_data:
    st.sidebar.header("2. Selection & Peaks")
    max_cols = max([d["df"].shape[1] for d in all_data])
    col_options = [f"Column {i}" for i in range(max_cols)]
    x_col = st.sidebar.selectbox("X軸 (2θ)", col_options, index=0)
    y_col = st.sidebar.selectbox("Y軸 (Intensity)", col_options, index=1 if max_cols > 1 else 0)

    # ピーク検出設定
    with st.sidebar.expander("📌 ピーク自動検出の設定"):
        use_peak_finder = st.checkbox("ピークを自動でマークする", value=False)
        peak_prominence = st.number_input("感度 (Prominence)", value=50.0, step=10.0)
        peak_distance = st.number_input("最小間隔 (Distance)", value=10, step=1)

    # 表示するファイルの選択
    for d in all_data:
        if st.sidebar.checkbox(d["name"], value=True, key=f"check_{d['name']}"):
            if x_col in d["df"].columns and y_col in d["df"].columns:
                selected_data.append(d)

# ---------------------------------------------------------
# 4. サイドバー: 表示範囲とスタイル
# ---------------------------------------------------------
if selected_data:
    st.sidebar.header("3. Graph Display Range")
    
    # 【機能追加】横軸の表示範囲を設定するための計算
    all_x_series = pd.concat([d["df"][x_col] for d in selected_data])
    global_x_min = float(all_x_series.min())
    global_x_max = float(all_x_series.max())

    # 表示範囲指定スライダー
    x_range = st.sidebar.slider(
        "横軸表示範囲 (2θ)", 
        min_value=global_x_min, 
        max_value=global_x_max, 
        value=(global_x_min, global_x_max),
        step=0.01
    )

    st.sidebar.header("4. Other Settings")
    use_interactive = st.sidebar.checkbox("インタラクティブモード", value=True)
    y_offset = st.sidebar.number_input("積み上げオフセット", value=0.0, step=100.0)

    # ---------------------------------------------------------
    # 5. メイン表示エリア
    # ---------------------------------------------------------
    peak_results = [] # ピーク情報を格納

    if use_interactive:
        # --- Plotly (インタラクティブ) ---
        fig = go.Figure()
        for i, d in enumerate(selected_data):
            x = d["df"][x_col]
            y = d["df"][y_col]
            y_disp = y + (i * y_offset)
            
            fig.add_trace(go.Scatter(
                x=x, y=y_disp, name=d["name"], mode='lines',
                hovertemplate = '2θ: %{x:.3f}<br>Int: %{text:.1f}',
                text = y 
            ))

            if use_peak_finder:
                peaks, _ = find_peaks(y, prominence=peak_prominence, distance=peak_distance)
                # 表示範囲内のピークのみ抽出
                p_x = x.iloc[peaks]
                p_y = y_disp.iloc[peaks]
                mask = (p_x >= x_range[0]) & (p_x <= x_range[1])
                
                fig.add_trace(go.Scatter(
                    x=p_x[mask], y=p_y[mask],
                    mode='markers+text',
                    text=[f"{val:.2f}" for val in p_x[mask]],
                    textposition="top center",
                    marker=dict(symbol='triangle-up', size=10),
                    name=f"Peaks ({d['name']})",
                    hoverinfo='skip'
                ))
                for p in peaks:
                    peak_results.append({"File": d["name"], "2θ (deg)": x.iloc[p], "Intensity": y.iloc[p]})

        fig.update_layout(
            xaxis_title="2θ (deg.)", 
            yaxis_title="Intensity (a.u.)",
            xaxis=dict(range=[x_range[0], x_range[1]]), # 横軸範囲の反映
            hovermode="x unified", height=600, template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        # --- Matplotlib (静的・保存用) ---
        fig, ax = plt.subplots(figsize=(10, 6))
        for i, d in enumerate(selected_data):
            x, y = d["df"][x_col], d["df"][y_col]
            y_disp = y + (i * y_offset)
            ax.plot(x, y_disp, label=d["name"])
            
            if use_peak_finder:
                peaks, _ = find_peaks(y, prominence=peak_prominence, distance=peak_distance)
                for p in peaks:
                    if x_range[0] <= x.iloc[p] <= x_range[1]: # 範囲内のみ表示
                        ax.text(x.iloc[p], y_disp.iloc[p], f"{x.iloc[p]:.2f}", 
                                fontsize=9, verticalalignment='bottom', horizontalalignment='center')
                        peak_results.append({"File": d["name"], "2θ (deg)": x.iloc[p], "Intensity": y.iloc[p]})
        
        ax.set_xlim(x_range) # 横軸範囲の反映
        ax.set_xlabel("2θ (deg.)")
        ax.set_ylabel("Intensity (a.u.)")
        ax.legend()
        st.pyplot(fig)

    # ピークリストの表示
    if use_peak_finder and peak_results:
        st.subheader("📋 Detected Peaks List")
        res_df = pd.DataFrame(peak_results)
        st.dataframe(res_df.style.format({"2θ (deg)": "{:.3f}", "Intensity": "{:.1f}"}))

elif uploaded_files:
    st.warning("表示データがありません。")
else:
    st.info("サイドバーからデータをアップロードしてください。")