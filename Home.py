import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="TriNetX Publication Toolkit",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("TriNetX Publication Toolkit")
st.caption("A front page for selecting the right tool, preparing the right export, and producing manuscript-ready outputs.")

st.markdown("""
This toolkit helps convert raw TriNetX exports into publication-facing tables, figures, diagnostics, and reporting checks.
Use the sidebar to open an individual tool. Start by identifying the type of output you need, then use the instructions
below to choose the correct TriNetX export and verify the output before placing it into a manuscript.
""")

st.info(
    "Keep the original TriNetX exports unchanged. Use the toolkit to create cleaned copies with readable cohort names, "
    "clear outcome labels, and formatting appropriate for tables, figures, posters, supplements, and manuscript drafts."
)

st.header("Quick tool chooser")

chooser = pd.DataFrame(
    [
        ["Create a Table 1 before and after propensity score matching", "7. PSM Table Generator", "Baseline Patient Characteristics CSV"],
        ["Assess covariate balance after matching", "6. Love Plot Generator", "Baseline Patient Characteristics CSV"],
        ["Create a Table 2-style outcomes table", "9. Outcomes Table Generator", "Measures of Association and/or Kaplan-Meier CSVs"],
        ["Create a forest plot of RR, OR, or HR estimates", "4. Forest Plot Generator", "MOA/KM exports or prepared effect-estimate table"],
        ["Graph absolute risks for two cohorts", "5. Two-Cohort Outcome Bar Graphs", "MOA table or graph exports"],
        ["Create a Kaplan-Meier survival curve", "3. Kaplan-Meier Curve Maker", "Kaplan-Meier CSV export"],
        ["Convert ratios into approximate standardized effect sizes", "1. Effect Size Calculator", "Manual ratio, CI, and p-value entry"],
        ["Estimate power, E-values, risk differences, and NNT/NNH", "2. Power, E-value, and NNT/NNH", "Outcome CSVs or manual risk table"],
        ["Correct p-values across many tested outcomes", "10. Multiple Comparisons Correction Tool", "MOA exports or p-value table"],
        ["Check STROBE reporting completeness", "8. STROBE Assessment Tool", "Your manuscript draft"],
    ],
    columns=["Goal", "Use this tool", "Primary input"],
)
st.dataframe(chooser, hide_index=True, use_container_width=True)

st.header("Recommended workflow")

st.markdown("""
1. **Export from TriNetX.** For most retrospective studies, download the Baseline Patient Characteristics table,
the Measures of Association table for each outcome, and Kaplan-Meier tables when time-to-event results are part of the analysis.

2. **Prepare baseline outputs.** Use the PSM Table Generator for the manuscript Table 1 and the Love Plot Generator
to document balance before and after matching.

3. **Prepare outcome outputs.** Use the Outcomes Table Generator for the main outcomes table. Use the Forest Plot
Generator for multi-outcome effect estimates, the Two-Cohort Bar Graphs tool for absolute risks, and the Kaplan-Meier
Curve Maker for survival curves.

4. **Run rigor checks.** Use the Power/E-value/NNT tool for interpretation, the Multiple Comparisons tool when many
outcomes were tested, and the STROBE tool before submission.

5. **Verify before submission.** Compare every final table and figure against the original TriNetX export.
""")

st.header("Detailed instructions for each tool")

with st.expander("1. Effect Size Calculator"):
    st.markdown("""
**Use when:** You have risk ratios, odds ratios, or hazard ratios and want approximate standardized effect sizes or a simple manually entered forest plot.

**Input:** Manually enter one row per outcome. Select the ratio type. Add lower and upper confidence intervals if you want CI columns or a forest plot. Add p-values if you want them displayed.

**How to use it:** Select the ratio type in the sidebar, add CI and p-value columns if needed, enter outcome labels and ratios, then enable the forest plot option only when CI values are available. Rows beginning with `##` can be used as section headers.

**Output:** A formatted table of ratios, approximate effect sizes, optional CIs, optional p-values, and a downloadable forest plot PNG.

**Check:** Treat the standardized effect size as an interpretive aid, not the primary TriNetX result.
""")

