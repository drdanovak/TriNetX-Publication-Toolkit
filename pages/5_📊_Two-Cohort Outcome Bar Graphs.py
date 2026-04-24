import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO, StringIO
from matplotlib.ticker import AutoMinorLocator

# ---------- COLOR PALETTES ----------
PALETTES = {
    "Classic TriNetX": ["#8e44ad", "#27ae60"],
    "University of California": ["#1295D8", "#FFB511"],
    "Colorblind-safe": ["#0072B2", "#D55E00"],
    "Tol (bright)": ["#4477AA", "#EE6677"],
    "Blue-Green": ["#1B9E77", "#7570B3"],
    "Red-Green": ["#D7263D", "#21A179"],
    "High-Contrast": ["#000000", "#E69F00"],
    "Grayscale": ["#888888", "#BBBBBB"],
}

CANONICAL_COLS = [
    "Outcome Name",
    "Cohort 1 Risk (%)",
    "Cohort 2 Risk (%)",
    "Cohort 1 Lower 95% CI (%)",
    "Cohort 1 Upper 95% CI (%)",
    "Cohort 2 Lower 95% CI (%)",
    "Cohort 2 Upper 95% CI (%)",
]

st.set_page_config(page_title="2-Cohort Outcome Bar Chart", layout="centered")

st.title("Two-Cohort Outcome Bar Chart")
st.markdown("""
Enter outcome risks manually or upload TriNetX Measures of Association graph sheets.  
The app will extract cohort names and risks from the `Graph Data Table` section and populate the chart. If the export includes lower and upper 95% confidence limits, the app can display them as error bars.
""")


def initialize_data():
    return pd.DataFrame({
        "Outcome Name": ["Diabetes", "Anemia", "Cancer"],
        "Cohort 1 Risk (%)": [11.2, 13.5, 9.7],
        "Cohort 2 Risk (%)": [8.9, 15.2, 10.1],
        "Cohort 1 Lower 95% CI (%)": [9.8, 11.7, 8.1],
        "Cohort 1 Upper 95% CI (%)": [12.6, 15.3, 11.4],
        "Cohort 2 Lower 95% CI (%)": [7.4, 13.2, 8.6],
        "Cohort 2 Upper 95% CI (%)": [10.5, 17.4, 11.9],
    })


def blank_data():
    return pd.DataFrame(columns=CANONICAL_COLS)


def clean_title_from_filename(filename: str) -> str:
    if not filename:
        return "Uploaded Outcome"
    stem = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    for token in ["_MOA_graph", "MOA_graph", "_graph", "graph"]:
        stem = stem.replace(token, "")
    stem = stem.replace("_", " ").replace("-", " ").strip()
    return " ".join(stem.split()) or "Uploaded Outcome"


def read_uploaded_text(uploaded_file) -> str:
    uploaded_file.seek(0)
    raw = uploaded_file.read()
    if isinstance(raw, str):
        return raw
    for enc in ["utf-8-sig", "utf-8", "latin-1"]:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_graph_data_table_from_csv_text(text: str) -> pd.DataFrame:
    lines = text.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip().strip('"').lower() == "graph data table":
            start_idx = i + 1
            break

    if start_idx is None:
        return pd.read_csv(StringIO(text))

    table_text = "\n".join(line for line in lines[start_idx:] if line.strip())
    if not table_text.strip():
        raise ValueError("The file contains 'Graph Data Table' but no readable table below it.")
    return pd.read_csv(StringIO(table_text))


def extract_graph_data_from_excel(uploaded_file) -> pd.DataFrame:
    uploaded_file.seek(0)
    sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    required = {"cohort", "cohortname", "risk"}

    for _, raw in sheets.items():
        raw = raw.dropna(how="all").dropna(axis=1, how="all")
        for idx in range(len(raw)):
            row_vals = [str(x).strip().lower() for x in raw.iloc[idx].tolist()]
            if required.issubset(set(row_vals)):
                header = [str(x).strip() for x in raw.iloc[idx].tolist()]
                table = raw.iloc[idx + 1:].copy()
                table.columns = header
                table = table.dropna(how="all")
                return table

    raise ValueError("Could not find a Graph Data Table with Cohort, CohortName, and Risk columns.")


