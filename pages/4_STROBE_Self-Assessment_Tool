import streamlit as st
import pandas as pd
from collections import defaultdict

# ---- FULL STROBE ITEMS ----
STROBE_ITEMS = [
    {
        "section": "Title and Abstract",
        "item": "Indicate the study’s design with a commonly used term in the title or the abstract.",
        "guidance": "Clearly state the study design (e.g., cohort, case-control, cross-sectional) in the title or abstract.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "No mention of study design in the title or abstract.",
            "Study design is referenced but not clearly or consistently.",
            "Study design is clearly and appropriately stated."
        ]
    },
    {
        "section": "Title and Abstract",
        "item": "Provide in the abstract an informative and balanced summary of what was done and what was found.",
        "guidance": "Summarize study purpose, methods, key results, and conclusions in the abstract.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "The abstract is missing key information about methods or results.",
            "The abstract provides some summary but is incomplete or unbalanced.",
            "The abstract gives a clear, informative, and balanced summary."
        ]
    },
    {
        "section": "Introduction",
        "item": "Explain the scientific background and rationale for the investigation being reported.",
        "guidance": "Describe why the study was done, with context and relevant literature.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Scientific background and rationale are missing.",
            "Some background is given but lacks context or sufficient detail.",
            "Rationale is well described and contextualized with relevant literature."
        ]
    },
    {
        "section": "Introduction",
        "item": "State specific objectives, including any prespecified hypotheses.",
        "guidance": "Clearly state what you set out to do, including hypotheses.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Objectives or hypotheses are not stated.",
            "Objectives are stated but are vague or hypotheses are missing.",
            "Objectives and hypotheses are clearly stated and specific."
        ]
    },
    {
        "section": "Methods",
        "item": "Present key elements of study design early in the paper.",
        "guidance": "Identify the type of study and its key design features.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Key elements of the study design are not presented.",
            "Some study design elements are given but not early or not all are present.",
            "Study design and its key features are introduced clearly at the start."
        ]
    },
    {
        "section": "Methods",
        "item": "Describe the setting, locations, and relevant dates, including periods of recruitment, exposure, follow-up, and data collection.",
        "guidance": "State where and when the study was done.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Setting, locations, or study dates are missing.",
            "Setting or dates are partially reported.",
            "All relevant settings, locations, and dates are well described."
        ]
    },
    {
        "section": "Methods",
        "item": "Give the eligibility criteria, and the sources and methods of selection of participants. Describe methods of follow-up. For matched studies, give matching criteria and number of exposed/unexposed.",
        "guidance": "Explain how participants were identified, included, excluded, and how they were followed up.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Eligibility criteria or selection methods are not described.",
            "Some eligibility or selection details are given but are incomplete.",
            "Eligibility criteria and participant selection are fully explained."
        ]
    },
    {
        "section": "Methods",
        "item": "For each variable of interest, give sources of data and details of methods of assessment (measurement).",
        "guidance": "Describe how each variable was measured or obtained.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Variables or their measurement are not described.",
            "Some variables or measurement methods are described.",
            "All variables and measurement methods are described in detail."
        ]
    },
    {
        "section": "Methods",
        "item": "Describe any efforts to address potential sources of bias.",
        "guidance": "Discuss what you did to minimize bias (e.g., blinding, statistical adjustments).",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "No mention of efforts to address bias.",
            "Some efforts to reduce bias are described but lack detail.",
            "Potential sources of bias and mitigation efforts are thoroughly discussed."
        ]
    },
    {
        "section": "Methods",
        "item": "Explain how the study size was arrived at.",
        "guidance": "Provide rationale for sample size, power calculations if possible.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "No explanation for how the sample size was determined.",
            "Sample size is mentioned, but rationale or calculations are lacking.",
            "Sample size rationale and calculations are clearly explained."
        ]
    },
    {
        "section": "Methods",
        "item": "Explain how quantitative variables were handled in the analyses. If applicable, describe which groupings were chosen and why.",
        "guidance": "Describe handling of quantitative data (e.g., categorized, continuous).",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Handling of quantitative variables is not described.",
            "Some information on quantitative variables is given but not complete.",
            "Quantitative variable handling and groupings are well described."
        ]
    },
    {
        "section": "Methods",
        "item": "Describe all statistical methods, including those used to control for confounding.",
        "guidance": "Outline your statistical approach, including confounder adjustment, missing data handling, etc.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Statistical methods are not described.",
            "Some statistical methods are given but confounders or missing data not addressed.",
            "All statistical methods, confounding, and missing data approaches are detailed."
        ]
    },
    {
        "section": "Results",
        "item": "Report numbers of individuals at each stage of study (e.g., eligible, included, follow-up, analyzed). Give reasons for non-participation at each stage. Consider use of a flow diagram.",
        "guidance": "Show a flow of participant numbers, with reasons for exclusions.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Numbers at each stage are not reported.",
            "Some numbers or reasons for non-participation are given, but incomplete.",
            "All numbers and reasons for non-participation are reported, with a flow diagram if applicable."
        ]
    },
    {
        "section": "Results",
        "item": "Give characteristics of study participants (e.g., demographic, clinical, social) and information on exposures and potential confounders. Indicate number of participants with missing data for each variable. Summarize follow-up time.",
        "guidance": "Provide descriptive stats for the sample, and report missing data.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Participant characteristics and missing data are not reported.",
            "Some characteristics or missing data are reported, but not all.",
            "All participant characteristics, confounders, and missing data are fully reported."
        ]
    },
    {
        "section": "Results",
        "item": "Report numbers of outcome events or summary measures over time.",
        "guidance": "Present main outcome data (events, summary measures).",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Outcome events or summary measures are not reported.",
            "Some outcome events are reported, but data is incomplete.",
            "Outcome events and summary measures are fully and clearly reported."
        ]
    },
    {
        "section": "Results",
        "item": "Give unadjusted estimates and, if applicable, confounder-adjusted estimates and their precision (e.g., 95% confidence interval). Report category boundaries when continuous variables were categorized. If relevant, consider translating estimates of relative risk into absolute risk.",
        "guidance": "Show both crude and adjusted results with precision (CIs), and define any group boundaries.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Estimates and precision are not reported.",
            "Estimates are given, but adjusted results or CIs are missing or incomplete.",
            "Both unadjusted and adjusted estimates, precision, and category boundaries are fully reported."
        ]
    },
    {
        "section": "Results",
        "item": "Report other analyses done (e.g., subgroup analyses and sensitivity analyses).",
        "guidance": "Describe any secondary, subgroup, or sensitivity analyses.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "No additional analyses are reported.",
            "Some secondary analyses are described, but not all relevant analyses.",
            "All secondary, subgroup, and sensitivity analyses are clearly reported."
        ]
    },
    {
        "section": "Discussion",
        "item": "Summarize key results with reference to study objectives.",
        "guidance": "Recap the main findings in light of the objectives.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Key results are not summarized.",
            "Results are summarized but not linked to study objectives.",
            "Key results are well summarized with clear reference to objectives."
        ]
    },
    {
        "section": "Discussion",
        "item": "Discuss limitations of the study, taking into account sources of potential bias or imprecision. Discuss both direction and magnitude of any potential bias.",
        "guidance": "Acknowledge weaknesses and possible biases; discuss direction and size.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Study limitations are not discussed.",
            "Some limitations are discussed, but bias or imprecision are not fully considered.",
            "Limitations, potential bias, and their direction and magnitude are thoroughly discussed."
        ]
    },
    {
        "section": "Discussion",
        "item": "Give a cautious overall interpretation of results considering objectives, limitations, multiplicity of analyses, results from similar studies, and other relevant evidence.",
        "guidance": "Discuss meaning and context, but avoid overstating conclusions.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Overall interpretation is missing or overstates conclusions.",
            "Interpretation is present but does not fully consider limitations or other evidence.",
            "Interpretation is cautious and well-contextualized with study limitations and existing literature."
        ]
    },
    {
        "section": "Discussion",
        "item": "Discuss the generalizability (external validity) of the study results.",
        "guidance": "Comment on how well results may apply elsewhere.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "No discussion of generalizability or external validity.",
            "Generalizability is mentioned but not fully discussed.",
            "Generalizability and external validity are clearly discussed."
        ]
    },
    {
        "section": "Other Information",
        "item": "Give the source of funding and the role of the funders for the present study and, if applicable, for the original study on which the present article is based.",
        "guidance": "State how the study was funded and any role of the sponsor.",
        "link": "https://www.strobe-statement.org/checklists/",
        "tag_options": [
            "Funding information is not provided.",
            "Funding is stated, but the role of funders is not described.",
            "Funding sources and funders' roles are fully described."
        ]
    }
]

