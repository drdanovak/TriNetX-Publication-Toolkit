import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

plt.style.use("seaborn-v0_8-whitegrid")
st.set_page_config(layout="wide")
st.title("🌲 Novak's TriNetX Forest Plot Generator")

input_mode = st.radio(
    "Select data input method:", ["📤 Upload file", "✍️ Manual entry"], index=1, horizontal=True
)

required_cols = [
    "Outcome",
    "Risk, Odds, or Hazard Ratio",
    "Effect Size (Cohen's d, approx.)",
    "Lower CI",
    "Upper CI"
]
df = None

def compute_cohens_d(rr):
    try:
        if pd.isnull(rr):
            return np.nan
        val = float(rr)
        return np.log(val) * (np.sqrt(3) / np.pi)
    except Exception:
        return np.nan

if input_mode == "📤 Upload file":
    uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            # Add Effect Size column if missing, after RR/OR/HR
            if "Effect Size (Cohen's d, approx.)" not in df.columns:
                idx = df.columns.get_loc("Risk, Odds, or Hazard Ratio") + 1
                df.insert(idx, "Effect Size (Cohen's d, approx.)", df["Risk, Odds, or Hazard Ratio"].apply(compute_cohens_d))
            # Ensure all required columns are present and in order
            for col in required_cols:
                if col not in df.columns:
                    df[col] = np.nan
            df = df[required_cols]
        except Exception as e:
            st.error(f"Error reading file: {e}")
else:
    default_data = pd.DataFrame({
        "Outcome": ["## Cardiovascular", "Hypertension", "Stroke", "## Metabolic", "Diabetes", "Obesity"],
        "Risk, Odds, or Hazard Ratio": [None, 1.5, 1.2, None, 0.85, 1.2],
        "Lower CI": [None, 1.2, 1.0, None, 0.7, 1.0],
        "Upper CI": [None, 1.8, 1.5, None, 1.0, 1.4],
    })
    # Compute Cohen's d and reorder columns
    default_data["Effect Size (Cohen's d, approx.)"] = default_data["Risk, Odds, or Hazard Ratio"].apply(compute_cohens_d)
    default_data = default_data[[
        "Outcome",
        "Risk, Odds, or Hazard Ratio",
        "Effect Size (Cohen's d, approx.)",
        "Lower CI",
        "Upper CI"
    ]]
    if "manual_table" not in st.session_state:
        st.session_state.manual_table = default_data.copy()
    col1, col2 = st.columns([2, 1])
    with col2:
        if st.button("🧹 Clear Table"):
            st.session_state.manual_table = pd.DataFrame({col: [None]*6 for col in required_cols})
    manual_df = st.session_state.manual_table.copy()
    manual_df["Effect Size (Cohen's d, approx.)"] = manual_df["Risk, Odds, or Hazard Ratio"].apply(compute_cohens_d)
    manual_df = manual_df[required_cols]
    st.session_state.manual_table = st.data_editor(
        manual_df,
        num_rows="dynamic",
        use_container_width=True,
        key="manual_input_table",
        column_config={
            "Effect Size (Cohen's d, approx.)": st.column_config.NumberColumn(
                "Effect Size (Cohen's d, approx.)",
                disabled=True,
                help="Auto-calculated as ln(RR/OR/HR) × sqrt(3)/π",
            )
        }
    )
    df = st.session_state.manual_table