with st.expander("2. Power, E-value, and NNT/NNH"):
    st.markdown("""
**Use when:** You want to contextualize outcome comparisons by estimating power, required sample size, E-values, risk differences, and NNT/NNH.

**Input:** Upload one or more outcome CSVs or enter findings manually. Each row needs Group 1 N, Group 2 N, Risk 1, and Risk 2. Enter risks as proportions rather than percentages.

**How to use it:** Upload or edit outcomes, set alpha and target power, choose one- or two-sided testing, define which cohort is treated/exposed, and specify whether the outcome should be interpreted as adverse or beneficial.

**Output:** A CSV-downloadable summary table with estimated power, required sample size, adequacy status, RR, E-value, risk difference, and NNT/NNH.

**Check:** These are approximate calculations for interpretation and sensitivity analysis. Do not describe them as TriNetX-native model estimates.
""")

with st.expander("3. Kaplan-Meier Curve Maker"):
    st.markdown("""
**Use when:** You need a clean survival curve from a TriNetX Kaplan-Meier export.

**Input:** Upload the Kaplan-Meier CSV containing Time (Days), survival probability columns, and 95% CI columns for both cohorts.

**How to use it:** Upload the CSV, rename the title and cohort labels, adjust axis labels, select color or black-and-white styling, decide whether to show confidence intervals, set the maximum days displayed, and click Generate Plot.

**Output:** A 300 DPI downloadable PNG survival curve.

**Check:** Make sure the y-axis label matches the plotted quantity, such as survival probability or event-free probability.
""")

with st.expander("4. Forest Plot Generator"):
    st.markdown("""
**Use when:** You want to compare multiple outcomes using RR, OR, or HR estimates with confidence intervals.

**Input:** Upload TriNetX Measures of Association exports, Kaplan-Meier exports, Excel exports, or a prepared forest-plot table with outcome, estimate, lower CI, upper CI, and optional p-value columns.

**How to use it:** Upload one or more files, choose the preferred effect measure, review the parsed estimates, rename outcomes, add section headers if needed, set the axis so 1.0 is clearly visible, and generate the plot.

**Output:** A publication-oriented forest plot or forest plot/table hybrid using the selected effect estimates.

**Check:** Avoid mixing RR, OR, and HR in the same visual unless the title and column label explicitly state that mixed effect estimates are being shown.
""")

with st.expander("5. Two-Cohort Outcome Bar Graphs"):
    st.markdown("""
**Use when:** Absolute risks are easier to communicate than ratios.

**Input:** Upload one or more TriNetX MOA table or graph exports in CSV, XLSX, or XLS format. The tool reads Cohort Statistics and Graph Data Table sections.

**How to use it:** Upload files in the sidebar, choose replace or append, import the data, verify risk percentages and CIs, rename cohorts and outcomes, then customize palette, orientation, axis labels, fonts, spacing, error bars, significance stars, and axis limits.

**Output:** A customizable two-cohort risk graph for manuscripts, posters, or presentations.

**Check:** Verify risk percentages and confidence intervals against the source export, especially when Wilson intervals are calculated from event counts.
""")

with st.expander("6. Love Plot Generator"):
    st.markdown("""
**Use when:** You need to show covariate balance before and after propensity score matching.

**Input:** Upload the TriNetX Baseline Patient Characteristics CSV. It must include standardized mean difference columns before and after matching.

**How to use it:** Upload the baseline file, confirm SMD column detection, set the balance threshold, decide whether to show category levels, use the editor to rename, include, exclude, reorder, and group covariates, then customize the x-axis, legend, colors, figure size, and reference band.

**Output:** A downloadable Love plot PNG plus balance metrics, sample retention metrics, variance ratio diagnostics, group-level balance summaries, and narrative balance text.

**Check:** If important covariates remain above the SMD threshold, address that in the results, limitations, or sensitivity-analysis plan.
""")

with st.expander("7. PSM Table Generator"):
    st.markdown("""
**Use when:** You need a journal-style Table 1 showing baseline characteristics before and after propensity score matching.

**Input:** Upload the TriNetX Baseline Patient Characteristics CSV with Characteristic ID, Characteristic Name, Category, cohort counts, percentages, and before/after SMD values.

**How to use it:** Upload the CSV, enter the table title and cohort labels, decide whether to clean labels, simplify lab bins, hide aggregate lab rows, blank repeated LOINC codes, and include p-value columns. Set decimal formatting, then edit the final table before export.

**Output:** A formatted Table 1 with section headers, count/percent cells, mean/SD cells when available, before/after PSM columns, and SMD values. Export options include HTML, CSV, and DOCX.

**Check:** Confirm that the table includes the variables used for matching and that post-match SMDs support the balance claim.
""")

