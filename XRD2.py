import streamlit as st
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
import plotly.graph_objects as go
import plotly.express as px

# ページ設定
st.set_page_config(page_title="XRD Analysis Web App", layout="wide")

# 定数 
WAVELENGTH = 1.5418  # Cu K-alpha

# --- 関数定義 ---

def theta_to_d(two_theta):
    """2theta (度) から d値 (A) を計算 (ブラッグの式: lambda = 2d sin(theta))"""
    theta_rad = np.deg2rad(two_theta / 2)
    with np.errstate(divide='ignore'):
        d = WAVELENGTH / (2 * np.sin(theta_rad))
    return d

def get_theoretical_ratios(lattice_type):
    """格子タイプごとのd値の理論比率を返す (d1に対する比)"""
    if lattice_type == "Lamellar":
        return np.array([1, 1/2, 1/3, 1/4, 1/5])
    elif lattice_type == "Hexagonal (Columnar)":
        return np.array([1, 1/np.sqrt(3), 1/2, 1/np.sqrt(7), 1/3])
    elif lattice_type == "Tetragonal (Columnar)":
        return np.array([1, 1/np.sqrt(2), 1/2, 1/np.sqrt(5), 1/3])
    return np.array([])

# --- サイドバー (設定) ---
st.sidebar.header("ファイル読み込み設定")

# 1. ファイル形式の選択
file_type = st.sidebar.radio(
    "ファイル形式を選択",
    ('txt (スペースまたはタブ区切り)', 'csv (カンマ区切り)')
)

# 2. アップローダー
uploaded_file = st.sidebar.file_uploader("XRDデータをアップロード", type=['csv', 'txt'])

# 3. ヘッダー行スキップ設定
header_rows = st.sidebar.number_input("スキップする行数 (ヘッダー除去)", value=0, min_value=0)


# --- メイン処理 ---
st.title("XRD Analysis Web App")