if df is not None:
    st.sidebar.header("⚙️ Basic Plot Settings")

    x_measure = st.sidebar.radio(
        "Plot on X-axis",
        ("Effect Size (Cohen's d, approx.)", "Risk, Odds, or Hazard Ratio"),
        index=0
    )

    plot_title = st.sidebar.text_input("Plot Title", value="Forest Plot")
    show_grid = st.sidebar.checkbox("Show Grid", value=True)
    show_values = st.sidebar.checkbox("Show Numerical Annotations", value=False)
    use_groups = st.sidebar.checkbox("Treat rows starting with '##' as section headers", value=True)

    with st.sidebar.expander("🎨 Advanced Visual Controls", expanded=False):
        color_scheme = st.selectbox("Color Scheme", ["Color", "Black & White"])
        point_size = st.slider("Marker Size", 6, 20, 10)
        line_width = st.slider("CI Line Width", 1, 4, 2)
        font_size = st.slider("Font Size", 10, 20, 12)
        label_offset = st.slider("Label Horizontal Offset", 0.01, 0.3, 0.05)
        use_log = st.checkbox("Use Log Scale for X-axis", value=(x_measure != "Effect Size (Cohen's d, approx.)"))
        axis_padding = st.slider("X-axis Padding (%)", 2, 40, 10)
        y_axis_padding = st.slider("Y-axis Padding (Rows)", 0.0, 5.0, 1.0, step=0.5)
        cap_height = st.slider("Tick Height (for CI ends)", 0.05, 0.5, 0.18, step=0.01)
        if color_scheme == "Color":
            ci_color = st.color_picker("CI Color", "#1f77b4")
            marker_color = st.color_picker("Point Color", "#d62728")
        else:
            ci_color = "black"
            marker_color = "black"

    # Axis and plot variables based on toggle
    if x_measure == "Effect Size (Cohen's d, approx.)":
        plot_column = "Effect Size (Cohen's d, approx.)"
        # Convert CI columns to Cohen's d
        ci_l = df["Lower CI"].apply(compute_cohens_d)
        ci_u = df["Upper CI"].apply(compute_cohens_d)
        ci_vals = pd.concat([ci_l.dropna(), ci_u.dropna(), df[plot_column].dropna()])
        ref_line = 0
    else:
        plot_column = "Risk, Odds, or Hazard Ratio"
        ci_l = df["Lower CI"]
        ci_u = df["Upper CI"]
        ci_vals = pd.concat([ci_l.dropna(), ci_u.dropna(), df[plot_column].dropna()])
        ref_line = 1

    x_axis_label = plot_column

    if st.button("📊 Generate Forest Plot"):
        rows = []
        y_labels = []
        text_styles = []
        indent = "\u00A0" * 4
        group_mode = False

        for i, row in df.iterrows():
            if use_groups and isinstance(row["Outcome"], str) and row["Outcome"].startswith("##"):
                header = row["Outcome"][3:].strip()
                y_labels.append(header)
                text_styles.append("bold")
                rows.append(None)
                group_mode = True
            else:
                display_name = f"{indent}{row['Outcome']}" if group_mode else row["Outcome"]
                y_labels.append(display_name)
                text_styles.append("normal")
                rows.append(row)

        fig, ax = plt.subplots(figsize=(10, len(y_labels) * 0.7))
        valid_rows = [i for i in range(len(rows)) if rows[i] is not None]

        # Use the correct scale for axis limits!
        x_min, x_max = ci_vals.min(), ci_vals.max()
        x_pad = (x_max - x_min) * (axis_padding / 100)
        ax.set_xlim(x_min - x_pad, x_max + x_pad)

        # Always plot marker and lines on correct scale
        for i, row in enumerate(rows):
            if row is None:
                continue

            if x_measure == "Effect Size (Cohen's d, approx.)":
                effect = row.get("Effect Size (Cohen's d, approx.)", np.nan)
                lci = compute_cohens_d(row.get("Lower CI", np.nan))
                uci = compute_cohens_d(row.get("Upper CI", np.nan))
            else:
                effect = row.get("Risk, Odds, or Hazard Ratio", np.nan)
                lci = row.get("Lower CI", np.nan)
                uci = row.get("Upper CI", np.nan)

            if pd.notnull(lci) and pd.notnull(uci):
                ax.hlines(i, xmin=lci, xmax=uci, color=ci_color, linewidth=line_width, capstyle='round')
                ax.vlines([lci, uci], [i - cap_height, i - cap_height], [i + cap_height, i + cap_height], color=ci_color, linewidth=line_width)

            if pd.notnull(effect):
                ax.plot(effect, i, 'o', color=marker_color, markersize=point_size, zorder=3)
                if show_values and pd.notnull(lci) and pd.notnull(uci):
                    label = f"{effect:.2f} [{lci:.2f}, {uci:.2f}]"
                    ax.text(uci + label_offset, i, label, va='center', fontsize=font_size - 2)

        ax.axvline(x=ref_line, color='gray', linestyle='--', linewidth=1)

        ax.set_yticks(range(len(y_labels)))
        for tick_label, style in zip(ax.set_yticklabels(y_labels), text_styles):
            if style == "bold":
                tick_label.set_fontweight("bold")
            tick_label.set_fontsize(font_size)

        if use_log:
            try:
                ax.set_xscale('log')
            except Exception:
                st.warning("Log scale is only valid for positive numbers.")
        if show_grid:
            ax.grid(True, axis='x', linestyle=':', linewidth=0.6)
        else:
            ax.grid(False)

        ax.set_ylim(len(y_labels) - 1 + y_axis_padding, -1 - y_axis_padding)
        ax.set_xlabel(x_axis_label, fontsize=font_size)
        ax.set_title(plot_title, fontsize=font_size + 2, weight='bold')
        fig.tight_layout()
        st.pyplot(fig)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300)
        st.download_button("📥 Download Plot as PNG", data=buf.getvalue(), file_name="forest_plot.png", mime="image/png")
else:
    st.info("Please upload a file or enter data manually to generate a plot.")