score_labels = {1: "1 = Not addressed", 2: "2 = Partially", 3: "3 = Fully addressed"}
score_colors = {1: "#e74c3c", 2: "#f1c40f", 3: "#2ecc40"}  # Red, Yellow, Green

# --- Sections in first-appearance order ---
sections = []
for item in STROBE_ITEMS:
    if item["section"] not in sections:
        sections.append(item["section"])

# --- Session State ---
n_items = len(STROBE_ITEMS)
if "scores" not in st.session_state or len(st.session_state.scores) != n_items:
    st.session_state.scores = [2] * n_items
if "comments" not in st.session_state or len(st.session_state.comments) != n_items:
    st.session_state.comments = [""] * n_items
if "selected_tags" not in st.session_state or len(st.session_state.selected_tags) != n_items:
    st.session_state.selected_tags = [[] for _ in range(n_items)]
if "manual_comment_edit" not in st.session_state or len(st.session_state.manual_comment_edit) != n_items:
    st.session_state.manual_comment_edit = [False] * n_items

if "expand_states" not in st.session_state or len(st.session_state.expand_states) != len(sections):
    st.session_state.expand_states = [False] * len(sections)

st.set_page_config(page_title="STROBE Self-Assessment", layout="wide")
st.title("📝 STROBE Self-Assessment Tool for TriNetX Projects")

