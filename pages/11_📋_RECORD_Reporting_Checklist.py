import streamlit as st
import pandas as pd
from collections import defaultdict

# RECORD 2015 checklist items — Nicholls et al., PLOS Medicine 2015
# Items marked (RECORD) are additions/extensions to STROBE specific to routinely-collected data.
RECORD_ITEMS = [
    # --- Title & Abstract ---
    {
        "section": "Title and Abstract",
        "item_num": "1",
        "item": "Indicate the study design and the type of routinely-collected health data used in the title or abstract. If applicable, report the geographic region and timeframe of the data, and the databases used.",
        "guidance": "Readers should be able to identify from the title/abstract that this study uses routinely-collected data (e.g., electronic health records, claims, registry). Name the specific database (e.g., TriNetX) where possible.",
        "record_specific": True,
        "tag_options": [
            "Title/abstract does not indicate use of routinely-collected data or name the database.",
            "Data source is implied but not explicitly named or described.",
            "Data type, database, geographic region, and timeframe are clearly stated."
        ]
    },
    {
        "section": "Title and Abstract",
        "item_num": "2",
        "item": "Provide an informative and balanced summary of what was done and what was found.",
        "guidance": "The abstract should include study purpose, data source, key methods, primary results, and conclusions.",
        "record_specific": False,
        "tag_options": [
            "Abstract is missing key information about methods or results.",
            "Abstract provides some summary but is incomplete or unbalanced.",
            "Abstract gives a clear, informative, and balanced summary."
        ]
    },
    # --- Introduction ---
    {
        "section": "Introduction",
        "item_num": "3",
        "item": "Explain the scientific background and rationale, including why routinely-collected data are appropriate for addressing the research question.",
        "guidance": "Justify the use of the specific database (e.g., TriNetX) — its size, representativeness, or the specific population it captures.",
        "record_specific": True,
        "tag_options": [
            "Background or rationale for using this data source is not provided.",
            "Rationale for the data source is mentioned but not justified.",
            "Rationale is well-described with justification for using routinely-collected data."
        ]
    },
    {
        "section": "Introduction",
        "item_num": "4",
        "item": "State specific objectives, including any pre-specified hypotheses.",
        "guidance": "Clearly state what you set out to do, including hypotheses and primary vs. secondary outcomes.",
        "record_specific": False,
        "tag_options": [
            "Objectives or hypotheses are not stated.",
            "Objectives are stated but are vague or hypotheses are missing.",
            "Objectives and hypotheses are clearly and specifically stated."
        ]
    },
    # --- Methods: Study Design ---
    {
        "section": "Methods – Study Design",
        "item_num": "5",
        "item": "Present key elements of study design early in the paper.",
        "guidance": "Identify the type of study (e.g., retrospective cohort, case-control, cross-sectional) and key design features.",
        "record_specific": False,
        "tag_options": [
            "Study design is not described.",
            "Some design elements are given but are incomplete or placed late.",
            "Study design and key features are introduced clearly and early."
        ]
    },
    {
        "section": "Methods – Study Design",
        "item_num": "6",
        "item": "Describe the setting, locations, and relevant dates including data collection period, study period, and follow-up.",
        "guidance": "State when and where the data were collected, and the study's observation period.",
        "record_specific": False,
        "tag_options": [
            "Setting, locations, or study dates are missing.",
            "Setting or dates are partially reported.",
            "Setting, locations, and all relevant dates are well described."
        ]
    },
    # --- Methods: Participants & Database ---
    {
        "section": "Methods – Participants & Database",
        "item_num": "7 (RECORD)",
        "item": "Describe the source database(s): the population it covers, the types of data recorded, and the time period available. Explain how the study population was selected from the database.",
        "guidance": "For TriNetX studies: describe how the platform was used, what health systems/networks contributed data, and the approximate patient population size. Report the ICD codes, CPT codes, or algorithms used to define cohorts.",
        "record_specific": True,
        "tag_options": [
            "Database characteristics and cohort selection methods are not described.",
            "Database is named but population coverage or selection methods are incomplete.",
            "Database characteristics, population coverage, and selection methods are fully described."
        ]
    },
    {
        "section": "Methods – Participants & Database",
        "item_num": "8 (RECORD)",
        "item": "Provide a complete list of codes and algorithms used to identify exposures, outcomes, confounders, and effect modifiers (e.g., ICD-9/10, CPT, RxNorm codes). If possible, provide this list in a supplement.",
        "guidance": "List every code used to define each variable. For TriNetX queries this includes the specific ICD, CPT, medication codes entered. Vague descriptions like 'hypertension was identified using ICD codes' are insufficient.",
        "record_specific": True,
        "tag_options": [
            "Codes or algorithms used to define key variables are not provided.",
            "Some codes are mentioned but the list is incomplete.",
            "A complete code list is provided (in text or supplement) for all key variables."
        ]
    },
    {
        "section": "Methods – Participants & Database",
        "item_num": "9",
        "item": "Describe eligibility criteria and how participants were identified and selected. For propensity score-matched studies, describe the matching procedure.",
        "guidance": "State inclusion and exclusion criteria. For TriNetX PSM studies, describe the matching algorithm, caliper width, and matched variables.",
        "record_specific": False,
        "tag_options": [
            "Eligibility criteria or selection methods are not described.",
            "Some criteria are given but the selection process is incomplete.",
            "Eligibility criteria and selection process are fully and clearly described."
        ]
    },
    # --- Methods: Variables & Bias ---
    {
        "section": "Methods – Variables & Bias",
        "item_num": "10",
        "item": "Clearly define all outcomes, exposures, predictors, confounders, and effect modifiers. Describe how they were measured and any data quality checks performed.",
        "guidance": "Describe how variables were operationally defined in the database. Acknowledge any limitations in how diagnoses or procedures are recorded (coding practices, documentation variability).",
        "record_specific": False,
        "tag_options": [
            "Variable definitions and measurement are not described.",
            "Variables are partially defined but measurement methods or quality checks are missing.",
            "All variables are clearly defined, measurement methods described, and data quality addressed."
        ]
    },
    {
        "section": "Methods – Variables & Bias",
        "item_num": "11",
        "item": "Describe any efforts to address sources of bias inherent to routinely-collected data (e.g., miscoding, missing data, informative censoring, immortal-time bias).",
        "guidance": "Routinely-collected data are collected for administrative, not research, purposes. Discuss potential biases specific to your database and any analytical steps taken to mitigate them.",
        "record_specific": True,
        "tag_options": [
            "Potential biases from using routinely-collected data are not discussed.",
            "Bias is mentioned but not adequately characterized or addressed.",
            "Sources of bias are clearly described with methods to detect or mitigate them."
        ]
    },
    # --- Methods: Statistics ---
    {
        "section": "Methods – Statistical Analysis",
        "item_num": "12",
        "item": "Describe all statistical methods, including methods for controlling confounding. Explain how missing data were handled.",
        "guidance": "Specify which statistical tests were used (e.g., log-rank, Cox regression, chi-squared). Describe handling of missing data. If propensity score matching was used, describe the method in detail.",
        "record_specific": False,
        "tag_options": [
            "Statistical methods are not described.",
            "Methods are partially described but confounding control or missing data handling is absent.",
            "All statistical methods, confounding control, and missing data handling are clearly described."
        ]
    },
    {
        "section": "Methods – Statistical Analysis",
        "item_num": "13",
        "item": "If multiple outcomes were tested, describe any corrections for multiple comparisons.",
        "guidance": "Testing many outcomes simultaneously inflates the false-positive rate. State whether and how corrections (e.g., Bonferroni, FDR) were applied, or justify why they were not.",
        "record_specific": False,
        "tag_options": [
            "Multiple testing is not addressed despite multiple outcome comparisons.",
            "Multiple comparisons are acknowledged but no correction is applied or justified.",
            "Multiple comparison corrections are applied or the absence of correction is justified."
        ]
    },
    # --- Results ---
    {
        "section": "Results – Participants",
        "item_num": "14 (RECORD)",
        "item": "Report the number of individuals at each stage of the study (initial database query, after each exclusion criterion, final analytic sample). If applicable, provide a flow diagram.",
        "guidance": "Show how the final analytic sample was derived from the full database. For TriNetX studies, this includes the numbers from each query step.",
        "record_specific": True,
        "tag_options": [
            "Participant numbers at each selection stage are not reported.",
            "Some participant counts are given but the full derivation is unclear.",
            "A complete participant flow (with counts at each step) is provided."
        ]
    },
    {
        "section": "Results – Participants",
        "item_num": "15",
        "item": "Report characteristics of the study population, including follow-up time and any differences between cohorts.",
        "guidance": "Provide a baseline characteristics table (Table 1) describing the cohorts. For PSM studies, report characteristics before and after matching.",
        "record_specific": False,
        "tag_options": [
            "Population characteristics are not reported.",
            "Some characteristics are reported but follow-up or cohort differences are missing.",
            "Full baseline characteristics with follow-up time and cohort comparisons are reported."
        ]
    },
    {
        "section": "Results – Outcomes",
        "item_num": "16",
        "item": "Report numbers of outcome events and summary measures (e.g., risks, rates, hazard ratios) with confidence intervals.",
        "guidance": "Report absolute event counts and rates in addition to relative measures (RR, OR, HR). Include 95% CIs for all effect estimates.",
        "record_specific": False,
        "tag_options": [
            "Outcome events or effect estimates are not reported.",
            "Outcome events are reported but CIs or absolute measures are missing.",
            "Outcome events, absolute measures, and effect estimates with CIs are fully reported."
        ]
    },
    {
        "section": "Results – Outcomes",
        "item_num": "17",
        "item": "Report unadjusted and adjusted estimates. If applicable, report subgroup and sensitivity analyses.",
        "guidance": "Clearly distinguish unadjusted from adjusted analyses. Pre-specified subgroup analyses should be distinguished from post-hoc analyses.",
        "record_specific": False,
        "tag_options": [
            "Unadjusted vs. adjusted estimates are not clearly differentiated.",
            "Some analyses are reported but subgroup or sensitivity analyses are missing.",
            "Unadjusted and adjusted estimates are clearly reported with pre-specified subgroup and sensitivity analyses."
        ]
    },
    # --- Discussion ---
    {
        "section": "Discussion",
        "item_num": "18",
        "item": "Summarize key results with reference to the study objectives.",
        "guidance": "State your main findings directly and link them back to your stated hypotheses.",
        "record_specific": False,
        "tag_options": [
            "Key results are not summarized in the discussion.",
            "Results are mentioned but not linked to objectives.",
            "Key results are clearly summarized with reference to stated objectives."
        ]
    },
    {
        "section": "Discussion",
        "item_num": "19 (RECORD)",
        "item": "Discuss limitations of the study, including those arising from the use of routinely-collected data: potential data quality issues, coding errors, missing variables, and the inability to establish causation.",
        "guidance": "Acknowledge that TriNetX and similar databases were designed for clinical operations, not research. Discuss: miscoding or under-coding of diagnoses, lack of laboratory/imaging detail, inability to verify clinical context, residual confounding from unmeasured variables.",
        "record_specific": True,
        "tag_options": [
            "Limitations specific to routinely-collected data are not discussed.",
            "Some limitations are mentioned but data-specific issues are inadequately addressed.",
            "Limitations of the data source (coding quality, missing variables, confounding) are thoroughly discussed."
        ]
    },
    {
        "section": "Discussion",
        "item_num": "20",
        "item": "Provide a cautious interpretation of results considering the study limitations, and discuss generalizability.",
        "guidance": "Consider the representativeness of the database population. TriNetX includes patients from participating health systems, which may not represent all care settings.",
        "record_specific": False,
        "tag_options": [
            "Results are interpreted without acknowledging limitations.",
            "Limitations are acknowledged but generalizability is not addressed.",
            "Results are cautiously interpreted and generalizability is explicitly discussed."
        ]
    },
    # --- Other Information ---
    {
        "section": "Other Information",
        "item_num": "21",
        "item": "Give the source of funding and the role of the funder. Declare any conflicts of interest.",
        "guidance": "Disclose all funding sources and any potential conflicts of interest, including access agreements with TriNetX or participating health systems.",
        "record_specific": False,
        "tag_options": [
            "Funding and conflicts of interest are not declared.",
            "Funding is mentioned but the funder's role or conflicts are not addressed.",
            "Funding source, funder's role, and conflicts of interest are fully declared."
        ]
    },
    {
        "section": "Other Information",
        "item_num": "22 (RECORD)",
        "item": "Provide information on how to access supplementary materials such as the study protocol, analytic code, and query definitions. If data cannot be shared, explain why.",
        "guidance": "For TriNetX studies, describe how readers could reproduce the queries. Share code lists, query parameters, and analysis scripts where possible. If data-sharing is restricted by TriNetX or IRB, state this explicitly.",
        "record_specific": True,
        "tag_options": [
            "No information on supplementary materials, code, or data access is provided.",
            "Supplements are mentioned but access information or restrictions are not addressed.",
            "Information on accessing protocols, code, and data (or reasons for restrictions) is clearly provided."
        ]
    },
]