def find_column(lower_to_original: dict, candidates: list[str]) -> str | None:
    normalized = {
        key.replace(" ", "").replace("_", "").replace("-", "").replace(".", "").lower(): value
        for key, value in lower_to_original.items()
    }
    for candidate in candidates:
        direct = candidate.lower()
        if direct in lower_to_original:
            return lower_to_original[direct]
        compact = candidate.replace(" ", "").replace("_", "").replace("-", "").replace(".", "").lower()
        if compact in normalized:
            return normalized[compact]
    return None


def pct_or_nan(value):
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return np.nan
    return float(numeric) * 100


def parse_trinetx_graph_sheet(uploaded_file, outcome_name: str | None = None) -> tuple[pd.DataFrame, dict]:
    filename = getattr(uploaded_file, "name", "")
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else "csv"

    if suffix in ["xlsx", "xls"]:
        graph_df = extract_graph_data_from_excel(uploaded_file)
    else:
        text = read_uploaded_text(uploaded_file)
        graph_df = extract_graph_data_table_from_csv_text(text)

    graph_df.columns = [str(c).strip() for c in graph_df.columns]
    lower_to_original = {c.lower(): c for c in graph_df.columns}

    required = ["cohort", "cohortname", "risk"]
    missing = [c for c in required if c not in lower_to_original]
    if missing:
        raise ValueError(f"Missing required graph columns: {', '.join(missing)}")

    cohort_col = lower_to_original["cohort"]
    name_col = lower_to_original["cohortname"]
    risk_col = lower_to_original["risk"]
    lower_ci_col = find_column(lower_to_original, [
        "lower 95% ci", "lower95ci", "lowerci", "risk lower 95% ci", "risk lower ci",
        "95% ci lower", "ci lower", "lower confidence interval", "lcl", "lower"
    ])
    upper_ci_col = find_column(lower_to_original, [
        "upper 95% ci", "upper95ci", "upperci", "risk upper 95% ci", "risk upper ci",
        "95% ci upper", "ci upper", "upper confidence interval", "ucl", "upper"
    ])

    keep_cols = [cohort_col, name_col, risk_col]
    for optional_col in [lower_ci_col, upper_ci_col]:
        if optional_col and optional_col not in keep_cols:
            keep_cols.append(optional_col)

    graph_df = graph_df[keep_cols].copy()
    graph_df[cohort_col] = pd.to_numeric(graph_df[cohort_col], errors="coerce")
    graph_df[risk_col] = pd.to_numeric(graph_df[risk_col], errors="coerce")
    if lower_ci_col:
        graph_df[lower_ci_col] = pd.to_numeric(graph_df[lower_ci_col], errors="coerce")
    if upper_ci_col:
        graph_df[upper_ci_col] = pd.to_numeric(graph_df[upper_ci_col], errors="coerce")
    graph_df = graph_df.dropna(subset=[cohort_col, risk_col]).sort_values(cohort_col)

    if len(graph_df) < 2:
        raise ValueError("Graph sheet must contain at least two cohort risk rows.")

    c1 = graph_df.iloc[0]
    c2 = graph_df.iloc[1]
    cohort1_name = str(c1[name_col]).strip() or "Cohort 1"
    cohort2_name = str(c2[name_col]).strip() or "Cohort 2"

    row = pd.DataFrame({
        "Outcome Name": [outcome_name or clean_title_from_filename(filename)],
        "Cohort 1 Risk (%)": [pct_or_nan(c1[risk_col])],
        "Cohort 2 Risk (%)": [pct_or_nan(c2[risk_col])],
        "Cohort 1 Lower 95% CI (%)": [pct_or_nan(c1[lower_ci_col]) if lower_ci_col else np.nan],
        "Cohort 1 Upper 95% CI (%)": [pct_or_nan(c1[upper_ci_col]) if upper_ci_col else np.nan],
        "Cohort 2 Lower 95% CI (%)": [pct_or_nan(c2[lower_ci_col]) if lower_ci_col else np.nan],
        "Cohort 2 Upper 95% CI (%)": [pct_or_nan(c2[upper_ci_col]) if upper_ci_col else np.nan],
    })
    meta = {"cohort1_name": cohort1_name, "cohort2_name": cohort2_name}
    return row, meta


