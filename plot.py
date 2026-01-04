import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io

# ---------------------------------------------------------
# 設定とタイトル
# ---------------------------------------------------------
st.set_page_config(page_title="XRD Plotter Pro", layout="wide")

st.title("XRD Multi-Plotter (Supports .2ta)")
st.markdown("""
### 使い方
1. サイドバーでデータ形式や**線の色**を設定。
2. データファイルをグレー部分にアップロード。
　　分子研データは，xy形式のファイルが楽。
    分子研のCSV形式データは，29行までヘッダー，またファイルの最後に温度情報があるので，プロットでは削除の必要。
3. プレビューを確認し、画像(PNG)やGnuplotスクリプトをダウンロード。
""")

# ---------------------------------------------------------
# サイドバー: 設定項目
# ---------------------------------------------------------

# --- 1. データ形式 ---
st.sidebar.header("1. Data Format")

use_header = st.sidebar.checkbox("File has Header row?", value=False)
header_row = 0
if use_header:
    header_row = st.sidebar.number_input("Header Row Index", min_value=0, value=0)

limit_rows = st.sidebar.checkbox("Limit rows?", value=False)
nrows_arg = None
if limit_rows:
    nrows_arg = st.sidebar.number_input("Number of rows", min_value=1, value=1000, step=100)

col1, col2 = st.sidebar.columns(2)
with col1:
    x_col_num = st.sidebar.number_input("X Column (2θ)", min_value=1, value=1)
with col2:
    y_col_num = st.sidebar.number_input("Y Column (Int.)", min_value=1, value=2)

st.sidebar.markdown("---")

# --- 2. プロットスタイル ---
st.sidebar.header("2. Plot Style")

offset_val = st.sidebar.number_input("Y-axis Offset", min_value=0.0, value=500.0, step=100.0, format="%.1f")
legend_loc = st.sidebar.radio("Legend Position", ('Inside (Best)', 'Outside (Right)'))
line_width = st.sidebar.slider("Line Width", 0.5, 3.0, 1.0)
font_size = st.sidebar.slider("Font Size", 8, 24, 12)

st.sidebar.markdown("---")

# --- 3. 色設定 ---
st.sidebar.header("3. Color Settings")
color_mode = st.sidebar.radio(
    "Color Mode",
    ("Auto", "All Black", "Custom"),
    help="Auto: 自動色分け, All Black: 全て黒, Custom: 個別に指定"
)

st.sidebar.markdown("---")

# --- 4. 軸設定 ---
st.sidebar.header("4. Axis Settings")
use_manual_range = st.sidebar.checkbox("Manual X-axis Range", value=False)
x_min, x_max = 10.0, 90.0 # Default

if use_manual_range:
    c_min, c_max = st.sidebar.columns(2)
    with c_min:
        x_min = st.sidebar.number_input("X Min (deg)", value=10.0, step=1.0, format="%.1f")
    with c_max:
        x_max = st.sidebar.number_input("X Max (deg)", value=80.0, step=1.0, format="%.1f")


# ---------------------------------------------------------
# データ読み込み関数
# ---------------------------------------------------------
def load_data(uploaded_file, has_header, header_idx, x_col, y_col, nrows=None):
    try:
        header_arg = header_idx if has_header else None
        # sep=None, engine='python' で多様なテキスト形式に対応
        df = pd.read_csv(uploaded_file, header=header_arg, sep=None, engine='python', nrows=nrows)
        
        if not has_header:
            df = df.apply(pd.to_numeric, errors='coerce').dropna()

        max_col = df.shape[1]
        if x_col >= max_col or y_col >= max_col:
            st.error(f"Error in {uploaded_file.name}: 列番号指定が範囲外です。")
            return None

        df_selected = df.iloc[:, [x_col, y_col]].copy()
        df_selected.columns = ["2theta", "Intensity"]
        df_selected["2theta"] = pd.to_numeric(df_selected["2theta"], errors='coerce')
        df_selected["Intensity"] = pd.to_numeric(df_selected["Intensity"], errors='coerce')
        df_selected = df_selected.dropna().sort_values(by="2theta")
        
        return df_selected
    except Exception as e:
        st.error(f"Error reading {uploaded_file.name}: {e}")
        return None

def generate_dummy_data():
    x = np.linspace(10, 80, 500)
    data_list = []
    for i in range(3):
        y = 100 * np.exp(-0.1 * (x - (20 + i*10))**2) + \
            50 * np.exp(-0.1 * (x - (40 + i*5))**2) + \
            np.random.normal(0, 2, len(x)) + 50
        df = pd.DataFrame({"2theta": x, "Intensity": y})
        data_list.append({"name": f"Demo_{i+1}.csv", "data": df})
    return data_list

# ---------------------------------------------------------
# メイン処理: ファイルアップロード
# ---------------------------------------------------------

