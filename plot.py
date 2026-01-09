import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import io
from scipy.signal import find_peaks
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. ページ設定
# ---------------------------------------------------------
st.set_page_config(page_title="XRD Plotter", layout="wide")
st.title("🔬 XRD Multi-Plotter")

# ---------------------------------------------------------
# 2. 関数：データ読み込み & エクスポート
# ---------------------------------------------------------
def load_xrd_data_full(uploaded_file):
    try:
        content = ""
        for enc in ['utf-8', 'cp932', 'shift_jis']:
            try:
                uploaded_file.seek(0)
                content = uploaded_file.read().decode(enc)
                break
            except: continue
        if not content: return None
        lines = content.splitlines()
        data_start_idx = 0
        for i, line in enumerate(lines):
            parts = line.replace('\t', ',').replace(' ', ',').split(',')
            parts = [p for p in parts if p.strip()]
            if len(parts) >= 2:
                try:
                    float(parts[0].strip()); float(parts[1].strip())
                    data_start_idx = i
                    break
                except ValueError: continue
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, skiprows=data_start_idx, header=None, sep=None, engine='python')
        df = df.apply(pd.to_numeric, errors='coerce').dropna(axis=0, how='any')
        if df.empty: return None
        df.columns = [f"Column {i}" for i in range(df.shape[1])]
        return df
    except Exception as e:
        st.error(f"Error parsing {uploaded_file.name}: {e}")
        return None

def generate_gnuplot_script(selected_data, styles, x_range, y_offset, show_legend, show_y_axis):
    legend_cmd = "set key linestyle -1" if show_legend else "unset key"
    y_tick_cmd = "" if show_y_axis else "unset ytics\nunset ylabels"
    script = f"""# Gnuplot script
set terminal pngcairo enhanced font 'Arial,12' size 800,600
set output 'xrd_plot.png'
set xlabel "2{{/Symbol q}} (deg.)"
set ylabel "Intensity (a.u.)"
set xrange [{x_range[0]}:{x_range[1]}]
{legend_cmd}
{y_tick_cmd}
"""
    plot_cmds = []
    for i, d in enumerate(selected_data):
        s = styles[d['name']]
        offset = i * y_offset
        plot_cmds.append(f"'processed_data.csv' u 1:(${i+2} * {s['scale']} + {offset}) w l lc rgb '{s['color']}' lw {s['lw']} title '{d['name']}'")
    script += "plot " + ", \\\n     ".join(plot_cmds)
    return script

# ---------------------------------------------------------
# 3. サイドバー設定
# ---------------------------------------------------------
st.sidebar.header("1. Data Import")
uploaded_files = st.sidebar.file_uploader("ファイルを読み込む", type=['csv', 'txt', 'dat', 'xy', '2ta'], accept_multiple_files=True)

all_data = []
if uploaded_files:
    for f in uploaded_files:
        df = load_xrd_data_full(f)
        if df is not None:
            all_data.append({"name": f.name, "df": df})

selected_data = []
individual_styles = {}

if all_data:
    st.sidebar.header("2. Individual Styling")
    max_cols = max([d["df"].shape[1] for d in all_data])
    x_col = st.sidebar.selectbox("X軸 (2θ)", [f"Column {i}" for i in range(max_cols)], index=0)
    y_col = st.sidebar.selectbox("Y軸 (Intensity)", [f"Column {i}" for i in range(max_cols)], index=1 if max_cols > 1 else 0)

    for i, d in enumerate(all_data):
        if st.sidebar.checkbox(d["name"], value=True, key=f"cb_{i}"):
            with st.sidebar.expander(f"🎨 {d['name']}"):
                sc = st.number_input("強度倍率", value=1.0, step=0.1, key=f"sc_{i}")
                cp = st.color_picker("プロット色", mcolors.to_hex(plt.cm.tab10(i % 10)), key=f"cp_{i}")
                lw = st.slider("線の太さ", 0.5, 5.0, 1.5, key=f"lw_{i}")
                individual_styles[d['name']] = {"scale": sc, "color": cp, "lw": lw}
                selected_data.append(d)

    st.sidebar.header("3. Global Style Settings")
    with st.sidebar.expander("🛠 表示・フォントの詳細設定", expanded=True):
        font_family = st.selectbox("フォント種類", ["Arial", "sans-serif", "serif", "monospace", "Times New Roman"])
        label_font_size = st.slider("軸ラベル文字サイズ (2θ等)", 10, 40, 20)
        tick_font_size = st.slider("目盛り数字サイズ", 8, 30, 16)
        legend_font_size = st.slider("凡例文字サイズ", 8, 30, 14)
        show_grid = st.checkbox("目盛り線 (Grid) を表示", value=True)
        show_legend = st.checkbox("凡例 (Legend) を表示", value=True)
        show_y_axis = st.checkbox("縦軸の数値・目盛りを表示", value=True)

    st.sidebar.header("4. X-Axis Range")
    all_x = pd.concat([d["df"][x_col] for d in selected_data])
    min_x_orig, max_x_orig = float(all_x.min()), float(all_x.max())
    
    c_in1, c_in2 = st.sidebar.columns(2)
    with c_in1:
        manual_min = st.number_input("Min X", value=min_x_orig, step=1.0)
    with c_in2:
        manual_max = st.number_input("Max X", value=max_x_orig, step=1.0)
    x_range = st.sidebar.slider("表示範囲 (バー操作)", min_x_orig, max_x_orig, (manual_min, manual_max), step=0.01)

    y_offset = st.sidebar.number_input("積み上げオフセット", value=0.0, step=100.0)
    use_peak_finder = st.sidebar.checkbox("ピーク検出を表示", value=False)
    peak_prom = st.sidebar.number_input("ピーク検出感度", value=50.0, step=10.0) if use_peak_finder else 0