if uploaded_file is not None:
    # --- 1. ファイル読み込み処理 ---
    try:
        if 'txt' in file_type:
            # txt選択時: 自動判定(sep=None) + pythonエンジン
            df = pd.read_csv(uploaded_file, skiprows=header_rows, header=None, sep=None, engine='python')
        else:
            # csv選択時: カンマ区切り
            df = pd.read_csv(uploaded_file, skiprows=header_rows, header=None, sep=',')
        
        # 読み込み直後のデータを少し表示（確認用）
        st.write("▼ 読み込んだデータの先頭 (Raw Data Preview)")
        st.dataframe(df.head())

        # --- 2. 列の選択機能 ---
        st.sidebar.markdown("---")
        st.sidebar.header("列の割り当て")
        
        # データフレームの列名（または番号）リストを取得
        columns = df.columns.tolist()
        
        if len(columns) < 2:
            st.error("エラー: データに列が2つ以上見つかりません。区切り文字やスキップ行数を確認してください。")
            st.stop()
        
        # デフォルトのインデックス設定 (0番目をX, 1番目をYとする)
        default_x = 0
        default_y = 1 if len(columns) > 1 else 0

        # セレクトボックスで列を選ばせる
        col_x = st.sidebar.selectbox("2Theta (X軸) の列", columns, index=default_x)
        col_y = st.sidebar.selectbox("Intensity (Y軸) の列", columns, index=default_y)

        # 選択されたデータを取得
        two_theta = pd.to_numeric(df[col_x], errors='coerce').values
        intensity = pd.to_numeric(df[col_y], errors='coerce').values
        
        # NaNが含まれている場合は除去
        valid_mask = ~np.isnan(two_theta) & ~np.isnan(intensity)
        two_theta = two_theta[valid_mask]
        intensity = intensity[valid_mask]
        
        # d値の計算
        d_values = theta_to_d(two_theta)
        
    except Exception as e:
        st.error(f"ファイル読み込みまたはデータ処理エラー: {e}")
        st.stop()

    # --- 3. ピークピッキング設定 ---
    st.subheader("Peak Search Settings")
    col_pset1, col_pset2 = st.columns(2)
    with col_pset1:
        # プロミネンス設定
        max_int = float(np.max(intensity)) if len(intensity) > 0 else 1.0
        prominence = st.slider("ピーク検出感度 (Prominence)", 
                               min_value=0.0, 
                               max_value=max_int, 
                               value=max_int*0.1)
    with col_pset2:
        width = st.slider("ピーク幅 (Width)", 1, 50, 5)

    # ピーク検出実行
    peaks, properties = find_peaks(intensity, prominence=prominence, width=width)
    peak_two_theta = two_theta[peaks]
    peak_d = d_values[peaks]
    peak_int = intensity[peaks]

    # --- 4. ピークの取捨選択 (Data Editor) ---
    st.subheader("Peak Selection")
    
    peak_df = pd.DataFrame({
        "Select": [True] * len(peaks),
        "2Theta": peak_two_theta,
        "d-value": peak_d,
        "Intensity": peak_int
    })
    
    edited_peak_df = st.data_editor(peak_df, num_rows="dynamic")
    selected_peaks = edited_peak_df[edited_peak_df["Select"] == True]
    
    # --- 5. プロット表示 ---
    st.subheader("Plots")
    
    tab1, tab2 = st.tabs(["2Theta vs Intensity", "d-value vs Intensity"])

    # 共通マーカー
    peak_trace = go.Scatter(
        x=selected_peaks["2Theta"], y=selected_peaks["Intensity"],
        mode='markers', name='Selected Peaks', marker=dict(color='red', size=10, symbol='x')
    )
    
    # --- グラフ1: 2Theta ---
    with tab1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=two_theta, y=intensity, mode='lines', name='Raw Data', line=dict(color='black')))
        fig1.add_trace(peak_trace)
        fig1.update_layout(title="XRD Profile (2θ)", xaxis_title="2Theta (deg)", yaxis_title="Intensity")
        st.plotly_chart(fig1, use_container_width=True)

    # --- グラフ2: d-value ---
    with tab2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=d_values, y=intensity, mode='lines', name='Raw Data', line=dict(color='blue')))
        
        fig2.add_trace(go.Scatter(
            x=selected_peaks["d-value"], y=selected_peaks["Intensity"],
            mode='markers', name='Selected Peaks', marker=dict(color='red', size=10, symbol='x')
        ))
        
        # d値表示範囲設定
        max_d_display = 50 
        if not selected_peaks.empty:
             max_d_display = selected_peaks["d-value"].max() * 1.5
        
        fig2.update_layout(title="XRD Profile (d-spacing)", xaxis_title="d (Å)", yaxis_title="Intensity", xaxis_range=[0, max_d_display])
        
        # --- 格子解析 (理想位置表示) ---
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


