import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# --- 計算ロジック (単一点計算用) ---
def calc_d_scalar(two_theta, wavelength, n=1):
    try:
        theta_rad = np.radians(two_theta / 2.0)
        sin_theta = np.sin(theta_rad)
        if sin_theta == 0: return None
        return (n * wavelength) / (2.0 * sin_theta)
    except:
        return None

def calc_2theta_scalar(d_value, wavelength, n=1):
    try:
        val = (n * wavelength) / (2.0 * d_value)
        if val > 1.0: return None
        return 2.0 * np.degrees(np.arcsin(val))
    except:
        return None

# --- UI設定 ---
st.set_page_config(page_title="Bragg Calculator (Matplotlib)", page_icon="📉")
st.title("🔬 Bragg's Law 変換")


# --- サイドバー: 波長設定 ---
st.sidebar.header("⚙️ 条件設定")
target = st.sidebar.selectbox("線源", ["Cu (1.5418 Å)", "Mo (0.7107 Å)", "Co (1.7902 Å)", "Custom"])

if "Cu" in target: wavelength = 1.54184
elif "Mo" in target: wavelength = 0.71073
elif "Co" in target: wavelength = 1.79026
else: wavelength = st.sidebar.number_input("波長 (Å)", value=1.54184, format="%.5f")

st.sidebar.write(f"λ = **{wavelength} Å**")

# --- タブ構成 ---
tab1, tab2 = st.tabs(["🔢 数値変換", "📉 グラフプロット"])

# === タブ1: 電卓機能 ===
with tab1:
    st.subheader("単一点の変換")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("2θ → d値")
        t2_in = st.number_input("2θ (deg)", value=20.0, step=0.1, key="t2_in")
        d_out = calc_d_scalar(t2_in, wavelength)
        if d_out:
            st.success(f"d = {d_out:.5f} Å")
            
    with col2:
        st.info("d値 → 2θ")
        d_in = st.number_input("d値 (Å)", value=4.0, step=0.1, key="d_in")
        t2_out = calc_2theta_scalar(d_in, wavelength)
        if t2_out:
            st.success(f"2θ = {t2_out:.2f}°")
        else:
            st.error("回折条件を満たしません")

# === タブ2: Matplotlibグラフ ===
with tab2:
    st.subheader("2θ vs d値 プロット")
    
    # グラフ設定用カラム
    c1, c2 = st.columns(2)
    with c1:
        start_deg = st.number_input("開始角度 (2θ)", value=5.0, min_value=0.1, step=1.0)
    with c2:
        end_deg = st.number_input("終了角度 (2θ)", value=90.0, max_value=179.0, step=1.0)

    # 配列計算 (Numpyを使うと高速かつコードが短い)
    # startからendまで500分割した角度配列を作成
    x = np.linspace(start_deg, end_deg, 500)
    
    # ブラッグの式を一括適用 (d = lambda / 2sin(theta))
    theta_rad = np.radians(x / 2.0)
    y = wavelength / (2.0 * np.sin(theta_rad))

    # --- プロット作成 ---
    # 日本語フォント設定が必要な場合がありますが、ここでは英語ラベルで汎用性を保ちます
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # データプロット
    ax.plot(x, y, label=f'λ = {wavelength} $\AA$', color='blue', linewidth=2)
    
    # 装飾
    ax.set_title("Bragg's Law Relationship", fontsize=14)
    ax.set_xlabel(r"Diffraction Angle $2\theta$ (degrees)", fontsize=12)
    ax.set_ylabel(r"Lattice Spacing $d$ ($\AA$)", fontsize=12)
    ax.grid(True, which='both', linestyle='--', alpha=0.7)
    ax.legend()
    
    # ユーザーが見やすいようにy軸の上限を制限するオプション
    if st.checkbox("Y軸(d値)の範囲を自動調整せず固定する"):
        max_y = st.number_input("Y軸最大値", value=10.0)
        ax.set_ylim(0, max_y)

    # Streamlitに表示
    st.pyplot(fig)

    # おまけ: CSVダウンロード
    csv_data = np.column_stack((x, y))
    st.download_button(
        label="CSVデータをダウンロード",
        data="\n".join([f"{r[0]:.4f},{r[1]:.5f}" for r in csv_data]),
        file_name="bragg_curve.csv",
        mime="text/csv"
    )