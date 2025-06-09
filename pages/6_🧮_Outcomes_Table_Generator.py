import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(layout="wide")
st.title("Novak's TriNetX Outcomes Table Generator")

uploaded_files = st.file_uploader(
    "📂 Upload TriNetX outcome files that you downloaded from the platform. Do not make any changes to the CSVs before uploading them.",
    type=["csv"], accept_multiple_files=True
)

if not uploaded_files:
    st.info("Upload at least one TriNetX outcome file exported from TriNetX.")
    st.stop()

# ---- Sidebar/Toolbar Options ----
st.sidebar.header("Table Options")

decimals = st.sidebar.number_input("Decimal places for risks/ratios", min_value=0, max_value=6, value=3, step=1)
show_percent = st.sidebar.checkbox("Show risk as percent (%)", value=False)

with st.sidebar.expander("Color and Style Options", expanded=False):
    palette = st.selectbox("Color Palette Preset", ["AMA", "APA", "NEJM", "Nature", "Monochrome"], index=0)
    palette_dict = {
        "AMA": {"header_bg":"#1b365d", "header_fg":"#fff", "stats_bg":"#e6ecf2", "stats_fg":"#243952"},
        "APA": {"header_bg":"#002b36", "header_fg":"#fff", "stats_bg":"#e1f0ee", "stats_fg":"#175c4c"},
        "NEJM": {"header_bg":"#d6001c", "header_fg":"#fff", "stats_bg":"#fbeaea", "stats_fg":"#990000"},
        "Nature": {"header_bg":"#053061", "header_fg":"#fff", "stats_bg":"#f4f7fa", "stats_fg":"#28527a"},
        "Monochrome": {"header_bg":"#646464", "header_fg":"#fff", "stats_bg":"#eee", "stats_fg":"#222"}
    }
    chosen_palette = palette_dict[palette]
    header_bg = st.color_picker("Header background", chosen_palette['header_bg'])
    header_fg = st.color_picker("Header text", chosen_palette['header_fg'])
    stats_bg = st.color_picker("Statistics row background", chosen_palette['stats_bg'])
    stats_fg = st.color_picker("Statistics row text", chosen_palette['stats_fg'])
    font_family = st.selectbox("Font", ["Arial, sans-serif", "Times New Roman, Times, serif", "Georgia, serif"], index=0)
    border_style = st.selectbox("Border Style", ["1px solid #b6c5db", "1px solid #aab8c2", "1px solid #e2bfc1", "1px solid #555"], index=0)
    spacing = st.slider("Cell vertical spacing (px)", 4, 20, 8, 1)
    horizontal_align = st.selectbox("Horizontal Align", ["center", "left", "right"], index=0)
    vertical_align = st.selectbox("Vertical Align", ["middle", "top", "bottom"], index=0)
    bold_headers = st.checkbox("Bold column headers", value=True)

# ---- Column Visibility Toggles ----
with st.sidebar.expander("Column Visibility", expanded=False):
    show_cohort = st.checkbox("Show Cohort column", value=True)
    show_patients = st.checkbox("Show Patients column", value=True)
    show_outcome = st.checkbox("Show Patients with Outcome column", value=True)
    show_risk = st.checkbox("Show Risk column", value=True)
    show_risk_diff = st.checkbox("Show Risk Difference", value=True)
    show_risk_ratio = st.checkbox("Show Risk Ratio", value=True)
    show_odds_ratio = st.checkbox("Show Odds Ratio", value=True)

# ---- File and Table Adjustments ----
with st.sidebar.expander("File and Table Adjustments", expanded=False):
    outcome_name_map = {}
    file_labels = []
    cohort_labels_1 = {}
    cohort_labels_2 = {}
    for idx, file in enumerate(uploaded_files):
        default_name = file.name.rsplit('.', 1)[0]
        user_outcome = st.text_input(f"Outcome name for '{default_name}'", default_name, key=f"outcome_{default_name}")
        outcome_name_map[file.name] = user_outcome
        file_labels.append(user_outcome)
        cohort_labels_1[file.name] = st.text_input(f"Cohort 1 label for '{default_name}'", "Cohort 1", key=f"c1_{default_name}")
        cohort_labels_2[file.name] = st.text_input(f"Cohort 2 label for '{default_name}'", "Cohort 2", key=f"c2_{default_name}")

    st.markdown("---")
    order_indices = st.multiselect(
        "Select and order outcomes for display:",
        options=list(range(len(file_labels))),
        format_func=lambda i: file_labels[i],
        default=list(range(len(file_labels)))
    )
    order = [file_labels[i] for i in order_indices] if order_indices else file_labels