# --- 6. Rectangular 2D 逆格子表示 (Reciprocal Space Q-plot) ---
    st.markdown("---")
    st.subheader("2D Lattice Analysis (Reciprocal Space Q-plot)")
    
    with st.expander("Rectangular解析 (逆空間プロット) を開く", expanded=True):
        if len(selected_peaks) < 2:
            st.warning("パターン計算には少なくとも2つのピークが必要です（d1, d2を使用するため）。")
        else:
            col_rec1, col_rec2 = st.columns([1, 2])
            
            with col_rec1:
                st.write("### 格子定数の設定")
                
                # d値の取得 (大きい順)
                sorted_ds = sorted(selected_peaks["d-value"].tolist(), reverse=True)
                d1 = sorted_ds[0]
                d2 = sorted_ds[1]
                
                st.markdown(f"**使用するd値:**")
                st.markdown(f"- $d_1$ = {d1:.4f} Å")
                st.markdown(f"- $d_2$ = {d2:.4f} Å")

                # --- パターンの計算 ---
                # パターン1: d1 -> (2,0), d2 -> (1,1)
                # a = 2 * d1
                p1_a = 2 * d1
                p1_b_term = (1/(d2**2)) - (1/(4 * d1**2))
                
                if p1_b_term > 0:
                    p1_b = 1 / np.sqrt(p1_b_term)
                    p1_valid = True
                else:
                    p1_b = 0
                    p1_valid = False

                # パターン2: d2 -> (2,0), d1 -> (1,1)
                # a = 2 * d2
                p2_a = 2 * d2
                p2_b_term = (1/(d1**2)) - (1/(4 * d2**2))
                
                if p2_b_term > 0:
                    p2_b = 1 / np.sqrt(p2_b_term)
                    p2_valid = True
                else:
                    p2_b = 0
                    p2_valid = False

                # --- 選択肢の表示 ---
                mode = st.radio(
                    "適用するモードを選択:",
                    ["Manual (手動)", "Pattern 1", "Pattern 2"]
                )

                # 計算結果の表示と値の決定
                if mode == "Pattern 1":
                    if p1_valid:
                        st.success(f"Pattern 1 適用中:\n a={p1_a:.4f}, b={p1_b:.4f}")
                        current_a = p1_a
                        current_b = p1_b
                    else:
                        st.error("Pattern 1 は数学的に成立しません")
                        current_a, current_b = d1, d1
                
                elif mode == "Pattern 2":
                    if p2_valid:
                        st.success(f"Pattern 2 適用中:\n a={p2_a:.4f}, b={p2_b:.4f}")
                        current_a = p2_a
                        current_b = p2_b
                    else:
                        st.error("Pattern 2 は数学的に成立しません")
                        current_a, current_b = d1, d1
                
                else: # Manual
                    st.info("下の入力欄で自由に調整できます")
                    current_a = float(d1)
                    current_b = float(d1)

                # 手動調整用
                a_est = st.number_input("a軸 (Å)", value=float(current_a), format="%.4f", key=f"a_{mode}")
                b_est = st.number_input("b軸 (Å)", value=float(current_b), format="%.4f", key=f"b_{mode}")
                
                st.markdown("""
                **プロットの見方:**
                - **青い点:** 計算された逆格子点（格子定数 $a, b$ に依存して動きます）
                - **赤い線:** 実測データの $d$ 値（固定されています）
                - **目標:** 青い点が赤い線の上に乗るように $a, b$ を調整します。
                """)

            with col_rec2:
                # Q-space プロットの作成
                fig_rec = go.Figure()
                
                # 逆格子ベクトル (Rectangular)
                # a* = 1/a, b* = 1/b
                a_star = 1.0 / a_est if a_est > 0 else 0
                b_star = 1.0 / b_est if b_est > 0 else 0

                # 1. 逆格子点 (Model Grid) をプロット
                # Qx = h * a*, Qy = k * b*
                max_index = 5
                qx_vals = []
                qy_vals = []
                text_vals = []
                
                for h in range(max_index + 1):
                    for k in range(max_index + 1):
                        if h==0 and k==0: continue
                        qx = h * a_star
                        qy = k * b_star
                        qx_vals.append(qx)
                        qy_vals.append(qy)
                        text_vals.append(f"({h},{k})")
                        
                fig_rec.add_trace(go.Scatter(
                    x=qx_vals, y=qy_vals,
                    mode='markers+text',
                    marker=dict(size=8, color='blue', symbol='circle'),
                    text=text_vals,
                    textposition="top right",
                    name='Reciprocal Lattice Points'
                ))
                
                # 2. 実測ピークの円弧 (Observed Iso-d curves)
                # 半径 Q = 1/d の円
                colors = px.colors.qualitative.Plotly
                
                # 表示範囲の決定（最大Q値）
                max_q_display = max(qx_vals) * 1.1 if qx_vals else 1.0
                
                for i, row in selected_peaks.iterrows():
                    d_val = row['d-value']
                    q_val = 1.0 / d_val
                    
                    label_txt = f"d={d_val:.2f}"
                    if np.isclose(d_val, d1, atol=0.01): label_txt += " (d1)"
                    if np.isclose(d_val, d2, atol=0.01): label_txt += " (d2)"
                    
                    color = colors[i % len(colors)]
                    
                    # 第一象限の円弧を描くためのデータ生成
                    theta = np.linspace(0, np.pi/2, 100)
                    arc_x = q_val * np.cos(theta)
                    arc_y = q_val * np.sin(theta)
                    
                    fig_rec.add_trace(go.Scatter(
                        x=arc_x, y=arc_y,
                        mode='lines',
                        line=dict(width=2, color=color, dash='dash'),
                        name=label_txt,
                        hoverinfo='name'
                    ))

                # レイアウト調整
                fig_rec.update_layout(
                    title="Reciprocal Space Map (Q-plot)",
                    xaxis_title="Qx (1/Å) [ ~ h · a* ]",
                    yaxis_title="Qy (1/Å) [ ~ k · b* ]",
                    xaxis=dict(range=[0, max_q_display], showgrid=True),
                    yaxis=dict(range=[0, max_q_display], scaleanchor="x", scaleratio=1, showgrid=True),
                    width=600, height=600,
                    showlegend=True
                )
                
                st.plotly_chart(fig_rec)