def coerce_app_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or len(df.columns) == 0:
        return blank_data()
    df = df.copy()
    if "Outcome Name" not in df.columns and len(df.columns) >= 1:
        df = df.rename(columns={df.columns[0]: "Outcome Name"})
    if "Cohort 1 Risk (%)" not in df.columns and len(df.columns) >= 2:
        df = df.rename(columns={df.columns[1]: "Cohort 1 Risk (%)"})
    if "Cohort 2 Risk (%)" not in df.columns and len(df.columns) >= 3:
        df = df.rename(columns={df.columns[2]: "Cohort 2 Risk (%)"})
    for col in CANONICAL_COLS:
        if col not in df.columns:
            df[col] = np.nan if col != "Outcome Name" else ""
    df = df[CANONICAL_COLS]
    for col in CANONICAL_COLS[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Outcome Name"] = df["Outcome Name"].astype(str)
    return df.dropna(subset=["Outcome Name", "Cohort 1 Risk (%)", "Cohort 2 Risk (%)"], how="all")


# ---------- SESSION STATE ----------
if "data" not in st.session_state:
    st.session_state.data = initialize_data()
if "cohort1_name" not in st.session_state:
    st.session_state.cohort1_name = "Cohort 1"
if "cohort2_name" not in st.session_state:
    st.session_state.cohort2_name = "Cohort 2"

# ---------- IMPORT CONTROLS ----------
st.sidebar.header("Import TriNetX Graph Sheets")
uploaded_graphs = st.sidebar.file_uploader(
    "Upload one or more MOA graph sheets",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True,
    help="Use the TriNetX Measures of Association graph export containing the Graph Data Table with Cohort, CohortName, and Risk columns. If lower/upper CI columns are present, they will also be imported.",
)

import_mode = st.sidebar.radio("When importing", ["Replace current table", "Append to current table"], index=0)

if st.sidebar.button("Import graph sheet data", disabled=not uploaded_graphs):
    imported_rows = []
    import_errors = []
    imported_meta = None

    for uploaded in uploaded_graphs:
        try:
            row, meta = parse_trinetx_graph_sheet(uploaded)
            imported_rows.append(row)
            imported_meta = imported_meta or meta
        except Exception as exc:
            import_errors.append(f"{uploaded.name}: {exc}")

    if imported_rows:
        imported_df = pd.concat(imported_rows, ignore_index=True)
        if import_mode == "Append to current table":
            st.session_state.data = pd.concat([coerce_app_dataframe(st.session_state.data), imported_df], ignore_index=True)
        else:
            st.session_state.data = imported_df

        if imported_meta:
            st.session_state.cohort1_name = imported_meta["cohort1_name"]
            st.session_state.cohort2_name = imported_meta["cohort2_name"]

        st.sidebar.success(f"Imported {len(imported_rows)} graph sheet(s).")

    if import_errors:
        st.sidebar.error("Some files could not be imported:\n" + "\n".join(import_errors))

if st.sidebar.button("Reset example data"):
    st.session_state.data = initialize_data()
    st.session_state.cohort1_name = "Cohort 1"
    st.session_state.cohort2_name = "Cohort 2"

# ---------- SIDEBAR: GRAPH SETTINGS ----------
st.sidebar.header("Graph Settings")
cohort1_name = st.sidebar.text_input("Cohort 1 Name", st.session_state.cohort1_name, key="cohort1_name_input")
cohort2_name = st.sidebar.text_input("Cohort 2 Name", st.session_state.cohort2_name, key="cohort2_name_input")
st.session_state.cohort1_name = cohort1_name
st.session_state.cohort2_name = cohort2_name

palette_name = st.sidebar.selectbox("Color Palette", list(PALETTES.keys()), index=1)
color1_default, color2_default = PALETTES[palette_name]
color1 = st.sidebar.color_picker(f"Bar Color for {cohort1_name}", color1_default)
color2 = st.sidebar.color_picker(f"Bar Color for {cohort2_name}", color2_default)

# ---------- EDITOR ----------
df = coerce_app_dataframe(st.session_state.data)
display_df = df.rename(columns={
    "Cohort 1 Risk (%)": f"{cohort1_name} Risk (%)",
    "Cohort 2 Risk (%)": f"{cohort2_name} Risk (%)",
    "Cohort 1 Lower 95% CI (%)": f"{cohort1_name} Lower 95% CI (%)",
    "Cohort 1 Upper 95% CI (%)": f"{cohort1_name} Upper 95% CI (%)",
    "Cohort 2 Lower 95% CI (%)": f"{cohort2_name} Lower 95% CI (%)",
    "Cohort 2 Upper 95% CI (%)": f"{cohort2_name} Upper 95% CI (%)",
})

edited_display_df = st.data_editor(
    display_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Outcome Name": st.column_config.TextColumn("Outcome Name"),
        f"{cohort1_name} Risk (%)": st.column_config.NumberColumn(f"{cohort1_name} Risk (%)", min_value=0.0, max_value=100.0, step=0.0001, format="%.4f"),
        f"{cohort2_name} Risk (%)": st.column_config.NumberColumn(f"{cohort2_name} Risk (%)", min_value=0.0, max_value=100.0, step=0.0001, format="%.4f"),
        f"{cohort1_name} Lower 95% CI (%)": st.column_config.NumberColumn(f"{cohort1_name} Lower 95% CI (%)", min_value=0.0, max_value=100.0, step=0.0001, format="%.4f"),
        f"{cohort1_name} Upper 95% CI (%)": st.column_config.NumberColumn(f"{cohort1_name} Upper 95% CI (%)", min_value=0.0, max_value=100.0, step=0.0001, format="%.4f"),
        f"{cohort2_name} Lower 95% CI (%)": st.column_config.NumberColumn(f"{cohort2_name} Lower 95% CI (%)", min_value=0.0, max_value=100.0, step=0.0001, format="%.4f"),
        f"{cohort2_name} Upper 95% CI (%)": st.column_config.NumberColumn(f"{cohort2_name} Upper 95% CI (%)", min_value=0.0, max_value=100.0, step=0.0001, format="%.4f"),
    },
    key="data_editor",
)

