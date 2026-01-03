import streamlit as st
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
import plotly.graph_objects as go

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
        if len(selected_peaks) < 1:
            st.warning("解析には少なくとも1つのピークを選択してください。")
        else:
            col_rec1, col_rec2 = st.columns([1, 2])
            
            with col_rec1:
                st.write("### 格子定数の調整")
                st.info("スライダー等を動かして、曲線が「青い点（整数座標）」の上を通るようにa, bを調整してください。")
                
                # デフォルト値の推定
                sorted_ds = sorted(selected_peaks["d-value"].tolist(), reverse=True)
                d_max = sorted_ds[0]
                
                # a, b の入力（少し刻みを細かくしています）
                a_est = st.number_input("推定 a軸 (Å)", value=float(d_max), step=0.1, format="%.2f")
                b_est = st.number_input("推定 b軸 (Å)", value=float(d_max), step=0.1, format="%.2f")
                
            with col_rec2:
                # h-k プロットの作成
                fig_hk = go.Figure()
                
                # 1. 整数の格子点 (Theoretical Grid) をプロット
                # 表示範囲 (h, k の最大値)
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
                    marker=dict(size=5, color='blue', opacity=0.5),
                    text=text_vals,
                    hoverinfo='text',
                    name='Integer Grid (h,k)'
                ))
                
                # 2. 実測ピークに対応する曲線をプロット (Iso-d curves)
                # Rectangularの式: 1/d^2 = (h/a)^2 + (k/b)^2
                # これを変形して k = b * sqrt( 1/d^2 - (h/a)^2 )
                
                # 色の準備（ピークごとに色を変える）
                colors = px.colors.qualitative.Plotly
                
                for i, row in selected_peaks.iterrows():
                    d_val = row['d-value']
                    peak_id = f"d={d_val:.2f}Å"
                    
                    # hの最大値 (k=0のとき) -> h_max = a / d
                    h_limit = a_est / d_val
                    
                    # プロット用のh配列を作成 (0からh_limitまで滑らかに)
                    h_plot = np.linspace(0, h_limit, 100)
                    
                    # 対応するkを計算
                    # 中身が負にならないようにclip
                    inside_sqrt = (1.0 / d_val**2) - (h_plot / a_est)**2
                    inside_sqrt = np.clip(inside_sqrt, 0, None)
                    k_plot = b_est * np.sqrt(inside_sqrt)
                    
                    # 表示範囲内のデータのみ残す (max_indexを超えたらカットしてもよいが、plotlyが自動調整するのでそのまま)
                    
                    color = colors[i % len(colors)]
                    
                    fig_hk.add_trace(go.Scatter(
                        x=h_plot, y=k_plot,
                        mode='lines',
                        line=dict(width=2, color=color),
                        name=peak_id,
                        hoverinfo='name'
                    ))

                # レイアウト調整
                fig_hk.update_layout(
                    title="h-k Index Map (Rectangular)",
                    xaxis_title="Index h",
                    yaxis_title="Index k",
                    xaxis=dict(range=[0, max_index+0.5], dtick=1),
                    yaxis=dict(range=[0, max_index+0.5], dtick=1, scaleanchor="x", scaleratio=1),
                    width=600, height=600,
                    showlegend=True
                )
                
                st.plotly_chart(fig_hk)
                st.write("各色の線は「そのd値においてあり得る(h,k)の組み合わせ」を表します。線が整数グリッド（青点）を通れば、その指数に帰属できます。")
else:
    st.info("👈 サイドバーからCSVまたはTXTファイルをアップロードしてください。")