def robust_csv_to_df(uploaded_file):
    raw = uploaded_file.read().decode('utf-8').splitlines()
    rows = []
    max_cols = 0
    for line in raw:
        comma_split = line.split(',')
        tab_split = line.split('\t')
        row = comma_split if len(comma_split) >= len(tab_split) else tab_split
        rows.append(row)
        if len(row) > max_cols:
            max_cols = len(row)
    rows = [r + [''] * (max_cols - len(r)) for r in rows]
    df = pd.DataFrame(rows)
    return df

def fmt_num(val, decimals=3, percent=False, integer=False):
    try:
        if integer:
            return f"{int(float(val)):,}"
        num = float(val)
        if percent:
            num = num * 100
            s = f"{num:.{decimals}f}%"
        else:
            s = f"{num:.{decimals}f}"
        return s
    except Exception:
        return val

def fmt_p(val):
    try:
        num = float(val)
        if num < 0.001:
            return "p<.001"
        else:
            return f"p={num:.3f}"
    except Exception:
        if str(val).strip() == "":
            return ""
        return f"p={val}"

def get_cell(df, row, col):
    try:
        val = df.iat[row, col]
        if pd.isna(val):
            return ""
        return str(val)
    except Exception:
        return ""

outcome_names = []
outcome_tables = []

# Determine columns to show/hide (and their positions)
base_headers = ["Cohort", "Patients", "Patients with Outcome", "Risk"]
stat_rows = [
    ("Risk Difference", show_risk_diff),
    ("Risk Ratio", show_risk_ratio),
    ("Odds Ratio", show_odds_ratio)
]
base_visible = [show_cohort, show_patients, show_outcome, show_risk]

for file in uploaded_files:
    df = robust_csv_to_df(file)
    min_rows = 28
    min_cols = 6
    if df.shape[0] < min_rows:
        df = pd.concat([df, pd.DataFrame([[''] * df.shape[1] for _ in range(min_rows - df.shape[0])])], ignore_index=True)
    if df.shape[1] < min_cols:
        add_cols = min_cols - df.shape[1]
        pad_df = pd.DataFrame([[''] * add_cols for _ in range(df.shape[0])])
        df = pd.concat([df, pad_df], axis=1)

    name = outcome_name_map[file.name]
    c1label = cohort_labels_1[file.name]
    c2label = cohort_labels_2[file.name]

    cohort_1 = [
        c1label,
        fmt_num(get_cell(df,10,2), integer=True),
        fmt_num(get_cell(df,10,3), integer=True),
        fmt_num(get_cell(df,10,4), decimals, show_percent)
    ]
    cohort_2 = [
        c2label,
        fmt_num(get_cell(df,11,2), integer=True),
        fmt_num(get_cell(df,11,3), integer=True),
        fmt_num(get_cell(df,11,4), decimals, show_percent)
    ]
    risk_diff = fmt_num(get_cell(df,16,0), decimals, show_percent)
    risk_diff_ci = f"({fmt_num(get_cell(df,16,1),decimals,show_percent)}, {fmt_num(get_cell(df,16,2),decimals,show_percent)})"
    risk_diff_p = fmt_p(get_cell(df,16,4))
    risk_ratio = fmt_num(get_cell(df,21,0), decimals, False)
    risk_ratio_ci = f"({fmt_num(get_cell(df,21,1),decimals,False)}, {fmt_num(get_cell(df,21,2),decimals,False)})"
    odds_ratio = fmt_num(get_cell(df,26,0), decimals, False)
    odds_ratio_ci = f"({fmt_num(get_cell(df,26,1),decimals,False)}, {fmt_num(get_cell(df,26,2),decimals,False)})"

    rows = []
    # Table title
    rows.append([f"<b>{name}</b>"] + [""]*(sum(base_visible)-1))
    # Headers
    headers = [h for h, v in zip(base_headers, base_visible) if v]
    rows.append(headers)
    # Cohort rows
    if show_cohort or show_patients or show_outcome or show_risk:
        rows.append([cell for cell, v in zip(cohort_1, base_visible) if v])
        rows.append([cell for cell, v in zip(cohort_2, base_visible) if v])
    # Divider
    rows.append([f"<div style='border-bottom: 4px solid #444; height: 0.1em;'></div>"] + [""]*(sum(base_visible)-1))
    # Stats rows
    if show_risk_diff:
        rows.append(["Risk Difference", risk_diff, f"95% CI: {risk_diff_ci}", risk_diff_p][:sum(base_visible)])
    if show_risk_ratio:
        rows.append(["Risk Ratio", risk_ratio, f"95% CI: {risk_ratio_ci}", ""][:sum(base_visible)])
    if show_odds_ratio:
        rows.append(["Odds Ratio", odds_ratio, f"95% CI: {odds_ratio_ci}", ""][:sum(base_visible)])

    outcome_names.append(name)
    outcome_tables.append(rows)

