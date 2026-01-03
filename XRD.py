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
    # 0割りを防ぐための処理
    theta_rad = np.deg2rad(two_theta / 2)
    with np.errstate(divide='ignore'):
        d = WAVELENGTH / (2 * np.sin(theta_rad))
    return d

def get_theoretical_ratios(lattice_type):
    """格子タイプごとのd値の理論比率を返す (d1に対する比)"""
    # d001: d002: d003... の比率
    if lattice_type == "Lamellar":
        return np.array([1, 1/2, 1/3, 1/4, 1/5])
    elif lattice_type == "Hexagonal (Columnar)":
        return np.array([1, 1/np.sqrt(3), 1/2, 1/np.sqrt(7), 1/3])
    elif lattice_type == "Tetragonal (Columnar)":
        return np.array([1, 1/np.sqrt(2), 1/2, 1/np.sqrt(5), 1/3])
    return np.array([])

# --- サイドバー (設定) ---
st.sidebar.header("設定")
uploaded_file = st.sidebar.file_uploader("XRDデータをアップロード (csv, txt)", type=['csv', 'txt'])
header_rows = st.sidebar.number_input("ヘッダー行数 (スキップする行)", value=0, min_value=0)
delimiter = st.sidebar.text_input("区切り文字 (空白の場合はspace)", value=",")

# --- メイン処理 ---

st.title("XRD Analysis Web App")