# --- Toolbar ---
col1, col2 = st.columns([1,2])
with col1:
    show_incomplete_only = st.checkbox("Show only incomplete items (score < 3)", value=False)
with col2:
    toc_mode = st.checkbox("📑 Show Table of Contents", value=True)

# Expand/Collapse all buttons
colA, colB = st.columns(2)
with colA:
    if st.button("Expand All Sections"):
        st.session_state.expand_states = [True] * len(sections)
with colB:
    if st.button("Collapse All Sections"):
        st.session_state.expand_states = [False] * len(sections)

# --- Sidebar: TOC ---
if toc_mode:
    st.sidebar.markdown("## 📑 Jump to Section")
    for sec in sections:
        st.sidebar.markdown(f"- [{sec}](#{sec.replace(' ', '-')})", unsafe_allow_html=True)

# --- Group items by section ---
section_items = defaultdict(list)
for i, item in enumerate(STROBE_ITEMS):
    section_items[item["section"]].append((i, item))

with st.form("strobe_form"):
    st.markdown("### Self-Assessment Checklist")
    for sec_idx, (section, items) in enumerate(section_items.items()):
        st.markdown(f'<a name="{section.replace(" ", "-")}"></a>', unsafe_allow_html=True)
        expanded = st.session_state.expand_states[sec_idx]
        with st.expander(section, expanded=expanded):
            any_rendered = False
            for idx, item in items:
                if show_incomplete_only and st.session_state.scores[idx] == 3:
                    continue
                any_rendered = True
                c1, c2, c3 = st.columns([3, 1, 2])
                with c1:
                    st.markdown(
                        f"<span style='font-weight:bold;'>{item['item']}</span>"
                        f"<br><span style='font-size:0.85em; color: #555;'>{item['guidance']}</span>",
                        unsafe_allow_html=True
                    )
                    st.markdown(f"<a href='{item['link']}' style='font-size:0.85em;' target='_blank'>[STROBE Guidance]</a>", unsafe_allow_html=True)
                with c2:
                    color = score_colors[st.session_state.scores[idx]]
                    st.markdown(
                        f"<span style='font-size:1.5em; color:{color};'>●</span>",
                        unsafe_allow_html=True,
                    )
                    score = st.selectbox(
                        "",
                        [1, 2, 3],
                        index=st.session_state.scores[idx] - 1,
                        format_func=lambda x: score_labels[x],
                        key=f"score_{idx}"
                    )
                    st.session_state.scores[idx] = score
                with c3:
                    st.markdown("**Select feedback tags:**")
                    tags = []
                    for tag_idx, tag in enumerate(item["tag_options"]):
                        checked = tag in st.session_state.selected_tags[idx]
                        new_checked = st.checkbox(tag, value=checked, key=f"tag_{idx}_{tag_idx}")
                        if new_checked:
                            tags.append(tag)
                    if not st.session_state.manual_comment_edit[idx]:
                        comment_val = "; ".join(tags)
                        st.session_state.comments[idx] = comment_val
                    st.session_state.selected_tags[idx] = tags
                    comment_input = st.text_area(
                        "Comments / Feedback",
                        value=st.session_state.comments[idx],
                        key=f"comment_{idx}"
                    )
                    if comment_input != "; ".join(st.session_state.selected_tags[idx]):
                        st.session_state.manual_comment_edit[idx] = True
                    else:
                        st.session_state.manual_comment_edit[idx] = False
                    st.session_state.comments[idx] = comment_input
                st.markdown("---")
            if not any_rendered:
                st.info("All items in this section are fully addressed (score = 3).")

    submitted = st.form_submit_button("Submit Self-Assessment")

if submitted:
    df = pd.DataFrame([
        {
            "Section": item["section"],
            "Checklist Item": item["item"],
            "Score": st.session_state.scores[idx],
            "Comments": st.session_state.comments[idx],
            "Guidance Link": item["link"]
        }
        for idx, item in enumerate(STROBE_ITEMS)
    ])
    st.success("Assessment Complete!")
    st.dataframe(df, use_container_width=True)

    percent_fully = round(100 * (df['Score'] == 3).sum() / len(df), 1)
    st.write(f"**Percent fully addressed:** {percent_fully}%")
    st.write(f"**Average score:** {round(df['Score'].mean(), 2)} / 3")

    low_scores = df[df["Score"] < 3]
    if not low_scores.empty:
        st.warning("### Areas for Improvement")
        for i, row in low_scores.iterrows():
            st.markdown(
                f"- **{row['Section']}**: [{row['Checklist Item']}]({row['Guidance Link']})  \n"
                f"  - Your score: {row['Score']}\n"
                f"  - Your comment: {row['Comments']}"
            )
    else:
        st.success("All items fully addressed! ✅")

    csv = df.to_csv(index=False).encode()
    st.download_button(
        label="📥 Download as CSV",
        data=csv,
        file_name="strobe_self_assessment.csv",
        mime="text/csv",
    )