# ---------------------------------------------------------
# 4. メイン表示 (Plotly)
# ---------------------------------------------------------
if selected_data:
    st.subheader("🔍 Interactive View")
    fig_plotly = go.Figure()
    export_df = pd.DataFrame()
    
    # 軸ラベル定義
    x_label_html = "2<i>θ</i> (deg.)"
    y_label_html = "Intensity (a.u.)"

    for i, d in enumerate(selected_data):
        style = individual_styles[d['name']]
        x = d["df"][x_col]
        y_scaled = d["df"][y_col] * style["scale"]
        y_disp = y_scaled + (i * y_offset)
        
        fig_plotly.add_trace(go.Scatter(
            x=x, y=y_disp, name=d["name"], mode='lines',
            line=dict(color=style["color"], width=style["lw"]),
            hovertemplate = '2θ: %{x:.3f}<br>Int: %{y:.1f}'
        ))
        if i == 0: export_df['2theta'] = x
        export_df[d['name']] = d["df"][y_col]

    fig_plotly.update_layout(
        xaxis=dict(
            title=dict(text=x_label_html, font=dict(size=label_font_size, family=font_family)),
            range=x_range, showgrid=show_grid, gridcolor='rgba(0,0,0,0.1)',
            tickfont=dict(size=tick_font_size, family=font_family)
        ),
        yaxis=dict(
            title=dict(text=y_label_html if show_y_axis else "", font=dict(size=label_font_size, family=font_family)),
            showgrid=show_grid if show_y_axis else False,
            showticklabels=show_y_axis,
            ticks="outside" if show_y_axis else "",
            gridcolor='rgba(0,0,0,0.1)',
            tickfont=dict(size=tick_font_size, family=font_family)
        ),
        font=dict(family=font_family, size=legend_font_size),
        showlegend=show_legend,
        height=650, template="plotly_white", hovermode="x unified"
    )
    st.plotly_chart(fig_plotly, use_container_width=True)

    # ---------------------------------------------------------
    # 5. エクスポート機能 (Matplotlib)
    # ---------------------------------------------------------
    st.divider()
    st.subheader("💾 Export Options")
    c1, c2, c3 = st.columns(3)

    with c1:
        # 画像保存処理の再構築
        # plt.figureの代わりに明示的にフォントを指定
        fig_mpl, ax = plt.subplots(figsize=(10, 6))
        
        # フォント設定を明示的に適用
        plt.rcParams['font.family'] = font_family
        
        for i, d in enumerate(selected_data):
            style = individual_styles[d['name']]
            ax.plot(d["df"][x_col], (d["df"][y_col] * style["scale"]) + (i * y_offset),
                    color=style["color"], linewidth=style["lw"], label=d["name"])
        
        ax.set_xlim(x_range)
        # ラベルとフォントサイズを個別に設定
        ax.set_xlabel(r'2$\theta$ (deg.)', fontsize=label_font_size, fontname=font_family)
        
        if show_y_axis:
            ax.set_ylabel("Intensity (a.u.)", fontsize=label_font_size, fontname=font_family)
            ax.tick_params(axis='both', which='major', labelsize=tick_font_size)
        else:
            ax.set_yticklabels([])
            ax.tick_params(left=False)
            ax.set_ylabel("") # ラベルも消す

        if show_grid:
            ax.grid(True, alpha=0.3)
        if show_legend:
            ax.legend(prop={'size': legend_font_size, 'family': font_family}, frameon=False)
        
        # 目盛りフォントを強制適用
        for label in (ax.get_xticklabels() + ax.get_yticklabels()):
            label.set_fontname(font_family)

        dpi_val = st.select_slider("保存解像度 (DPI)", [72, 150, 300, 600], value=300)
        buf = io.BytesIO()
        # bbox_inches='tight'を入れることでラベルが切れるのを防ぐ
        fig_mpl.savefig(buf, format="png", dpi=dpi_val, bbox_inches='tight')
        st.download_button("🖼 画像を保存 (PNG)", buf.getvalue(), "xrd_plot.png", "image/png")

    with c2:
        gp_script = generate_gnuplot_script(selected_data, individual_styles, x_range, y_offset, show_legend, show_y_axis)
        st.download_button("📜 gnuplotスクリプト保存", gp_script, "xrd_analysis.gp", "text/plain")

    with c3:
        csv_data = export_df.to_csv(index=False).encode('utf-8')
        st.download_button("📊 生データ(CSV)保存", csv_data, "xrd_combined.csv", "text/csv")

else:
    st.info("サイドバーからデータをアップロードしてください。")