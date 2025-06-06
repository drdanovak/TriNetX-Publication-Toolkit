import streamlit as st

st.set_page_config(
    page_title="TriNetX Publication Toolkit",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar content
st.sidebar.title("📖 Navigation")
st.sidebar.markdown("""
- 🌲 **Forest Plot Generator**
- 📉 **Kaplan-Meier Viewer**
- 📊 **Table Generator**
- 📐 **Effect Size Calculator**
""")

# Main page content
st.title("📚 TriNetX Publication Toolkit")
st.markdown("""
Welcome to the **TriNetX Publication Toolkit**, a collection of easy-to-use tools designed to streamline your research publication workflow.

Navigate using the sidebar.
""")
