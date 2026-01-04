import streamlit as st
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
import plotly.graph_objects as go
import plotly.express as px
import os

# --- Page Configuration ---
st.set_page_config(page_title="LCANA (AI ver.)", layout="wide")

# --- Constants ---
WAVELENGTH = 1.5418  # Cu K-alpha
DEFAULT_FILE_NAME = "demo.txt"

# --- Functions ---
def theta_to_d(two_theta):
    """Calculate d-value (A) from 2theta (deg) using Bragg's Law: lambda = 2d sin(theta)"""
    theta_rad = np.deg2rad(two_theta / 2)
    with np.errstate(divide='ignore'):
        d = WAVELENGTH / (2 * np.sin(theta_rad))
    return d

def get_theoretical_ratios(lattice_type):
    """Return theoretical d-value ratios for different lattice types"""
    if lattice_type == "Lamellar":
        return np.array([1, 1/2, 1/3, 1/4, 1/5])
    elif lattice_type == "Hexagonal (Columnar)":
        return np.array([1, 1/np.sqrt(3), 1/2, 1/np.sqrt(7), 1/3])
    elif lattice_type == "Tetragonal (Columnar)":
        return np.array([1, 1/np.sqrt(2), 1/2, 1/np.sqrt(5), 1/3])
    return np.array([])

# --- Sidebar (Settings) ---
st.sidebar.header("ファイル読み込み設定")

# 1. File Type Selection
file_type = st.sidebar.radio(
    "ファイル形式を選択",
    ('txt (スペースまたはタブ区切り)', 'csv (カンマ区切り)')
)

# 2. File Uploader
uploaded_file = st.sidebar.file_uploader("XRDデータをアップロード", type=['csv', 'txt'])

# 3. Header Skip Setting
header_rows = st.sidebar.number_input("スキップする行数 (ヘッダー除去)", value=0, min_value=0)

# --- Main Application ---
st.title("LCANA (AI ver.)")
st.markdown(f"""
### 使い方
1. ファイルをアップロード（またはデフォルトの `{DEFAULT_FILE_NAME}` を使用）
2. 自動でピークを探してテーブル出力
3. プロット＆ピーク表示
4. 下部の解析ツールで格子定数を検討
""")

# データ読み込みロジック
df = None
using_default_file = False

if uploaded_file is not None:
    # ユーザーがファイルをアップロードした場合
    try:
        if 'txt' in file_type:
            df = pd.read_csv(uploaded_file, skiprows=header_rows, header=None, sep=None, engine='python')
        else:
            df = pd.read_csv(uploaded_file, skiprows=header_rows, header=None, sep=',')
        st.success(f"ファイルをアップロードしました: {uploaded_file.name}")
    except Exception as e:
        st.error(f"読み込みエラー: {e}")
elif os.path.exists(DEFAULT_FILE_NAME):
    # アップロードがなく、デフォルトファイルが存在する場合
    try:
        df = pd.read_csv(DEFAULT_FILE_NAME, skiprows=0, header=None, sep=None, engine='python')
        using_default_file = True
        st.info(f"📂 モデルデータ '{DEFAULT_FILE_NAME}' をロードしました。")
    except Exception as e:
        st.error(f"モデルデータの読み込みに失敗しました: {e}")