SCORE_MAP = {0: 0, 1: 1, 2: 2}  # index → score

st.set_page_config(layout="wide")
st.title("Novak's RECORD Reporting Checklist for TriNetX Studies")
st.markdown(
    "Based on the **RECORD Statement** (Nicholls et al., *PLOS Medicine* 2015) — "
    "an extension of STROBE specifically for studies using **Routinely-collected Electronic health Data**. "
    "Items marked 🔷 are RECORD-specific additions beyond standard STROBE."
)

with st.expander("ℹ️ About RECORD"):
    st.markdown("""
The **RE**porting of studies **C**onducted using **O**bservational **R**outinely-collected health **D**ata
(RECORD) statement addresses unique reporting requirements for studies using electronic health records,
administrative claims, or research databases such as TriNetX.

**Reference:** Nicholls SG et al. RECORD: The Reporting of Studies Conducted Using Observational
Routinely-Collected Health Data Statement. *PLOS Medicine*. 2015;12(11):e1001885.
DOI: [10.1371/journal.pmed.1001885](https://doi.org/10.1371/journal.pmed.1001885)
""")

responses = {}
section_groups = defaultdict(list)
for item in RECORD_ITEMS:
    section_groups[item["section"]].append(item)

for section, items in section_groups.items():
    st.markdown(f"### {section}")
    for item in items:
        badge = "🔷 " if item["record_specific"] else ""
        label = f"**Item {item['item_num']}** — {badge}{item['item']}"
        with st.expander(label, expanded=False):
            st.markdown(f"*{item['guidance']}*")
            key = f"record_{item['item_num']}"
            response = st.radio(
                "Compliance level:",
                item["tag_options"],
                index=0,
                key=key,
                label_visibility="collapsed"
            )
            responses[item["item_num"]] = (item["tag_options"].index(response), item["section"], item["record_specific"])