if uploaded_file is not None:
    # 1. ファイル読み込み
    try:
        sep = delimiter if delimiter != "space" else None
        # pandasで読み込む方がロバストです
        df = pd.read_csv(uploaded_file, skiprows=header_rows, header=None, sep=sep)
        # データの整形（1列目:2theta, 2列目:Intensityと仮定）
        data = df.iloc[:, :2].values
        two_theta = data[:, 0]
        intensity = data[:, 1]
        
        # d値の計算
        d_values = theta_to_d(two_theta)
        
    except Exception as e:
        st.error(f"ファイル読み込みエラー: {e}")
        st.stop()

    # --- 3. ピークピッキング設定 ---
    st.subheader("Peak Search Settings")
    col_pset1, col_pset2 = st.columns(2)
    with col_pset1:
        # プロミネンス（ピークの際立ち度）で制御
        prominence = st.slider("ピーク検出感度 (Prominence)", 
                               min_value=float(np.min(intensity)), 
                               max_value=float(np.max(intensity)), 
                               value=float(np.max(intensity)*0.1))
    with col_pset2:
        width = st.slider("ピーク幅 (Width)", 1, 50, 5)

    # ピーク検出実行
    peaks, properties = find_peaks(intensity, prominence=prominence, width=width)
    peak_two_theta = two_theta[peaks]
    peak_d = d_values[peaks]
    peak_int = intensity[peaks]

    # --- 4. ピークの取捨選択 (Data Editor) ---
    st.subheader("Peak Selection")
    
    # DataFrame作成
    peak_df = pd.DataFrame({
        "Select": [True] * len(peaks), # デフォルトですべて選択
        "2Theta": peak_two_theta,
        "d-value": peak_d,
        "Intensity": peak_int
    })
    
    # ユーザーが編集可能なテーブルを表示
    edited_peak_df = st.data_editor(peak_df, num_rows="dynamic")
    
    # 選択されたピークのみを抽出
    selected_peaks = edited_peak_df[edited_peak_df["Select"] == True]
    
    # --- 1 & 2. プロット表示 (Plotlyを使用) ---
    st.subheader("Plots")
    
    tab1, tab2 = st.tabs(["2Theta vs Intensity", "d-value vs Intensity"])

    # 共通のピークマーカー設定
    peak_trace_2theta = go.Scatter(
        x=selected_peaks["2Theta"], y=selected_peaks["Intensity"],
        mode='markers', name='Selected Peaks', marker=dict(color='red', size=10, symbol='x')
    )
    
    # グラフ1: 2Theta
    with tab1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=two_theta, y=intensity, mode='lines', name='Raw Data', line=dict(color='black')))
        fig1.add_trace(peak_trace_2theta)
        fig1.update_layout(title="XRD Profile (2θ)", xaxis_title="2Theta (deg)", yaxis_title="Intensity")
        st.plotly_chart(fig1, use_container_width=True)

    # グラフ2: d-value (要件2)
    with tab2:
        fig2 = go.Figure()
        # d値プロットは通常、小さい角度（大きいd）が左に来るか、通常の数直線通りか好みが分かれますが、
        # ここでは通常の数値軸（左が小、右が大）でプロットします。
        # データが膨大な場合、線が重なるのでmarkersのみあるいはlinesで描画
        fig2.add_trace(go.Scatter(x=d_values, y=intensity, mode='lines', name='Raw Data', line=dict(color='blue')))
        
        fig2.add_trace(go.Scatter(
            x=selected_peaks["d-value"], y=selected_peaks["Intensity"],
            mode='markers', name='Selected Peaks', marker=dict(color='red', size=10, symbol='x')
        ))
        
        # d値の範囲設定 (極端に大きい値をカット)
        max_d_display = 50 
        if not selected_peaks.empty:
             max_d_display = selected_peaks["d-value"].max() * 1.5
        
        fig2.update_layout(title="XRD Profile (d-spacing)", xaxis_title="d (Å)", yaxis_title="Intensity", xaxis_range=[0, max_d_display])
        
        # --- 5. 格子解析 (理想位置の表示) ---
        analysis_type = st.radio(
            "格子モデルの重ね書き", 
            ["None", "Lamellar", "Hexagonal (Columnar)", "Tetragonal (Columnar)"],
            horizontal=True
        )

        if analysis_type != "None" and not selected_peaks.empty:
            # 最大のd値を持つピークを基準 (d1) とする (通常低角側の最強ピーク)
            # ユーザーが選んだリストの中で最大のd値を取得
            base_d = selected_peaks["d-value"].max()
            
            ratios = get_theoretical_ratios(analysis_type)
            theoretical_ds = base_d * ratios
            
            # 垂直線を追加
            for td in theoretical_ds:
                fig2.add_vline(x=td, line_width=1, line_dash="dash", line_color="green")
                fig2.add_annotation(x=td, y=selected_peaks["Intensity"].max(), text=f"{td:.2f}", showarrow=False, yshift=10)
            
            st.info(f"基準ピーク d = {base_d:.2f} Å に基づく {analysis_type} の理論位置を緑の破線で表示しています。")

        st.plotly_chart(fig2, use_container_width=True)


    # --- 6. Rectangular 2D 逆格子表示 ---
    st.markdown("---")
    st.subheader("2D Reciprocal Lattice Analysis (Rectangular)")
    
    with st.expander("Rectangular格子解析を開く"):
        if len(selected_peaks) < 2:
            st.warning("Rectangular解析には少なくとも2つのピークを選択してください（a軸、b軸決定のため）。")
        else:
            col_rec1, col_rec2 = st.columns([1, 2])
            
            with col_rec1:
                st.write("格子定数の仮定")
                # 簡易的に、選択されたピークの上位2つを使ってa, bを決定するロジック、
                # またはユーザー入力させるロジックなどが考えられます。
                # ここではユーザーに入力させ、観測ピークと比較する形式にします。
                
                # デフォルト値を選択ピークから推定
                sorted_ds = sorted(selected_peaks["d-value"].tolist(), reverse=True)
                d1_def = sorted_ds[0]
                d2_def = sorted_ds[1] if len(sorted_ds) > 1 else sorted_ds[0]/2
                
                # Rectangular (hk0) 面と仮定: 1/d^2 = (h/a)^2 + (k/b)^2
                # 単純化のため、ユーザーにa, bを推定入力させる、あるいは
                # d1 = a (10), d2 = b (01) と仮定するケースなど多様ですが、
                # ここでは逆格子ベクトル a* = 1/a, b* = 1/b をプロットします。
                
                a_est = st.number_input("推定 a軸 (Å)", value=d1_def)
                b_est = st.number_input("推定 b軸 (Å)", value=d2_def)
                
                gamma_deg = st.number_input("角度 gamma (deg)", value=90.0)
                
            with col_rec2:
                # 逆格子マップの作成
                st.write("逆格子マップ (a* vs b*)")
                
                # 逆格子ベクトルの長さ
                a_star = 1/a_est
                b_star = 1/b_est
                gamma_rad = np.deg2rad(gamma_deg)
                
                # 理想的なスポット (h, k) = (-5~5, -5~5)
                h_range = range(-3, 4)
                k_range = range(-3, 4)
                
                rec_x = [] # a* 方向
                rec_y = [] # b* 方向
                indices = []
                
                for h in h_range:
                    for k in k_range:
                        if h==0 and k==0: continue
                        # 一般的な斜交座標系での逆格子位置
                        # 直交座標系(x, y)への変換
                        # x = h*a* + k*b* cos(gamma*)
                        # y = k*b* sin(gamma*)
                        # Rectangularならgamma=90なので x=h/a, y=k/b
                        
                        # 簡易計算 (Rectangular/Oblique対応)
                        qx = h * a_star + k * b_star * np.cos(gamma_rad) # ※厳密な逆格子角ではないが簡易可視化用
                        qy = k * b_star * np.sin(gamma_rad)
                        
                        rec_x.append(qx)
                        rec_y.append(qy)
                        indices.append(f"({h},{k})")

                # 実測ピークの円環（デバイリング）を表示
                # 原点からの距離 q = 1/d
                
                fig_rec = go.Figure()
                
                # 1. 理論スポットのプロット
                fig_rec.add_trace(go.Scatter(
                    x=rec_x, y=rec_y, mode='markers+text',
                    text=indices, textposition="top center",
                    marker=dict(size=8, color='blue'),
                    name='Theoretical (hk)'
                ))
                
                # 2. 実測ピークのデバイリング（円）
                # 観測されたd値に対応する逆空間距離 1/d の円を描く
                q_obs = 1.0 / selected_peaks["d-value"].values
                
                for q in q_obs:
                    fig_rec.add_shape(
                        type="circle",
                        xref="x", yref="y",
                        x0=-q, y0=-q, x1=q, y1=q,
                        line_color="red", line_dash="dot",
                    )
                
                # レイアウト調整
                max_q = max(q_obs) * 1.2 if len(q_obs) > 0 else max(max(rec_x), max(rec_y))
                fig_rec.update_layout(
                    width=600, height=600,
                    xaxis_range=[-max_q, max_q],
                    yaxis_range=[-max_q, max_q],
                    title="2D Reciprocal Lattice Simulation",
                    xaxis_title="Qx (1/Å)",
                    yaxis_title="Qy (1/Å)",
                    showlegend=True
                )
                fig_rec.update_yaxes(scaleanchor="x", scaleratio=1) # アスペクト比を1:1に固定
                
                st.plotly_chart(fig_rec)
                st.caption("青点: 入力a,bに基づく理論スポット。赤破線: 選択したピークの1/d値（デバイリング）。スポットが赤線上に乗れば指数付け成功。")

else:
    st.info("サイドバーからCSVまたはTXTファイルをアップロードしてください。")