# --- メイン処理 ---
if df is not None:
    st.write("▼ データの先頭 (Raw Data Preview)")
    st.dataframe(df.head())

    # --- 2. Column Assignment ---
    st.sidebar.markdown("---")
    st.sidebar.header("列の割り当て")
    
    columns = df.columns.tolist()
    
    if len(columns) < 2:
        st.error("エラー: データに列が2つ以上見つかりません。")
        st.stop()
    
    # デフォルトの列インデックス
    # モデルデータ使用時は、0列目(2Theta)と1列目(Intensity)を自動選択
    if using_default_file:
        default_x = 0
        default_y = 1
    else:
        default_x = 0
        default_y = 1 if len(columns) > 1 else 0

    col_x = st.sidebar.selectbox("2Theta (X軸) の列", columns, index=default_x)
    col_y = st.sidebar.selectbox("Intensity (Y軸) の列", columns, index=default_y)

    # Retrieve Data
    two_theta = pd.to_numeric(df[col_x], errors='coerce').values
    intensity = pd.to_numeric(df[col_y], errors='coerce').values
    
    # Drop NaNs
    valid_mask = ~np.isnan(two_theta) & ~np.isnan(intensity)
    two_theta = two_theta[valid_mask]
    intensity = intensity[valid_mask]
    
    # Calculate d-values
    d_values = theta_to_d(two_theta)
        

    # --- 3. Peak Search Settings ---
    st.subheader("2 Peak Search Settings")
    col_pset1, col_pset2 = st.columns(2)
    with col_pset1:
        max_int = float(np.max(intensity)) if len(intensity) > 0 else 1.0
        # モデルデータの場合、ピークが明確なので感度を少し調整
        default_prominence = max_int * 0.05 if using_default_file else max_int * 0.1
        
        prominence = st.slider("ピーク検出感度 (Prominence)", 
                               min_value=0.0, 
                               max_value=max_int, 
                               value=default_prominence)
    with col_pset2:
        width = st.slider("ピーク幅 (Width)", 1, 50, 5)

    # Execute Peak Detection
    peaks, properties = find_peaks(intensity, prominence=prominence, width=width)
    peak_two_theta = two_theta[peaks]
    peak_d = d_values[peaks]
    peak_int = intensity[peaks]

    # --- 4. Peak Selection (Data Editor) ---
    st.subheader("3 Peak Selection")
    
    peak_df = pd.DataFrame({
        "Select": [True] * len(peaks),
        "2Theta": peak_two_theta,
        "d-value": peak_d,
        "Intensity": peak_int
    })
    
    # Allow user to edit the dataframe (select/deselect peaks)
    edited_peak_df = st.data_editor(peak_df, num_rows="dynamic")
    selected_peaks = edited_peak_df[edited_peak_df["Select"] == True]
    
    # --- 5. Plotting ---
    st.subheader("4 Plots")
    
    tab1, tab2 = st.tabs(["2Theta vs Intensity", "d-value vs Intensity (予備的な相決定)"])

    # Common marker trace
    peak_trace = go.Scatter(
        x=selected_peaks["2Theta"], y=selected_peaks["Intensity"],
        mode='markers', name='Selected Peaks', marker=dict(color='red', size=10, symbol='x')
    )
    
    # --- Graph 1: 2Theta ---
    with tab1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=two_theta, y=intensity, mode='lines', name='Raw Data', line=dict(color='black')))
        fig1.add_trace(peak_trace)
        fig1.update_layout(title="XRD Profile (2θ)", xaxis_title="2Theta (deg)", yaxis_title="Intensity")
        st.plotly_chart(fig1, use_container_width=True)

    # --- Graph 2: d-value ---
    with tab2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=d_values, y=intensity, mode='lines', name='Raw Data', line=dict(color='blue')))
        
        fig2.add_trace(go.Scatter(
            x=selected_peaks["d-value"], y=selected_peaks["Intensity"],
            mode='markers', name='Selected Peaks', marker=dict(color='red', size=10, symbol='x')
        ))
        
        # Display range for d-value (Zoom in for relevant range if using sample data)
        if using_default_file:
             # Sample data is likely LC/SAXS, so focus on d=10-50A area usually, or auto
             max_d_display = 100
             if not selected_peaks.empty:
                 max_d_display = selected_peaks["d-value"].max() * 1.2
        else:
             max_d_display = 50
             if not selected_peaks.empty:
                 max_d_display = selected_peaks["d-value"].max() * 1.5
        
        fig2.update_layout(title="XRD Profile (d-spacing)", xaxis_title="d (Å)", yaxis_title="Intensity", xaxis_range=[0, max_d_display])
        
        # Theoretical Lattice Overlay
        analysis_type = st.radio(
            "格子モデルの重ね書き", 
            ["None", "Lamellar", "Hexagonal (Columnar)", "Tetragonal (Columnar)"],
            horizontal=True
        )

        if analysis_type != "None" and not selected_peaks.empty:
            base_d = selected_peaks["d-value"].max()
            ratios = get_theoretical_ratios(analysis_type)
            theoretical_ds = base_d * ratios
            
            for td in theoretical_ds:
                fig2.add_vline(x=td, line_width=1, line_dash="dash", line_color="green")
                fig2.add_annotation(x=td, y=selected_peaks["Intensity"].max(), text=f"{td:.2f}", showarrow=False, yshift=10)
            
            st.info(f"基準ピーク d = {base_d:.2f} Å に基づく {analysis_type} の理論位置を表示中")

        st.plotly_chart(fig2, use_container_width=True)


    # --- 6. Rectangular 2D Reciprocal Space Q-plot ---
    st.markdown("---")
    st.subheader("52D Lattice Analysis (Reciprocal Space Q-plot)")
    
    with st.expander("Rectangular解析 (逆空間プロット) を開く", expanded=True):
        if len(selected_peaks) < 2:
            st.warning("パターン計算には少なくとも2つのピークが必要です（d1, d2を使用するため）。")
        else:
            col_rec1, col_rec2 = st.columns([1, 2])
            
            with col_rec1:
                st.write("### 格子定数の設定")
                
                # Sort d-values descending
                sorted_ds = sorted(selected_peaks["d-value"].tolist(), reverse=True)
                d1 = sorted_ds[0]
                d2 = sorted_ds[1]
                
                st.markdown(f"**使用するd値:**")
                st.markdown(f"- $d_1$ = {d1:.4f} Å")
                st.markdown(f"- $d_2$ = {d2:.4f} Å")

                # --- Pattern Calculation ---
                p1_a = 2 * d1
                p1_b_term = (1/(d2**2)) - (1/(4 * d1**2))
                
                if p1_b_term > 0:
                    p1_b = 1 / np.sqrt(p1_b_term)
                    p1_valid = True
                else:
                    p1_b = 0
                    p1_valid = False

                p2_a = 2 * d2
                p2_b_term = (1/(d1**2)) - (1/(4 * d2**2))
                
                if p2_b_term > 0:
                    p2_b = 1 / np.sqrt(p2_b_term)
                    p2_valid = True
                else:
                    p2_b = 0
                    p2_valid = False

                mode = st.radio(
                    "適用するモードを選択:",
                    ["Manual (手動)", "Pattern 1 (d1=(2,0), d2=(1,1))", "Pattern 2 (d2=(2,0), d1=(1,1))"]
                )

                if "Pattern 1" in mode:
                    if p1_valid:
                        st.success(f"Pattern 1 適用中:\n a={p1_a:.4f}, b={p1_b:.4f}")
                        current_a, current_b = p1_a, p1_b
                    else:
                        st.error("Pattern 1 は数学的に成立しません")
                        current_a, current_b = d1, d1
                
                elif "Pattern 2" in mode:
                    if p2_valid:
                        st.success(f"Pattern 2 適用中:\n a={p2_a:.4f}, b={p2_b:.4f}")
                        current_a, current_b = p2_a, p2_b
                    else:
                        st.error("Pattern 2 は数学的に成立しません")
                        current_a, current_b = d1, d1
                
                else: # Manual
                    st.info("下の入力欄で自由に調整できます")
                    current_a, current_b = float(d1), float(d1)

                a_est = st.number_input("a軸 (Å)", value=float(current_a), format="%.4f", key=f"a_{mode}")
                b_est = st.number_input("b軸 (Å)", value=float(current_b), format="%.4f", key=f"b_{mode}")
                
            with col_rec2:
                fig_rec = go.Figure()
                
                a_star = 1.0 / a_est if a_est > 0 else 0
                b_star = 1.0 / b_est if b_est > 0 else 0

                max_index = 5
                qx_vals, qy_vals, text_vals = [], [], []
                
                for h in range(max_index + 1):
                    for k in range(max_index + 1):
                        if h==0 and k==0: continue
                        qx = h * a_star
                        qy = k * b_star
                        qx_vals.append(qx)
                        qy_vals.append(qy)
                        text_vals.append(f"({h},{k})")
                        
                fig_rec.add_trace(go.Scatter(
                    x=qx_vals, y=qy_vals, mode='markers+text',
                    marker=dict(size=8, color='blue', symbol='circle'),
                    text=text_vals, textposition="top right", name='Reciprocal Lattice Points'
                ))
                
                colors = px.colors.qualitative.Plotly
                max_q_display = max(qx_vals) * 1.1 if qx_vals else 1.0
                
                for i, row in selected_peaks.iterrows():
                    d_val = row['d-value']
                    q_val = 1.0 / d_val
                    label_txt = f"d={d_val:.2f}"
                    
                    color = colors[i % len(colors)]
                    theta_range = np.linspace(0, np.pi/2, 100)
                    arc_x = q_val * np.cos(theta_range)
                    arc_y = q_val * np.sin(theta_range)
                    
                    fig_rec.add_trace(go.Scatter(
                        x=arc_x, y=arc_y, mode='lines',
                        line=dict(width=2, color=color, dash='dash'),
                        name=label_txt, hoverinfo='name'
                    ))

                fig_rec.update_layout(
                    title="Reciprocal Space Map (Rectangular)",
                    xaxis_title="Qx (1/Å)", yaxis_title="Qy (1/Å)",
                    xaxis=dict(range=[0, max_q_display], showgrid=True),
                    yaxis=dict(range=[0, max_q_display], scaleanchor="x", scaleratio=1, showgrid=True),
                    width=600, height=600
                )
                st.plotly_chart(fig_rec)

    # --- 7. Oblique 2D Lattice Analysis ---
    st.markdown("---")
    st.subheader("6 2D Lattice Analysis (Oblique / 斜交格子)")
    
    with st.expander("Oblique解析 (斜交格子プロット) を開く", expanded=False):
        if len(selected_peaks) < 1:
            st.warning("解析には実測ピークが必要です。")
        else:
            col_ob1, col_ob2 = st.columns([1, 2])
            
            with col_ob1:
                st.write("### パラメータ調整")
                
                ds_sorted = sorted(selected_peaks["d-value"].tolist(), reverse=True)
                d_max_val = ds_sorted[0]
                d_sec_val = ds_sorted[1] if len(ds_sorted) > 1 else d_max_val * 0.5
                
                a_ob = st.number_input("実空間 a軸 (Å)", value=float(d_max_val), format="%.4f", step=0.1, key="ob_a")
                b_ob = st.number_input("実空間 b軸 (Å)", value=float(d_sec_val), format="%.4f", step=0.1, key="ob_b")
                st.markdown("---")
                gamma_deg = st.slider("実空間 角度 γ (deg)", min_value=30.0, max_value=150.0, value=90.0, step=0.5)
                
                gamma_star_deg = 180.0 - gamma_deg
                st.metric(label="逆空間の角度 γ*", value=f"{gamma_star_deg:.1f}°")

            with col_ob2:
                fig_ob = go.Figure()
                
                gamma_rad = np.deg2rad(gamma_deg)
                gamma_star_rad = np.deg2rad(gamma_star_deg)
                sin_g = np.sin(gamma_rad)
                
                if sin_g == 0 or a_ob == 0 or b_ob == 0:
                    st.error("Invalid parameters")
                else:
                    a_star_len = 1.0 / (a_ob * sin_g)
                    b_star_len = 1.0 / (b_ob * sin_g)
                    
                    min_d_obs = selected_peaks["d-value"].min()
                    max_q_display = (1.0 / min_d_obs) * 1.2
                    
                    h_limit = min(int(max_q_display / a_star_len) + 2, 20)
                    k_limit = min(int(max_q_display / b_star_len) + 2, 20)

                    mesh_x, mesh_y = [], []
                    for k in range(k_limit):
                        sx = k * b_star_len * np.cos(gamma_star_rad)
                        sy = k * b_star_len * np.sin(gamma_star_rad)
                        ex = (h_limit - 1) * a_star_len + sx
                        ey = sy 
                        mesh_x.extend([sx, ex, None])
                        mesh_y.extend([sy, ey, None])

                    for h in range(h_limit):
                        sx = h * a_star_len
                        sy = 0
                        ex = sx + (k_limit - 1) * b_star_len * np.cos(gamma_star_rad)
                        ey = sy + (k_limit - 1) * b_star_len * np.sin(gamma_star_rad)
                        mesh_x.extend([sx, ex, None])
                        mesh_y.extend([sy, ey, None])

                    fig_ob.add_trace(go.Scatter(
                        x=mesh_x, y=mesh_y, mode='lines',
                        line=dict(color='lightblue', width=1),
                        hoverinfo='skip', name='Lattice Grid'
                    ))

                    qx_list, qy_list, txt_list = [], [], []
                    for h in range(h_limit):
                        for k in range(k_limit):
                            if h==0 and k==0: continue
                            qx = h * a_star_len + k * b_star_len * np.cos(gamma_star_rad)
                            qy = k * b_star_len * np.sin(gamma_star_rad)
                            if np.sqrt(qx**2 + qy**2) < max_q_display:
                                qx_list.append(qx)
                                qy_list.append(qy)
                                txt_list.append(f"({h},{k})")

                    fig_ob.add_trace(go.Scatter(
                        x=qx_list, y=qy_list, mode='markers+text',
                        marker=dict(size=8, color='blue', symbol='circle', line=dict(width=1, color='DarkBlue')),
                        text=txt_list, textposition="top right", name='Points'
                    ))

                    theta = np.linspace(0, np.pi/2, 100)
                    for i, row in selected_peaks.iterrows():
                        d_val = row['d-value']
                        q_val = 1.0 / d_val
                        color = px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
                        fig_ob.add_trace(go.Scatter(
                            x=q_val * np.cos(theta), y=q_val * np.sin(theta),
                            mode='lines', line=dict(width=2, color=color, dash='dash'),
                            name=f"d={d_val:.2f}"
                        ))

                    fig_ob.update_layout(
                        title=f"Oblique Q-plot (γ*={gamma_star_deg:.1f}°)",
                        xaxis_title="Qx (along a*) [1/Å]", yaxis_title="Qy [1/Å]",
                        width=600, height=600,
                        xaxis=dict(range=[-0.05*max_q_display, max_q_display], showgrid=False, zeroline=True),
                        yaxis=dict(range=[-0.05*max_q_display, max_q_display], scaleanchor="x", scaleratio=1, showgrid=False, zeroline=True)
                    )
                    st.plotly_chart(fig_ob)
else:
    st.info("👈 サイドバーからCSVまたはTXTファイルをアップロードしてください（またはデフォルトファイルを配置してください）。")