# --- 7. Oblique 2D 逆格子表示 (Oblique Lattice Analysis) ---
    st.markdown("---")
    st.subheader("2D Lattice Analysis (Oblique / 斜交格子)")
    
    with st.expander("Oblique解析 (斜交格子プロット) を開く", expanded=False):
        if len(selected_peaks) < 1:
            st.warning("解析には実測ピークが必要です。")
        else:
            col_ob1, col_ob2 = st.columns([1, 2])
            
            with col_ob1:
                st.write("### パラメータ調整")
                st.info("実空間の角度 γ を調整して、青い点を赤い円弧上に配置してください。")
                
                # デフォルト値の推定
                ds_sorted = sorted(selected_peaks["d-value"].tolist(), reverse=True)
                d_max_val = ds_sorted[0]
                d_sec_val = ds_sorted[1] if len(ds_sorted) > 1 else d_max_val * 0.5
                
                # --- パラメータ入力 ---
                
                # 1. 格子定数 a, b (実空間)
                a_ob = st.number_input("実空間 a軸 (Å)", value=float(d_max_val), format="%.4f", step=0.1, key="ob_a")
                b_ob = st.number_input("実空間 b軸 (Å)", value=float(d_sec_val), format="%.4f", step=0.1, key="ob_b")

                st.markdown("---")
                
                # 2. 角度 gamma (実空間)
                gamma_deg = st.slider("実空間 角度 γ (deg)", min_value=30.0, max_value=150.0, value=90.0, step=0.5)
                
                # 逆空間角度 gamma*
                gamma_star_deg = 180.0 - gamma_deg
                
                st.metric(
                    label="逆空間の角度 γ*", 
                    value=f"{gamma_star_deg:.1f}°",
                    delta=f"From real γ: {gamma_deg}°",
                    delta_color="off"
                )

                st.markdown(r"""
                **表示の説明:**
                - **薄い青線:** 逆格子のグリッド（a*軸・b*軸に平行な線）
                - **青い点:** 逆格子点 $(h,k)$
                - **赤い破線:** 実測値 $(d)$
                """)

            with col_ob2:
                fig_ob = go.Figure()
                
                # --- 計算ロジック ---
                gamma_rad = np.deg2rad(gamma_deg)
                gamma_star_rad = np.deg2rad(gamma_star_deg)
                sin_g = np.sin(gamma_rad)
                
                if sin_g == 0 or a_ob == 0 or b_ob == 0:
                    st.error("Invalid parameters")
                    st.stop()

                # 逆格子ベクトルの長さ
                a_star_len = 1.0 / (a_ob * sin_g)
                b_star_len = 1.0 / (b_ob * sin_g)
                
                # 表示範囲の設定
                min_d_obs = selected_peaks["d-value"].min()
                max_q_display = (1.0 / min_d_obs) * 1.2
                
                # グリッド生成範囲 (少し広めに計算してクリッピングは表示時に任せる)
                h_limit = int(max_q_display / a_star_len) + 2
                k_limit = int(max_q_display / b_star_len) + 2
                h_limit = min(h_limit, 20) 
                k_limit = min(k_limit, 20)

                # --- 1. グリッド線 (Lattice Mesh Lines) ---
                # 格子点同士を結ぶ線を描画します
                mesh_x = []
                mesh_y = []
                
                # a*方向に平行な線 (hを走査, k固定)
                for k in range(k_limit):
                    # Start point (h=0)
                    sx = k * b_star_len * np.cos(gamma_star_rad)
                    sy = k * b_star_len * np.sin(gamma_star_rad)
                    # End point (h=h_limit-1)
                    ex = (h_limit - 1) * a_star_len + sx
                    ey = sy # a*はX軸上なのでY座標は変わらない
                    
                    mesh_x.extend([sx, ex, None])
                    mesh_y.extend([sy, ey, None])

                # b*方向に平行な線 (kを走査, h固定)
                for h in range(h_limit):
                    # Start point (k=0)
                    sx = h * a_star_len
                    sy = 0
                    # End point (k=k_limit-1)
                    ex = sx + (k_limit - 1) * b_star_len * np.cos(gamma_star_rad)
                    ey = sy + (k_limit - 1) * b_star_len * np.sin(gamma_star_rad)
                    
                    mesh_x.extend([sx, ex, None])
                    mesh_y.extend([sy, ey, None])

                fig_ob.add_trace(go.Scatter(
                    x=mesh_x, y=mesh_y,
                    mode='lines',
                    line=dict(color='lightblue', width=1), # 薄い青色で細く
                    hoverinfo='skip',
                    name='Lattice Grid'
                ))

                # --- 2. 逆格子点 (Grid Points) ---
                qx_list = []
                qy_list = []
                txt_list = []

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
                    x=qx_list, y=qy_list,
                    mode='markers+text',
                    marker=dict(
                        size=8, 
                        color='blue', 
                        symbol='circle',
                        line=dict(width=1, color='DarkBlue')
                    ),
                    text=txt_list,
                    textposition="top right",
                    name='Points'
                ))

                # --- 3. 逆空間の軸 (Axes Vectors) ---
                axis_scale = max_q_display * 0.2
                # a* vector
                fig_ob.add_annotation(
                    x=axis_scale, y=0, xref="x", yref="y",
                    ax=0, ay=0, axref="x", ayref="y",
                    showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="green"
                )
                fig_ob.add_annotation(x=axis_scale, y=0, text="a*", font=dict(color="green"))

                # b* vector
                b_vec_x = axis_scale * np.cos(gamma_star_rad)
                b_vec_y = axis_scale * np.sin(gamma_star_rad)
                fig_ob.add_annotation(
                    x=b_vec_x, y=b_vec_y, xref="x", yref="y",
                    ax=0, ay=0, axref="x", ayref="y",
                    showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="green"
                )
                fig_ob.add_annotation(
                    x=b_vec_x, y=b_vec_y, text="b*", 
                    xanchor="right" if b_vec_x < 0 else "left", font=dict(color="green")
                )

                # --- 4. 実測データの円弧 ---
                colors = px.colors.qualitative.Plotly
                theta = np.linspace(0, np.pi/2, 100)
                for i, row in selected_peaks.iterrows():
                    d_val = row['d-value']
                    q_val = 1.0 / d_val
                    color = colors[i % len(colors)]
                    
                    fig_ob.add_trace(go.Scatter(
                        x=q_val * np.cos(theta), 
                        y=q_val * np.sin(theta),
                        mode='lines',
                        line=dict(width=2, color=color, dash='dash'),
                        name=f"d={d_val:.2f}"
                    ))

                # レイアウト調整
                fig_ob.update_layout(
                    title=f"Oblique Q-plot (γ*={gamma_star_deg:.1f}°)",
                    xaxis_title="Qx (along a*) [1/Å]",
                    yaxis_title="Qy [1/Å]",
                    width=600, height=600,
                    showlegend=True,
                    # 軸の設定（薄くする）
                    xaxis=dict(
                        range=[-0.05 * max_q_display, max_q_display], 
                        showgrid=True, 
                        gridcolor='#F0F0F0', # 非常に薄いグレー
                        zeroline=True, 
                        zerolinecolor='#BBBBBB', # 薄めのグレー（真っ黒ではない）
                        zerolinewidth=1
                    ),
                    yaxis=dict(
                        range=[-0.05 * max_q_display, max_q_display], 
                        scaleanchor="x", scaleratio=1,
                        showgrid=True, 
                        gridcolor='#F0F0F0', 
                        zeroline=True, 
                        zerolinecolor='#BBBBBB',
                        zerolinewidth=1
                    )
                )
                
                st.plotly_chart(fig_ob)
else:
    st.info("👈 サイドバーからCSVまたはTXTファイルをアップロードしてください。")