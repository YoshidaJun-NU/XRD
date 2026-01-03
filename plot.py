import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io

# ---------------------------------------------------------
# 設定とタイトル
# ---------------------------------------------------------
st.set_page_config(page_title="XRD Plotter", layout="wide")

st.title("XRD Multi-Plotter (Supports TXT & CSV)")
st.markdown("""
### 使い方
1. サイドバーでグラフの見た目（オフセット、線の太さなど）を調整します。
2. 下のエリアにXRDデータファイル（**txt, csv, xy, dat**）をドラッグ＆ドロップします。
3. データの区切り文字（カンマやスペース）は自動判別されます。
""")

# ---------------------------------------------------------
# サイドバー: 設定項目
# ---------------------------------------------------------
st.sidebar.header("Plot Settings")

# オフセット設定
offset_val = st.sidebar.number_input(
    "Y-axis Offset (Intensity)", 
    min_value=0.0, 
    value=500.0, 
    step=100.0,
    format="%.1f",
    help="各データ間の縦方向の間隔を設定します"
)

# 凡例の設定
legend_loc = st.sidebar.radio(
    "Legend Position",
    ('Inside (Best)', 'Outside (Right)')
)

# 線の太さ
line_width = st.sidebar.slider("Line Width", 0.5, 3.0, 1.0)

# フォントサイズ
font_size = st.sidebar.slider("Font Size", 8, 20, 12)

# ---------------------------------------------------------
# データ読み込み・生成関数
# ---------------------------------------------------------
def load_data(uploaded_file):
    """アップロードされたファイルをPandas DataFrameに変換"""
    try:
        # sep=None, engine='python'を指定することで、
        # カンマ区切り(csv)でもスペース区切り(txt)でも自動判定して読み込みます
        df = pd.read_csv(uploaded_file, header=None, sep=None, engine='python')
        
        # 数値以外の行（ヘッダー文字列など）が含まれている場合の簡易対策
        # データをすべて数値に変換し、エラーが出る行（文字列）をNaNにして削除
        df = df.apply(pd.to_numeric, errors='coerce').dropna()

        # データが2列以上あるか確認
        if df.shape[1] < 2:
            st.error(f"{uploaded_file.name}: データ列が足りません (2列必要: 2theta, Intensity)")
            return None
            
        # 最初の2列だけ抽出
        df = df.iloc[:, :2]
        df.columns = ["2theta", "Intensity"]
        
        # 2theta順にソート（念のため）
        df = df.sort_values(by="2theta")
        
        return df
    except Exception as e:
        st.error(f"Error reading {uploaded_file.name}: {e}")
        return None

def generate_dummy_data():
    """テスト用のダミーデータを生成"""
    x = np.linspace(10, 80, 500)
    data_list = []
    for i in range(3):
        # ガウス分布で適当なピークを作る
        y = 100 * np.exp(-0.1 * (x - (20 + i*10))**2) + \
            50 * np.exp(-0.1 * (x - (40 + i*5))**2) + \
            np.random.normal(0, 2, len(x)) + 50
        df = pd.DataFrame({"2theta": x, "Intensity": y})
        data_list.append({"name": f"Demo_Data_{i+1}.txt", "data": df})
    return data_list

# ---------------------------------------------------------
# メイン処理
# ---------------------------------------------------------

# ファイルアップローダー
# type引数で許可する拡張子を指定します
uploaded_files = st.file_uploader(
    "Upload XRD Data files", 
    type=['txt', 'csv', 'xy', 'dat'], 
    accept_multiple_files=True
)

plot_data = []

if uploaded_files:
    for file in uploaded_files:
        df = load_data(file)
        if df is not None:
            plot_data.append({"name": file.name, "data": df})
else:
    st.info("ファイルをアップロードしてください。以下はダミーデータのデモ表示です。")
    plot_data = generate_dummy_data()

# ---------------------------------------------------------
# Matplotlib プロット作成
# ---------------------------------------------------------
if plot_data:
    st.subheader("Interactive Preview (Matplotlib)")
    
    fig, ax = plt.subplots(figsize=(10, 6))