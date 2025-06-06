# app.py - Feature-rich Kaplan-Meier Plot Viewer using Streamlit

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import io
import base64
import re
from PIL import Image
import numpy as np
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import logrank_test

# Title and Instructions
st.title("Kaplan-Meier Survival Curve Viewer")
st.markdown("Upload your Kaplan-Meier CSV output. Customize the visualization and download a publication-ready figure.")

# Step 1: File Upload
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
if uploaded_file:
    lines = uploaded_file.getvalue().decode("utf-8").splitlines()
    header_keywords = ["Time (Days)", "Cohort 1: Survival Probability"]
    header_row_idx = next(i for i, line in enumerate(lines) if all(k in line for k in header_keywords))
    df = pd.read_csv(uploaded_file, skiprows=header_row_idx)

    # Clean data
    df.columns = df.columns.str.strip()
    df.sort_values('Time (Days)', inplace=True)
    df[['Cohort 1: Survival Probability', 'Cohort 2: Survival Probability',
       'Cohort 1: Survival Probability 95 % CI Lower', 'Cohort 1: Survival Probability 95 % CI Upper',
       'Cohort 2: Survival Probability 95 % CI Lower', 'Cohort 2: Survival Probability 95 % CI Upper']] = \
    df[['Cohort 1: Survival Probability', 'Cohort 2: Survival Probability',
        'Cohort 1: Survival Probability 95 % CI Lower', 'Cohort 1: Survival Probability 95 % CI Upper',
        'Cohort 2: Survival Probability 95 % CI Lower', 'Cohort 2: Survival Probability 95 % CI Upper']].ffill()

    # Step 2: User Parameters
    st.sidebar.header("Customize Plot")

    plot_title = st.sidebar.text_input("Plot Title", "Kaplan-Meier Survival Curve")
    label1 = st.sidebar.text_input("Label for Cohort 1", "Cohort 1")
    label2 = st.sidebar.text_input("Label for Cohort 2", "Cohort 2")

    x_label = st.sidebar.text_input("X-axis Label", "Time (Days)")
    y_label = st.sidebar.text_input("Y-axis Label", "Survival Probability")

    style = st.sidebar.radio("Color Scheme", ['Color', 'Black & White'])
    color1 = st.sidebar.color_picker("Cohort 1 Color", '#1f77b4')
    color2 = st.sidebar.color_picker("Cohort 2 Color", '#ff7f0e')

    line_width = st.sidebar.slider("Line Width", 1.0, 5.0, 2.0)
    show_ci = st.sidebar.checkbox("Show Confidence Intervals", True)
    ci_alpha = st.sidebar.slider("CI Transparency", 0.0, 1.0, 0.2)

    show_grid = st.sidebar.checkbox("Show Grid", True)
    fig_width = st.sidebar.slider("Figure Width (inches)", 6, 16, 10)
    fig_height = st.sidebar.slider("Figure Height (inches)", 4, 10, 6)

    y_min = st.sidebar.slider("Y-axis Min", 0.0, 1.0, 0.0)
    y_max = st.sidebar.slider("Y-axis Max", 0.0, 1.5, 1.05)

    title_fontsize = st.sidebar.slider("Title Font Size", 10, 30, 16)
    label_fontsize = st.sidebar.slider("Axis Label Font Size", 10, 20, 12)
    tick_fontsize = st.sidebar.slider("Tick Label Font Size", 8, 16, 10)
    legend_fontsize = st.sidebar.slider("Legend Font Size", 8, 16, 12)

    max_days = st.sidebar.number_input("Maximum Days to Display", min_value=0, max_value=int(df['Time (Days)'].max()), value=int(df['Time (Days)'].max()))

    # Step 3: Generate Plot
    if st.button("Generate Plot"):
        df_limited = df[df['Time (Days)'] <= max_days]
        time = df_limited['Time (Days)']

        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        if style == 'Black & White':
            color1_use, color2_use = 'black', 'gray'
        else:
            color1_use, color2_use = color1, color2

        ax.plot(time, df_limited['Cohort 1: Survival Probability'], label=label1, color=color1_use, linewidth=line_width)
        if show_ci and 'Cohort 1: Survival Probability 95 % CI Lower' in df.columns:
            ax.fill_between(time,
                            df_limited['Cohort 1: Survival Probability 95 % CI Lower'],
                            df_limited['Cohort 1: Survival Probability 95 % CI Upper'],
                            color=color1_use, alpha=ci_alpha)

        ax.plot(time, df_limited['Cohort 2: Survival Probability'], label=label2, color=color2_use, linewidth=line_width)
        if show_ci and 'Cohort 2: Survival Probability 95 % CI Lower' in df.columns:
            ax.fill_between(time,
                            df_limited['Cohort 2: Survival Probability 95 % CI Lower'],
                            df_limited['Cohort 2: Survival Probability 95 % CI Upper'],
                            color=color2_use, alpha=ci_alpha)

        ax.set_title(plot_title, fontsize=title_fontsize)
        ax.set_xlabel(x_label, fontsize=label_fontsize)
        ax.set_ylabel(y_label, fontsize=label_fontsize)
        ax.set_ylim(y_min, y_max)
        ax.tick_params(axis='both', labelsize=tick_fontsize)
        ax.legend(fontsize=legend_fontsize)
        if show_grid:
            ax.grid(True)

        st.pyplot(fig)

        # Step 5: PNG Download with Button
        cleaned_title = re.sub(r'[^\w\-_. ]', '', plot_title).strip().replace(" ", "_")
        filename = f"{cleaned_title or 'kaplan_meier_curve'}.png"

        img_bytes = io.BytesIO()
        fig.savefig(img_bytes, format='png', dpi=300, bbox_inches='tight')
        img_bytes.seek(0)

        st.download_button(
            label="Download Plot",
            data=img_bytes,
            file_name=filename,
            mime="image/png"
        )
