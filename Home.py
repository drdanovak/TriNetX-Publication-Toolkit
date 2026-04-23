import streamlit as st

st.set_page_config(
    page_title="TriNetX Publication Toolkit",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📚 TriNetX Publication Toolkit")
st.markdown("""
Welcome to the **TriNetX Publication Toolkit**, a collection of easy-to-use tools organized into:
- 📏 **Calculators**
- 📊 **Graphing Tools**
- 📋 **Table Generators**
- ✅ **Reporting Checklists**

Use the sidebar to explore each tool.
""")

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📏 Calculators")
    st.markdown("""
- 📐 Effect Size Calculator
- 🎯 Power & Sample Size Adequacy Calculator
- 🔢 **Multiple Testing Correction Calculator** *(new)*
""")
    st.markdown("### 📊 Graphing Tools")
    st.markdown("""
- 📉 Kaplan-Meier Curve Maker
- 🌲 Forest Plot Generator
- 📊 Two-Cohort Outcome Bar Graphs
- ❤️ Love Plot Generator
- ⚔️ **Competing Risks / CIF Plotter** *(new)*
""")

with col2:
    st.markdown("### 📋 Table Generators")
    st.markdown("""
- ⚖️ PSM Table Generator
- 🧮 Outcomes Table Generator
""")
    st.markdown("### ✅ Reporting Checklists")
    st.markdown("""
- 📝 Novak's STROBE Assessment Tool
- 📋 **RECORD Reporting Checklist** *(new — for routinely-collected data)*
""")