edited_df = edited_display_df.rename(columns={
    f"{cohort1_name} Risk (%)": "Cohort 1 Risk (%)",
    f"{cohort2_name} Risk (%)": "Cohort 2 Risk (%)",
    f"{cohort1_name} Lower 95% CI (%)": "Cohort 1 Lower 95% CI (%)",
    f"{cohort1_name} Upper 95% CI (%)": "Cohort 1 Upper 95% CI (%)",
    f"{cohort2_name} Lower 95% CI (%)": "Cohort 2 Lower 95% CI (%)",
    f"{cohort2_name} Upper 95% CI (%)": "Cohort 2 Upper 95% CI (%)",
})
st.session_state.data = coerce_app_dataframe(edited_df)
df = st.session_state.data.copy()

# ---------- CHART CONTROLS ----------
st.sidebar.header("Chart Appearance")
orientation = st.sidebar.radio("Bar Orientation", ["Vertical", "Horizontal"], index=1)
font_family = st.sidebar.selectbox("Font Family", ["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana"], index=0)
font_size = st.sidebar.slider("Font Size", 8, 32, 14)
tick_fontsize = st.sidebar.slider("Tick Mark Font Size", 6, 28, 11)
major_tick_length = st.sidebar.slider("Major Tick Length", 2, 15, 8)
minor_ticks = st.sidebar.checkbox("Show Minor Ticks", value=True)

bar_width = st.sidebar.slider("Bar Width", 0.1, 0.6, 0.26)
group_gap = st.sidebar.slider("Distance Between Bar Groups", 1.0, 5.0, 2.3, step=0.05)
pair_gap = st.sidebar.slider("Spacing Between Cohort Bars in a Group", 0.05, 1.2, 0.32, step=0.01)
gridlines = st.sidebar.checkbox("Show gridlines", value=True)
show_legend = st.sidebar.checkbox("Show legend", value=True)
show_values = st.sidebar.checkbox("Show values on bars", value=True)
show_error_bars = st.sidebar.checkbox("Show 95% CI error bars", value=False, help="Uses lower/upper 95% CI columns when imported from TriNetX or entered manually.")
error_bar_capsize = st.sidebar.slider("Error Bar Cap Size", 0, 12, 4)
error_bar_linewidth = st.sidebar.slider("Error Bar Line Width", 0.5, 4.0, 1.4, step=0.1)

st.subheader("Bar Chart")

if show_error_bars:
    needed_ci_cols = [
        "Cohort 1 Lower 95% CI (%)", "Cohort 1 Upper 95% CI (%)",
        "Cohort 2 Lower 95% CI (%)", "Cohort 2 Upper 95% CI (%)",
    ]
    if df[needed_ci_cols].isna().all(axis=None):
        st.info("Error bars are enabled, but no 95% CI columns are populated. Enter CI values manually or upload a graph sheet/export that includes lower and upper CI values.")