with st.expander("8. STROBE Assessment Tool"):
    st.markdown("""
**Use when:** You are preparing an observational TriNetX manuscript for submission and want a structured reporting checklist.

**Input:** No file upload is required. Use the manuscript draft and score each STROBE item based on the current text.

**How to use it:** Expand each section, score each item as not addressed, partially addressed, or fully addressed, select feedback tags, add comments, and use the incomplete-only view to guide revision.

**Output:** A scored STROBE checklist with comments, percent fully addressed, average score, a list of improvement areas, and a downloadable CSV.

**Check:** STROBE assesses reporting completeness. It does not by itself establish that the design or analysis is methodologically sufficient.
""")

with st.expander("9. Outcomes Table Generator"):
    st.markdown("""
**Use when:** You need a clean manuscript-style outcomes table from multiple TriNetX outcome files.

**Input:** Upload one or more Measures of Association CSVs or Kaplan-Meier CSVs. The tool detects export type and extracts cohort statistics, event counts, risks, survival-derived event probabilities, effect estimates, confidence intervals, and p-values.

**How to use it:** Upload outcome files, review detected type, include or exclude rows, rename outcomes, set display order, add section labels, edit cohort labels, choose decimal formatting, decide whether to include risk difference, odds ratio, or detected-type columns, and preview the table.

**Output:** A Table 2-style outcomes table with outcome names, cohort rows, patients, events, p-values, and RR/HR/OR estimates with 95% CIs.

**Check:** If MOA and KM outputs are combined, make the effect-estimate column label explicit because risk ratios and hazard ratios answer different questions.
""")

with st.expander("10. Multiple Comparisons Correction Tool"):
    st.markdown("""
**Use when:** A study tests many outcomes and you need adjusted p-values.

**Input:** Upload raw TriNetX MOA exports or upload/paste a manual table with an outcome column and raw p-value column.

**How to use it:** Set alpha, choose TriNetX MOA mode or manual p-value mode, upload or paste data, review parsed outcomes, rename outcomes, exclude rows that do not belong to the same testing family, then review adjusted results and the comparison plot.

**Output:** Adjusted p-values and significance flags using Bonferroni, Holm-Bonferroni, Benjamini-Hochberg FDR, and Benjamini-Yekutieli, plus a plot and downloadable CSV.

**Check:** Define the family of tests before interpreting the corrections.
""")

st.header("TriNetX export guide")

exports = pd.DataFrame(
    [
        ["Baseline Patient Characteristics CSV", "Table 1 and balance diagnostics", "PSM Table Generator; Love Plot Generator"],
        ["Measures of Association CSV", "Risks, RR/OR, p-values, bar graphs, outcomes tables, multiple comparisons", "Outcomes Table Generator; Forest Plot Generator; Two-Cohort Bar Graphs; Multiple Comparisons; Power/E-value/NNT"],
        ["Kaplan-Meier CSV", "Survival curves, HRs, log-rank p-values, time-to-event outcomes", "Kaplan-Meier Curve Maker; Outcomes Table Generator; Forest Plot Generator"],
        ["Prepared manual table", "Curated values from outside TriNetX", "Effect Size Calculator; Forest Plot Generator; Multiple Comparisons"],
    ],
    columns=["TriNetX export", "Use for", "Compatible tools"],
)
st.table(exports)

st.header("Common troubleshooting checks")

st.markdown("""
**Upload fails or fields are blank:** Confirm that the file is the correct export type and contains the expected section labels, such as Cohort Statistics, Risk Difference, Risk Ratio, Hazard Ratio, Log-Rank Test, or Characteristic ID.

**Outcome labels are unreadable:** Rename outcomes inside the editable table. Do not use raw file names in manuscript outputs.

**Cohort direction seems reversed:** Check whether Cohort 1 or Cohort 2 is the exposed group. Direction affects risk differences, ratios, E-values, and NNT/NNH.

**P-values do not match expectations:** Check which export section the tool is using. MOA workflows often use the Risk Difference section p-value, while Kaplan-Meier workflows may use log-rank or hazard-ratio information.

**Figure is too crowded:** Shorten labels, add group headers, reduce displayed rows, increase figure size, or use a horizontal layout.

**Final output looks polished:** Still compare the table or figure back to the raw TriNetX export before submission.
""")

st.markdown("---")
st.markdown(
    "**Suggested methods language:** Figures and tables were prepared from TriNetX Analytics exports using the TriNetX "
    "Publication Toolkit, a Streamlit-based set of utilities for formatting real-world data outputs into manuscript-ready "
    "tables, plots, and reporting diagnostics."
)
