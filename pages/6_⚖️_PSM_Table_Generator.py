import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

st.set_page_config(layout="wide")
st.title("📊 Novak's TriNetX Journal-Style Table Generator")

uploaded_file = st.file_uploader("📂 Upload your TriNetX CSV file and turn it into a journal-ready table that you can copy and paste into a Word doc or poster. Made by Dr. Daniel Novak at UC Riverside School of Medicine, 2025.", type="csv")
if not uploaded_file:
    st.stop()

# Auto-detect the header row
lines = uploaded_file.getvalue().decode("utf-8").splitlines()
header_index = None
for i, line in enumerate(lines):
    if line.strip().startswith("Characteristic ID"):
        header_index = i
        break

if header_index is None:
    st.error("❌ Could not locate the header row with 'Characteristic ID'. Please check your file format.")
    st.stop()

df_raw = pd.read_csv(uploaded_file, header=header_index)
original_df = df_raw.copy()

# Sidebar Settings UI Changes
with st.sidebar.expander("### ✍️ Table Operations", expanded=False):
    edit_toggle = st.sidebar.checkbox("✏️ Edit Table (with drag-and-drop)")
    merge_duplicates = st.sidebar.checkbox("🔁 Merge duplicate row titles")
    add_column_grouping = st.sidebar.checkbox("📌 Add Before/After PSM Column Separators (with headers)")
    reset_table = st.sidebar.button("🔄 Reset Table to Default")

with st.sidebar.expander("🛠️ Table Formatting Settings", expanded=False):
    st.markdown("### 🔧 Adjust Visual Presentation")
    font_size = st.slider("Font Size", 6, 18, 10)
    h_align = st.selectbox("Text Horizontal Alignment", ["left", "center", "right"])
    v_align = st.selectbox("Text Vertical Alignment", ["top", "middle", "bottom"])
    journal_style = st.selectbox("Journal Style", ["None", "NEJM", "AMA", "APA", "JAMA"])
    decimal_places = st.slider("Round numerical values to", 0, 5, 2)

default_columns = [
    "Characteristic Name", "Characteristic ID", "Category",
    "Cohort 1 Before: Patient Count", "Cohort 1 Before: % of Cohort", "Cohort 1 Before: Mean", "Cohort 1 Before: SD",
    "Cohort 2 Before: Patient Count", "Cohort 2 Before: % of Cohort", "Cohort 2 Before: Mean", "Cohort 2 Before: SD",
    "Before: p-Value", "Before: Standardized Mean Difference",
    "Cohort 1 After: Patient Count", "Cohort 1 After: % of Cohort", "Cohort 1 After: Mean", "Cohort 1 After: SD",
    "Cohort 2 After: Patient Count", "Cohort 2 After: % of Cohort", "Cohort 2 After: Mean", "Cohort 2 After: SD",
    "After: p-Value", "After: Standardized Mean Difference"
]
available_columns = list(df_raw.columns)
filtered_columns = [col for col in default_columns if col in available_columns]
df_trimmed = df_raw[filtered_columns].copy()

with st.sidebar.expander("📋 Column Selection and Renaming", expanded=False):
    selected_columns = st.multiselect("Select columns to include", available_columns, default=filtered_columns)
    rename_dict = {col: st.text_input(f"Rename '{col}'", col, key=f"rename_{col}") for col in selected_columns}
df_trimmed = df_raw[selected_columns].copy()
df_trimmed.rename(columns=rename_dict, inplace=True)
for col in df_trimmed.select_dtypes(include=["object"]).columns:
    df_trimmed[col].fillna("", inplace=True)

with st.sidebar.expander("🧩 Group Rows Settings", expanded=False):
    preset_groups = ["Demographics", "Conditions", "Lab Values", "Medications"]
    custom_group_input = st.text_input("Add Custom Group Name")
    if custom_group_input:
        preset_groups.append(custom_group_input)
        preset_groups = list(dict.fromkeys(preset_groups))
    selected_groups = [label for label in preset_groups if st.checkbox(label, key=f"group_checkbox_{label}")]

for col in df_trimmed.columns:
    try:
        df_trimmed[col] = df_trimmed[col].astype(float).round(decimal_places)
    except:
        pass

for col in df_trimmed.columns:
    if "p-Value" in col:
        df_trimmed[col] = df_trimmed[col].apply(lambda x: "p<.001" if str(x).strip() == "0" else x)

# Handle grouping rows
if selected_groups:
    current_rows = df_trimmed.to_dict("records")
    rebuilt_rows = []
    for row in current_rows:
        name = str(row.get("Characteristic Name", "")).strip()
        if name in selected_groups:
            rebuilt_rows.append(row)
        elif name in preset_groups:
            continue
        else:
            rebuilt_rows.append(row)
    for group in selected_groups:
        if not any(str(row.get("Characteristic Name", "")).strip() == group for row in rebuilt_rows):
            group_row = {col: "" for col in df_trimmed.columns}
            group_row["Characteristic Name"] = group
            rebuilt_rows.insert(0, group_row)
    df_trimmed = pd.DataFrame(rebuilt_rows)

# Get Characteristic Name column robustly
if isinstance(df_trimmed.columns, pd.MultiIndex):
    possible_name_cols = [col for col in df_trimmed.columns if col[1] == "Characteristic Name"]
    if possible_name_cols:
        name_col = possible_name_cols[0]
    else:
        st.error("Could not find 'Characteristic Name' column in MultiIndex.")
        st.stop()
else:
    name_col = "Characteristic Name"
    if name_col not in df_trimmed.columns:
        st.error("Could not find 'Characteristic Name' column.")
        st.stop()

if "row_order" not in st.session_state:
    st.session_state["row_order"] = list(df_trimmed[name_col])