def plot_2cohort_outcomes(
    df, cohort1, cohort2, color1, color2, orientation, font_family, font_size, tick_fontsize,
    bar_width, gridlines, show_values, show_legend, group_gap, pair_gap, major_tick_length, minor_ticks,
    show_error_bars=False, error_bar_capsize=4, error_bar_linewidth=1.4
):
    df = coerce_app_dataframe(df)
    if len(df) == 0:
        fig, ax = plt.subplots()
        ax.set_title("No data to plot.")
        return fig

    outcomes = df["Outcome Name"].tolist()
    cohort1_vals = df["Cohort 1 Risk (%)"].fillna(0).tolist()
    cohort2_vals = df["Cohort 2 Risk (%)"].fillna(0).tolist()
    n = len(outcomes)
    group_centers = np.arange(n) * group_gap
    pair_offset = pair_gap / 2
    max_val = max(cohort1_vals + cohort2_vals) if cohort1_vals + cohort2_vals else 0

    error_cols = [
        "Cohort 1 Lower 95% CI (%)", "Cohort 1 Upper 95% CI (%)",
        "Cohort 2 Lower 95% CI (%)", "Cohort 2 Upper 95% CI (%)",
    ]
    has_error_data = show_error_bars and all(col in df.columns for col in error_cols) and df[error_cols].notna().all(axis=1).any()

    def asymmetric_errors(values, lower_col, upper_col):
        values_arr = np.array(values, dtype=float)
        lower_arr = pd.to_numeric(df[lower_col], errors="coerce").to_numpy(dtype=float)
        upper_arr = pd.to_numeric(df[upper_col], errors="coerce").to_numpy(dtype=float)
        lower_err = np.where(np.isfinite(lower_arr), np.maximum(values_arr - lower_arr, 0), 0)
        upper_err = np.where(np.isfinite(upper_arr), np.maximum(upper_arr - values_arr, 0), 0)
        return np.vstack([lower_err, upper_err])

    max_ci_val = max_val
    if has_error_data:
        ci_upper_values = pd.concat([
            pd.to_numeric(df["Cohort 1 Upper 95% CI (%)"], errors="coerce"),
            pd.to_numeric(df["Cohort 2 Upper 95% CI (%)"], errors="coerce"),
        ]).dropna()
        if not ci_upper_values.empty:
            max_ci_val = max(max_val, float(ci_upper_values.max()))

    plt.style.use("default")
    fig, ax = plt.subplots(figsize=(max(7, 1.2 * n * group_gap), 5.2))
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FAFAFA")

    if orientation == "Vertical":
        bars1 = ax.bar(group_centers - pair_offset, cohort1_vals, bar_width, label=cohort1, color=color1, linewidth=0, zorder=3)
        bars2 = ax.bar(group_centers + pair_offset, cohort2_vals, bar_width, label=cohort2, color=color2, linewidth=0, zorder=3)
        if has_error_data:
            ax.errorbar(group_centers - pair_offset, cohort1_vals, yerr=asymmetric_errors(cohort1_vals, "Cohort 1 Lower 95% CI (%)", "Cohort 1 Upper 95% CI (%)"), fmt="none", ecolor="black", elinewidth=error_bar_linewidth, capsize=error_bar_capsize, zorder=4)
            ax.errorbar(group_centers + pair_offset, cohort2_vals, yerr=asymmetric_errors(cohort2_vals, "Cohort 2 Lower 95% CI (%)", "Cohort 2 Upper 95% CI (%)"), fmt="none", ecolor="black", elinewidth=error_bar_linewidth, capsize=error_bar_capsize, zorder=4)
        ax.set_xticks(group_centers)
        ax.set_xticklabels(outcomes, fontsize=font_size, fontweight="bold", rotation=15, ha="right", fontname=font_family)
        ax.set_ylabel("Risk (%)", fontsize=font_size + 3, fontweight="bold", fontname=font_family)
        ax.set_xlabel("Outcome", fontsize=font_size + 2, fontname=font_family)
        ax.set_ylim([0, max(1, max_ci_val * 1.18)])
        if show_values:
            offset = max(0.01, max_ci_val * 0.02)
            for rect in list(bars1) + list(bars2):
                height = rect.get_height()
                if height > 0:
                    ax.text(rect.get_x() + rect.get_width() / 2., height + offset, f"{height:.4f}%", ha="center", va="bottom", fontsize=max(6, font_size - 1), fontweight="medium", fontname=font_family)
        if gridlines:
            ax.yaxis.grid(True, color="#DDDDDD", zorder=0)
        ax.xaxis.set_tick_params(labelsize=tick_fontsize, length=major_tick_length)
        ax.yaxis.set_tick_params(labelsize=tick_fontsize, length=major_tick_length)
        if minor_ticks:
            ax.yaxis.set_minor_locator(AutoMinorLocator())
            ax.yaxis.set_tick_params(which="minor", length=int(major_tick_length * 0.7), width=0.8)
    else:
        bars1 = ax.barh(group_centers - pair_offset, cohort1_vals, bar_width, label=cohort1, color=color1, linewidth=0, zorder=3)
        bars2 = ax.barh(group_centers + pair_offset, cohort2_vals, bar_width, label=cohort2, color=color2, linewidth=0, zorder=3)
        if has_error_data:
            ax.errorbar(cohort1_vals, group_centers - pair_offset, xerr=asymmetric_errors(cohort1_vals, "Cohort 1 Lower 95% CI (%)", "Cohort 1 Upper 95% CI (%)"), fmt="none", ecolor="black", elinewidth=error_bar_linewidth, capsize=error_bar_capsize, zorder=4)
            ax.errorbar(cohort2_vals, group_centers + pair_offset, xerr=asymmetric_errors(cohort2_vals, "Cohort 2 Lower 95% CI (%)", "Cohort 2 Upper 95% CI (%)"), fmt="none", ecolor="black", elinewidth=error_bar_linewidth, capsize=error_bar_capsize, zorder=4)
        ax.set_yticks(group_centers)
        ax.set_yticklabels(outcomes, fontsize=font_size, fontweight="bold", fontname=font_family)
        ax.set_xlabel("Risk (%)", fontsize=font_size + 3, fontweight="bold", fontname=font_family)
        ax.set_ylabel("Outcome", fontsize=font_size + 2, fontname=font_family)
        ax.set_xlim([0, max(1, max_ci_val * 1.18)])
        if show_values:
            offset = max(0.01, max_ci_val * 0.02)
            for rect in list(bars1) + list(bars2):
                width_val = rect.get_width()
                if width_val > 0:
                    ax.text(width_val + offset, rect.get_y() + rect.get_height() / 2., f"{width_val:.4f}%", va="center", ha="left", fontsize=max(6, font_size - 1), fontweight="medium", fontname=font_family)
        if gridlines:
            ax.xaxis.grid(True, color="#DDDDDD", zorder=0)
        ax.xaxis.set_tick_params(labelsize=tick_fontsize, length=major_tick_length)
        ax.yaxis.set_tick_params(labelsize=tick_fontsize, length=major_tick_length)
        if minor_ticks:
            ax.xaxis.set_minor_locator(AutoMinorLocator())
            ax.xaxis.set_tick_params(which="minor", length=int(major_tick_length * 0.7), width=0.8)

    if show_legend:
        ax.legend(fontsize=font_size + 1, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.01), borderaxespad=0)

    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)
    plt.tight_layout(rect=[0, 0, 0.89 if show_legend else 1, 1])
    return fig


fig = plot_2cohort_outcomes(
    df,
    cohort1=cohort1_name,
    cohort2=cohort2_name,
    color1=color1,
    color2=color2,
    orientation=orientation,
    font_family=font_family,
    font_size=font_size,
    tick_fontsize=tick_fontsize,
    bar_width=bar_width,
    gridlines=gridlines,
    show_values=show_values,
    show_legend=show_legend,
    group_gap=group_gap,
    pair_gap=pair_gap,
    major_tick_length=major_tick_length,
    minor_ticks=minor_ticks,
    show_error_bars=show_error_bars,
    error_bar_capsize=error_bar_capsize,
    error_bar_linewidth=error_bar_linewidth,
)

st.pyplot(fig)

png_buf = BytesIO()
fig.savefig(png_buf, format="png", dpi=300, bbox_inches="tight")
st.download_button("📥 Download Chart as PNG", data=png_buf.getvalue(), file_name="2Cohort_Bargraph.png", mime="image/png")

csv_buf = st.session_state.data.to_csv(index=False).encode("utf-8")
st.download_button("📥 Download Edited Data as CSV", data=csv_buf, file_name="2Cohort_Bargraph_Data.csv", mime="text/csv")
