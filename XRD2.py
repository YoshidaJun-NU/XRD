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


   # --- 6. Rectangular 2D 逆格子表示 (h-k space) ---
    st.markdown("---")
    st.subheader("2D Lattice Analysis (h-k plot)")
    
    with st.expander("Rectangular解析 (h-k プロット) を開く", expanded=True):
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
                # パターン1: d1=(2,0), d2=(1,1)
                # a = 2*d1
                # 1/b^2 = 1/d2^2 - 1/(4*d1^2)
                p1_a = 2 * d1
                p1_b_term = (1/(d2**2)) - (1/(4 * d1**2))
                p1_b = 1/np.sqrt(p1_b_term) if p1_b_term > 0 else 0
                p1_valid = p1_b > 0

                # パターン2: d2=(2,0), d1=(1,1)
                # a = 2*d2
                # 1/b^2 = 1/d1^2 - 1/(4*d2^2)
                p2_a = 2 * d2
                p2_b_term = (1/(d1**2)) - (1/(4 * d2**2))
                p2_b = 1/np.sqrt(p2_b_term) if p2_b_term > 0 else 0
                p2_valid = p2_b > 0

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
                        st.error("Pattern 1 は数学的に成立しません (ルートの中が負)")
                        current_a = d1 # fallback
                        current_b = d1
                
                elif mode == "Pattern 2":
                    if p2_valid:
                        st.success(f"Pattern 2 適用中:\n a={p2_a:.4f}, b={p2_b:.4f}")
                        current_a = p2_a
                        current_b = p2_b
                    else:
                        st.error("Pattern 2 は数学的に成立しません (ルートの中が負)")
                        current_a = d1
                        current_b = d1
                
                else: # Manual
                    st.info("下の入力欄で自由に調整できます")
                    current_a = float(d1)
                    current_b = float(d1)

                # 手動調整用 (選択したパターンの値をデフォルトに入れるが、微調整可能にする)
                # keyを変えることで外部からの値更新を反映させるテクニック
                a_est = st.number_input("a軸 (Å)", value=float(current_a), format="%.4f", key=f"a_{mode}")
                b_est = st.number_input("b軸 (Å)", value=float(current_b), format="%.4f", key=f"b_{mode}")
                
                st.markdown("""
                **帰属パターンの詳細:**
                - **Pattern 1:** $d_1 \to (20)$, $d_2 \to (11)$
                - **Pattern 2:** $d_2 \to (20)$, $d_1 \to (11)$
                """)

            with col_rec2:
                # h-k プロットの作成
                fig_hk = go.Figure()
                
                # 1. 整数の格子点 (Theoretical Grid)
                max_index = 6
                h_vals = []
                k_vals = []
                text_vals = []
                
                for h in range(max_index + 1):
                    for k in range(max_index + 1):
                        if h==0 and k==0: continue
                        h_vals.append(h)
                        k_vals.append(k)
                        text_vals.append(f"({h},{k})")
                        
                fig_hk.add_trace(go.Scatter(
                    x=h_vals, y=k_vals,
                    mode='markers',
                    marker=dict(size=6, color='blue', opacity=0.3),
                    text=text_vals,
                    hoverinfo='text',
                    name='Grid (Integer)'
                ))
                
                # 2. 実測ピーク曲線 (Iso-d curves)
                # k = b * sqrt( 1/d^2 - (h/a)^2 )
                colors = px.colors.qualitative.Plotly
                
                for i, row in selected_peaks.iterrows():
                    d_val = row['d-value']
                    # Label
                    label_txt = f"d={d_val:.2f}"
                    if np.isclose(d_val, d1, atol=0.01): label_txt += " (d1)"
                    if np.isclose(d_val, d2, atol=0.01): label_txt += " (d2)"

                    # hの最大値 (k=0になる点)
                    h_limit = a_est / d_val
                    
                    # プロット用のh配列
                    h_plot = np.linspace(0, h_limit, 200)
                    
                    # 対応するkを計算
                    inside_sqrt = (1.0 / d_val**2) - (h_plot / a_est)**2
                    inside_sqrt = np.clip(inside_sqrt, 0, None)
                    k_plot = b_est * np.sqrt(inside_sqrt)
                    
                    color = colors[i % len(colors)]
                    
                    fig_hk.add_trace(go.Scatter(
                        x=h_plot, y=k_plot,
                        mode='lines',
                        line=dict(width=2, color=color),
                        name=label_txt,
                        hoverinfo='name'
                    ))

                # レイアウト調整
                fig_hk.update_layout(
                    title="h-k Plot (First Quadrant)",
                    xaxis_title="Index h",
                    yaxis_title="Index k",
                    xaxis=dict(range=[0, max_index+0.5], dtick=1, showgrid=True),
                    yaxis=dict(range=[0, max_index+0.5], dtick=1, scaleanchor="x", scaleratio=1, showgrid=True),
                    width=600, height=600,
                    showlegend=True
                )
                
                st.plotly_chart(fig_hk)
                st.caption("曲線が青い点（整数交点）を通るように調整してください。Patternを選択すると自動で合わせます。")
else:
    st.info("👈 サイドバーからCSVまたはTXTファイルをアップロードしてください。")