# ---- Score Summary ----
st.divider()
st.subheader("📊 Compliance Summary")

total_items = len(RECORD_ITEMS)
max_score = total_items * 2
total_score = sum(v[0] for v in responses.values())
record_specific_items = [k for k, v in responses.items() if v[2]]
record_score = sum(responses[k][0] for k in record_specific_items)
record_max = len(record_specific_items) * 2

col1, col2, col3 = st.columns(3)
col1.metric("Overall Score", f"{total_score} / {max_score}", help="0 = not met, 1 = partial, 2 = fully met")
col2.metric("Overall %", f"{100 * total_score / max_score:.0f}%")
col3.metric("RECORD-Specific Score", f"{record_score} / {record_max}")

# Section breakdown
st.markdown("#### Score by Section")
section_scores = defaultdict(lambda: [0, 0])
for item_num, (score, section, _) in responses.items():
    section_scores[section][0] += score
    section_scores[section][1] += 2

rows = []
for section, (s, m) in section_scores.items():
    rows.append({"Section": section, "Score": f"{s}/{m}", "Percent": f"{100*s/m:.0f}%"})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# Items needing attention
low_items = [(k, v) for k, v in responses.items() if v[0] == 0]
if low_items:
    st.markdown("#### ⚠️ Items Requiring Attention (score = 0)")
    for item_num, (_, section, record_specific) in low_items:
        badge = " 🔷 RECORD-specific" if record_specific else ""
        st.markdown(f"- Item **{item_num}** ({section}){badge}")

# Export
st.divider()
st.subheader("Export Results")
export_rows = []
for item in RECORD_ITEMS:
    score, section, is_record = responses[item["item_num"]]
    export_rows.append({
        "Item": item["item_num"],
        "Section": section,
        "RECORD-Specific": is_record,
        "Description": item["item"],
        "Score (0-2)": score,
        "Response": item["tag_options"][score]
    })
export_df = pd.DataFrame(export_rows)
csv_out = export_df.to_csv(index=False)
st.download_button(
    "Download Checklist Results (CSV)", data=csv_out,
    file_name="RECORD_checklist_results.csv", mime="text/csv"
)
