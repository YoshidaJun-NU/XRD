import streamlit as st
import math

# --- 計算ロジック ---
def calc_d_from_twotheta(two_theta, wavelength, n=1):
    try:
        theta_rad = math.radians(two_theta / 2.0)
        sin_theta = math.sin(theta_rad)
        if sin_theta == 0:
            return float('inf')
        d = (n * wavelength) / (2.0 * sin_theta)
        return d
    except Exception:
        return None

def calc_twotheta_from_d(d_value, wavelength, n=1):
    try:
        val = (n * wavelength) / (2.0 * d_value)
        if val > 1.0:
            return None # 物理的に回折不可能
        theta_rad = math.asin(val)
        two_theta = 2.0 * math.degrees(theta_rad)
        return two_theta
    except (ValueError, ZeroDivisionError):
        return None

# --- UI設定 ---
st.set_page_config(page_title="Bragg's Law Calculator", page_icon="🔬")

st.title("🔬 ブラッグの法則 計算機")
st.markdown("X線回折における **2θ (回折角)** と **d値 (格子面間隔)** を相互変換します。")

# --- サイドバー: 波長設定 ---
st.sidebar.header("⚙️ 設定")
st.sidebar.markdown("X線の波長 (λ) を設定してください。")

wavelength_preset = st.sidebar.selectbox(
    "線源プリセット",
    ("Cu Kα (1.5418 Å)", "Mo Kα (0.7107 Å)", "Co Kα (1.7902 Å)", "Custom")
)

# プリセットに応じた波長の値
if "Cu" in wavelength_preset:
    default_lambda = 1.54184
elif "Mo" in wavelength_preset:
    default_lambda = 0.71073
elif "Co" in wavelength_preset:
    default_lambda = 1.79026
else:
    default_lambda = 1.54184

# 波長の数値入力 (Customを選んだ場合に変更可能)
wavelength = st.sidebar.number_input(
    "波長 λ (Å)",
    value=default_lambda,
    format="%.5f",
    step=0.00001
)

st.sidebar.markdown("---")
st.sidebar.write(f"現在の波長: **{wavelength} Å**")

# --- 数式の表示 ---
st.markdown("### ブラッグの式")
st.latex(r"2d \sin\theta = n\lambda")

# --- メインエリア: タブによる機能切り替え ---
tab1, tab2 = st.tabs(["2θ → d値 変換", "d値 → 2θ 変換"])

# === タブ1: 2theta -> d ===
with tab1:
    st.subheader("2θ から d値を計算")
    
    col1, col2 = st.columns(2)
    with col1:
        input_2theta = st.number_input(
            "2θ (度) を入力", 
            min_value=0.01, 
            max_value=179.9, 
            value=20.0, 
            step=0.1,
            format="%.2f"
        )
    
    # 計算実行
    result_d = calc_d_from_twotheta(input_2theta, wavelength)
    
    with col2:
        st.write("結果 (d値):")
        if result_d:
            st.success(f"d = {result_d:.5f} Å")
        else:
            st.error("計算エラー")

    # 補足情報: q値の計算なども容易に追加可能
    if result_d:
        st.info(f"参考: 1/d = {1/result_d:.4f} Å⁻¹")

# === タブ2: d -> 2theta ===
with tab2:
    st.subheader("d値 から 2θ を計算")
    
    col1, col2 = st.columns(2)
    with col1:
        input_d = st.number_input(
            "d値 (Å) を入力", 
            min_value=0.1, 
            value=4.0, 
            step=0.1,
            format="%.4f"
        )

    # 計算実行
    result_2theta = calc_twotheta_from_d(input_d, wavelength)

    with col2:
        st.write("結果 (2θ):")
        if result_2theta:
            st.success(f"2θ = {result_2theta:.2f}°")
        else:
            st.error(f"計算不可 (d < λ/2)。波長 {wavelength}Å に対してd値が小さすぎます。")

    if result_2theta:
        st.info(f"計算条件: λ = {wavelength} Å, n = 1")

# --- フッター ---
st.markdown("---")
st.caption("Created with Python & Streamlit")