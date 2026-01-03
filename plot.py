import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io

# ---------------------------------------------------------
# 設定とタイトル
# ---------------------------------------------------------
st.set_page_config(page_title="XRD Plotter Pro", layout="wide")

st.title("XRD Multi-Plotter (Custom Columns & Header)")
st.markdown("""
### 使い方
1. サイドバーの **"Data Format Settings"** で、データの列位置やヘッダー行を指定します。
2. XRDデータファイル（csv, txt, xy, datなど）をアップロードします。
3. 自動で列を抽出し、プロットを作成します。
""")

# ---------------------------------------------------------
# サイドバー: 設定項目
# ---------------------------------------------------------
st.sidebar.header("1. Data Format Settings")

# ヘッダー設定
use_header = st.sidebar.checkbox("File has Header row?", value=False)
header_row = 0
if use_header:
    header_row = st.sidebar.number_input(
        "Header Row Index (0=1st line)", 
        min_value=0, value=0, step=1,
        help="列名が書かれている行番号を指定します（0始まり）"
    )

# 列の選択（ユーザーにはわかりやすく1始まりで入力させ、内部で-1する）
col1, col2 = st.sidebar.columns(2)
with col1:
    x_col_num = st.sidebar.number_input("X Column (2θ)", min_value=1, value=1, step=1)
with col2:
    y_col_num = st.sidebar.number_input("Y Column (Int.)", min_value=1, value=2, step=1)

st.sidebar.markdown("---")
st.sidebar.header("2. Plot Style")

# オフセット設定
offset_val = st.sidebar.number_input(
    "Y-axis Offset", 
    min_value=0.0, 
    value=500.0, 
    step=100.0,
    format="%.1f"
)

# 凡例の設定
legend_loc = st.sidebar.radio(
    "Legend Position",
    ('Inside (Best)', 'Outside (Right)')
)

# 見た目設定
line_width = st.sidebar.slider("Line Width", 0.5, 3.0, 1.0)
font_size = st.sidebar.slider("Font Size", 8, 24, 12)

# ---------------------------------------------------------
# データ読み込み関数
# ---------------------------------------------------------
def load_data(uploaded_file, has_header, header_idx, x_col, y_col):
    """
    指定された列とヘッダー設定に基づいてデータを読み込む
    x_col, y_col は 0始まりのインデックス
    """
    try:
        # ヘッダー指定の処理
        header_arg = header_idx if has_header else None
        
        # データの読み込み (sep=Noneで自動判定)
        df = pd.read_csv(uploaded_file, header=header_arg, sep=None, engine='python')
        
        # ヘッダーなしとして読み込んだ場合、数値以外の行が混じると困るので
        # 強制的に数値変換してエラー行（文字列ヘッダーなど）を除去する処理を入れる
        if not has_header:
            df = df.apply(pd.to_numeric, errors='coerce').dropna()

        # 指定された列が存在するかチェック
        max_col = df.shape[1]
        if x_col >= max_col or y_col >= max_col:
            st.error(
                f"Error in {uploaded_file.name}: 指定された列番号が存在しません。\n"
                f"データは {max_col} 列ですが、列 {x_col+1} や {y_col+1} を指定しています。"
            )
            return None

        # 指定列を抽出
        df_selected = df.iloc[:, [x_col, y_col]].copy()
        df_selected.columns = ["2theta", "Intensity"]
        
        # データのクリーニング（数値化とNaN除去）
        df_selected["2theta"] = pd.to_numeric(df_selected["2theta"], errors='coerce')
        df_selected["Intensity"] = pd.to_numeric(df_selected["Intensity"], errors='coerce')
        df_selected = df_selected.dropna()
        
        # 2theta順にソート
        df_selected = df_selected.sort_values(by="2theta")
        
        return df_selected

    except Exception as e:
        st.error(f"Error reading {uploaded_file.name}: {e}")
        return None

def generate_dummy_data():
    """デモ用のダミーデータ生成"""
    x = np.linspace(10, 80, 500)
    data_list = []
    for i in range(3):
        y = 100 * np.exp(-0.1 * (x - (20 + i*10))**2) + \
            50 * np.exp(-0.1 * (x - (40 + i*5))**2) + \
            np.random.normal(0, 2, len(x)) + 50
        # 3列のデータを作成してみる (Index, 2theta, Intensity)
        df = pd.DataFrame({"Index": range(len(x)), "2theta": x, "Intensity": y})
        # デモ用に列を少し複雑にする（2列目と3列目を使う想定）
        data_list.append({"name": f"Demo_Data_{i+1}.csv", "data": df.iloc[:, 1:]}) # デモ表示用は整形済みとして扱う
    return data_list