# ここに '2ta' を追加しました
uploaded_files = st.file_uploader(
    "Upload XRD Data files", 
    type=['txt', 'csv', 'xy', 'dat', '2ta'], 
    accept_multiple_files=True
)

plot_data = []
x_idx = x_col_num - 1
y_idx = y_col_num - 1

if uploaded_files:
    for file in uploaded_files:
        file.seek(0)
        df = load_data(file, use_header, header_row, x_idx, y_idx, nrows=nrows_arg)
        if df is not None:
            plot_data.append({"name": file.name, "data": df})
else:
    st.info("ファイルをアップロードしてください。")
    plot_data = generate_dummy_data()

# ---------------------------------------------------------
# 色の準備 (Custom Mode用)
# ---------------------------------------------------------
custom_colors_list = []

if plot_data and color_mode == "Custom":
    st.sidebar.markdown("##### Custom Colors")
    for i, item in enumerate(plot_data):
        default_c = ["#FF0000", "#0000FF", "#008000", "#FFA500", "#800080"][i % 5]
        picked_color = st.sidebar.color_picker(f"Color: {item['name']}", value=default_c, key=f"color_{i}")
        custom_colors_list.append(picked_color)

# ---------------------------------------------------------
# プロット作成 (Matplotlib)
# ---------------------------------------------------------
if plot_data:
    st.subheader("Interactive Preview")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    N = len(plot_data)
    
    for i in range(N - 1, -1, -1):
        item = plot_data[i]
        df = item['data']
        
        y_shifted = df["Intensity"] + (i * offset_val)
        
        # 色決定
        color_arg = None
        if color_mode == "All Black":
            color_arg = "black"
        elif color_mode == "Custom":
            color_arg = custom_colors_list[i]
            
        ax.plot(df["2theta"], y_shifted, label=item['name'], linewidth=line_width, color=color_arg)

    ax.set_xlabel(r"$2\theta$ (deg.)", fontsize=font_size)
    ax.set_ylabel("Intensity (a.u.)", fontsize=font_size)
    ax.tick_params(labelsize=font_size-2)
    ax.set_yticks([]) 
    
    # 軸範囲の設定
    if use_manual_range:
        ax.set_xlim(x_min, x_max)
    
    # 凡例
    if legend_loc == 'Outside (Right)':
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0., fontsize=font_size-2)
        plt.tight_layout(rect=[0, 0, 0.85, 1])
    else:
        ax.legend(loc='best', fontsize=font_size-2)
        plt.tight_layout()

    st.pyplot(fig)

    # ---------------------------------------------------------
    # 画像ダウンロード
    # ---------------------------------------------------------
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        
        st.download_button(
            label="Download Image (.png)",
            data=img_buffer,
            file_name="xrd_plot.png",
            mime="image/png"
        )

    # ---------------------------------------------------------
    # Gnuplot スクリプト生成
    # ---------------------------------------------------------
    with col_dl2:
        pass

    st.markdown("---")
    st.subheader("Export for Gnuplot")
    st.markdown("現在の設定（色・表示範囲含む）を反映したGnuplotスクリプトです。")

    gnuplot_script = f"""# XRD Plot Script generated by Streamlit
set terminal pdfcairo enhanced color font "Arial,{int(font_size+2)}" size 5in,3.5in
set output 'xrd_plot.pdf'

set xlabel "2{{/Symbol q}} (deg.)"
set ylabel "Intensity (a.u.)"
set ytics format ""

"""
    # 範囲設定
    if use_manual_range:
        gnuplot_script += f"set xrange [{x_min}:{x_max}]\n"

    # 凡例設定
    if legend_loc == 'Outside (Right)':
        gnuplot_script += "set key outside right top\n"
    else:
        gnuplot_script += "set key right top\n"

    gnuplot_script += "\nplot \\\n"
    
    data_blocks = ""
    
    for i in range(N - 1, -1, -1):
        item = plot_data[i]
        block_name = f"DATA_{i}"
        offset_math = f"{i * offset_val}"
        
        # 色指定
        lc_str = ""
        if color_mode == "All Black":
            lc_str = " lc rgb 'black'"
        elif color_mode == "Custom":
            hex_c = custom_colors_list[i]
            lc_str = f" lc rgb '{hex_c}'"
        
        gnuplot_script += f"    ${block_name} using 1:($2 + {offset_math}) with lines lw {line_width}{lc_str} title '{item['name']}'"
        
        if i > 0:
            gnuplot_script += ", \\\n"
        else:
            gnuplot_script += "\n"
            
        data_str = item['data'].to_csv(sep='\t', index=False, header=False)
        data_blocks += f"${block_name} << EOD\n{data_str}EOD\n\n"

    final_script = gnuplot_script + "\n" + data_blocks

    st.download_button(
        label="Download Gnuplot Script (.plt)",
        data=final_script,
        file_name="xrd_plot.plt",
        mime="text/plain"
    )