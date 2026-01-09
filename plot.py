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

    with st.sidebar.expander("📌 ピーク自動検出の設定"):
        use_peak_finder = st.checkbox("ピークを自動でマークする", value=False)
        peak_prominence = st.number_input("感度 (Prominence)", value=50.0, step=10.0)
        peak_distance = st.number_input("最小間隔 (Distance)", value=10, step=1)

    # ---------------------------------------------------------
    # 4. 個別スタイル設定（強度倍率の追加）
    # ---------------------------------------------------------
    st.sidebar.header("3. Individual Style & Scale")
    individual_styles = {}
    for i, d in enumerate(all_data):
        # チェックボックスで表示・非表示を選択
        if st.sidebar.checkbox(d["name"], value=True, key=f"check_{d['name']}"):
            with st.sidebar.expander(f"🎨 設定: {d['name']}"):
                # 【新機能】強度倍率の入力
                scale = st.number_input("強度倍率 (Scale X)", value=1.0, min_value=0.0, step=0.1, key=f"scale_{i}")
                
                col_pick, lw_set = st.columns(2)
                with col_pick:
                    color = st.color_picker("色", value=mcolors.to_hex(plt.cm.tab10(i % 10)), key=f"c_{i}")
                with lw_set:
                    lw = st.slider("線の太さ", 0.5, 5.0, 1.5, key=f"lw_{i}")
                
                ls = st.selectbox("線種", ["-", "--", ":", "-."], key=f"ls_{i}")
                
                individual_styles[d['name']] = {"scale": scale, "color": color, "lw": lw, "ls": ls}
                selected_data.append(d)

# ---------------------------------------------------------
# 5. 表示範囲と全体設定
# ---------------------------------------------------------
if selected_data:
    st.sidebar.header("4. Global Display Settings")
    
    # 横軸範囲
    all_x_series = pd.concat([d["df"][x_col] for d in selected_data])
    x_range = st.sidebar.slider("横軸表示範囲 (2θ)", float(all_x_series.min()), float(all_x_series.max()), (float(all_x_series.min()), float(all_x_series.max())), step=0.01)

    y_offset = st.sidebar.number_input("積み上げオフセット (Y-offset)", value=0.0, step=100.0)
    use_interactive = st.sidebar.checkbox("インタラクティブモード", value=True)

    # ---------------------------------------------------------
    # 6. メイン表示エリア
    # ---------------------------------------------------------
    peak_results = []

    if use_interactive:
        fig = go.Figure()
        for i, d in enumerate(selected_data):
            style = individual_styles[d['name']]
            x = d["df"][x_col]
            # 強度をスケーリング
            y_scaled = d["df"][y_col] * style["scale"]
            y_disp = y_scaled + (i * y_offset)
            
            fig.add_trace(go.Scatter(
                x=x, y=y_disp, name=d["name"], mode='lines',
                line=dict(color=style["color"], width=style["lw"], dash=None if style["ls"]=="-" else "dash" if style["ls"]=="--" else "dot"),
                hovertemplate = '2θ: %{x:.3f}<br>Scaled Int: %{y:.1f}',
            ))

            if use_peak_finder:
                peaks, _ = find_peaks(y_scaled, prominence=peak_prominence, distance=peak_distance)
                p_x, p_y = x.iloc[peaks], y_disp.iloc[peaks]
                mask = (p_x >= x_range[0]) & (p_x <= x_range[1])
                
                fig.add_trace(go.Scatter(
                    x=p_x[mask], y=p_y[mask], mode='markers+text',
                    text=[f"{val:.2f}" for val in p_x[mask]], textposition="top center",
                    marker=dict(symbol='triangle-up', size=8), showlegend=False
                ))
                for p in peaks:
                    peak_results.append({"File": d["name"], "Scale": style["scale"], "2θ (deg)": x.iloc[p], "Intensity(Scaled)": y_scaled.iloc[p]})

        fig.update_layout(xaxis_title="2θ (deg.)", yaxis_title="Intensity (a.u.)", xaxis=dict(range=x_range), template="plotly_white", height=700)
        st.plotly_chart(fig, use_container_width=True)

    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        for i, d in enumerate(selected_data):
            style = individual_styles[d['name']]
            x = d["df"][x_col]
            y_scaled = d["df"][y_col] * style["scale"]
            y_disp = y_scaled + (i * y_offset)
            
            ax.plot(x, y_disp, label=f"{d['name']} (x{style['scale']})", 
                    color=style["color"], linewidth=style["lw"], linestyle=style["ls"])
            
            if use_peak_finder:
                peaks, _ = find_peaks(y_scaled, prominence=peak_prominence, distance=peak_distance)
                for p in peaks:
                    if x_range[0] <= x.iloc[p] <= x_range[1]:
                        ax.text(x.iloc[p], y_disp.iloc[p], f"{x.iloc[p]:.2f}", fontsize=8, ha='center', va='bottom')
                        peak_results.append({"File": d["name"], "Scale": style["scale"], "2θ (deg)": x.iloc[p], "Intensity(Scaled)": y_scaled.iloc[p]})
        
        ax.set_xlim(x_range)
        ax.set_xlabel("2θ (deg.)")
        ax.set_ylabel("Intensity (a.u.)")
        ax.legend(prop={'size': 8})
        st.pyplot(fig)

    if use_peak_finder and peak_results:
        st.subheader("📋 Detected Peaks List (Scaled)")
        st.dataframe(pd.DataFrame(peak_results))

elif uploaded_files:
    st.warning("表示データがありません。")
else:
    st.info("サイドバーからデータをアップロードしてください。")