def style_block(block, bold_headers, header_bg, header_fg, stats_bg, stats_fg, font_family, border_style, spacing, h_align, v_align):
    css = f"""
    <style>
    .compact-table {{
        border-collapse:collapse;width:70%;font-family:{font_family};font-size:1.04em;margin-bottom:2em;
    }}
    .compact-table th, .compact-table td {{
        border:{border_style};
        padding:{spacing}px 8px;
        text-align:{h_align};
        vertical-align:{v_align};
    }}
    .compact-table tr:nth-child(1) td {{
        background:{header_bg};
        color:{header_fg};
        {"font-weight:700;" if bold_headers else ""}
        font-size:1.08em;
        text-align:left;
    }}
    .compact-table tr:nth-child(2) td {{
        background:{header_bg};
        color:{header_fg};
        {"font-weight:700;" if bold_headers else ""}
    }}
    .compact-table tr.divider-row td {{
        border-bottom: 4px solid #444 !important;
        height: 0.2em !important;
        background: #fff !important;
        font-size: 1px !important;
        padding: 0 !important;
    }}
    .compact-table tr.stats-row td {{
        background:{stats_bg};
        color:{stats_fg};
        font-weight:600;
    }}
    </style>
    """
    html = css + "<table class='compact-table'>"
    for i, row in enumerate(block):
        if i == 4:
            html += "<tr class='divider-row'>" + "".join([f"<td colspan='{len(row)}'>{cell}</td>" if idx == 0 else "" for idx, cell in enumerate(row)]) + "</tr>"
        elif i >= 5:
            html += "<tr class='stats-row'>" + "".join([f"<td>{cell}</td>" for cell in row]) + "</tr>"
        else:
            html += "<tr>" + "".join([f"<td>{cell}</td>" for cell in row]) + "</tr>"
    html += "</table>"
    return html

st.markdown("### Compact Outcomes Table(s)")
for name in order:
    idx = outcome_names.index(name)
    block = outcome_tables[idx]
    st.markdown(style_block(
        block,
        bold_headers=bold_headers,
        header_bg=header_bg,
        header_fg=header_fg,
        stats_bg=stats_bg,
        stats_fg=stats_fg,
        font_family=font_family,
        border_style=border_style,
        spacing=spacing,
        h_align=horizontal_align,
        v_align=vertical_align,
    ), unsafe_allow_html=True)

csv_buffer = io.StringIO()
for idx, name in enumerate(order):
    pd.DataFrame(outcome_tables[outcome_names.index(name)]).to_csv(csv_buffer, index=False, header=False)
    csv_buffer.write("\n\n")
st.download_button(
    "Download All Outcomes as CSV",
    csv_buffer.getvalue(),
    "all_outcomes_tables.csv",
    "text/csv"
)