# ---------------------------------------------------------
# メイン処理
# ---------------------------------------------------------

# ファイルアップローダー
uploaded_files = st.file_uploader(
    "Upload XRD Data files (txt, csv, xy, dat)", 
    type=['txt', 'csv', 'xy', 'dat'], 
    accept_multiple_files=True
)

plot_data = []

# ユーザー入力は1始まりなので、0始まりのインデックスに変換
x_idx = x_col_num - 1
y_idx = y_col_num - 1

if uploaded_files:
    for file in uploaded_files:
        # ファイルポインタを先頭に戻す（再読み込み時用）
        file.seek(0)
        df = load_data(file, use_header, header_row, x_idx, y_idx)
        if df is not None:
            plot_data.append({"name": file.name, "data": df})
else:
    st.info("ファイルをアップロードしてください。以下はダミーデータのデモです。")
    # ダミーデータの場合は設定に関わらず表示できるように簡易処理
    dummy = generate_dummy_data()
    plot_data = dummy

# ---------------------------------------------------------
# Matplotlib プロット作成
# ---------------------------------------------------------
if plot_data:
    st.subheader("Interactive Preview (Matplotlib)")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # データをプロット (reversedで積み上げ順を調整)
    for i, item in enumerate(reversed(plot_data)):
        df = item['data']
        # オフセット処理
        y_shifted = df["Intensity"] + (i * offset_val)
        ax.plot(df["2theta"], y_shifted, label=item['name'], linewidth=line_width)

    ax.set_xlabel(r"$2\theta$ (deg.)", fontsize=font_size)
    ax.set_ylabel("Intensity (a.u.)", fontsize=font_size)
    ax.tick_params(labelsize=font_size-2)
    ax.set_yticks([]) # Y軸の数値はオフセット時は非表示
    
    # 凡例
    if legend_loc == 'Outside (Right)':
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0., fontsize=font_size-2)
        plt.tight_layout(rect=[0, 0, 0.85, 1])
    else:
        ax.legend(loc='best', fontsize=font_size-2)
        plt.tight_layout()

    st.pyplot(fig)

    st.markdown("---")

    # ---------------------------------------------------------
    # Gnuplot スクリプト生成
    # ---------------------------------------------------------
    st.subheader("Export for Gnuplot")
    st.markdown("現在表示されているデータ（抽出・整形済み）を使用してGnuplotスクリプトを生成します。")

    gnuplot_script = f"""# XRD Plot Script generated by Streamlit
set terminal pdfcairo enhanced color font "Arial,{int(font_size+2)}" size 5in,3.5in
set output 'xrd_plot.pdf'

set xlabel "2{{/Symbol q}} (deg.)"
set ylabel "Intensity (a.u.)"
set ytics format ""

# Legend settings
"""
    if legend_loc == 'Outside (Right)':
        gnuplot_script += "set key outside right top\n"
    else:
        gnuplot_script += "set key right top\n"

    gnuplot_script += "\nplot \\\n"
    
    data_blocks = ""
    
    for i, item in enumerate(reversed(plot_data)):
        block_name = f"DATA_{i}"
        offset_math = f"{i * offset_val}"
        
        gnuplot_script += f"    ${block_name} using 1:($2 + {offset_math}) with lines lw {line_width} title '{item['name']}'"
        
        if i < len(plot_data) - 1:
            gnuplot_script += ", \\\n"
        else:
            gnuplot_script += "\n"
            
        # データブロック出力（ここでは既に抽出済みの2列データを出力する）
        data_str = item['data'].to_csv(sep='\t', index=False, header=False)
        data_blocks += f"${block_name} << EOD\n{data_str}EOD\n\n"

    final_script = gnuplot_script + "\n" + data_blocks

    st.download_button(
        label="Download Gnuplot Script (.plt)",
        data=final_script,
        file_name="xrd_plot.plt",
        mime="text/plain"
    )