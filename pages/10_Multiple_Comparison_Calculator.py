from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from statsmodels.stats.multitest import multipletests


st.set_page_config(
    page_title="TriNetX Multiple Comparisons Correction Tool",
    page_icon="📊",
    layout="wide",
)

SECTION_NAMES = {
    "Cohort Statistics",
    "Risk Difference",
    "Risk Ratio",
    "Odds Ratio",
    "Hazard Ratio",
}

METHOD_SPECS = {
    "Bonferroni": {
        "code": "bonferroni",
        "purpose": "Primary endpoints where any false positive is unacceptable",
        "family": "FWER",
    },
    "Holm–Bonferroni": {
        "code": "holm",
        "purpose": "Uniformly more powerful than Bonferroni with the same FWER control",
        "family": "FWER",
    },
    "Benjamini–Hochberg FDR": {
        "code": "fdr_bh",
        "purpose": "Recommended for secondary or exploratory outcomes",
        "family": "FDR",
    },
    "Benjamini–Yekutieli": {
        "code": "fdr_by",
        "purpose": "FDR-controlling under arbitrary dependence or correlated outcomes",
        "family": "FDR",
    },
}


def clean_row(row: List[str]) -> List[str]:
    return [str(cell).strip().replace("\ufeff", "") for cell in row]


def nonempty_rows_from_text(text: str) -> List[List[str]]:
    rows: List[List[str]] = []
    for raw_line in text.splitlines():
        parsed = next(csv.reader([raw_line]))
        cleaned = clean_row(parsed)
        if any(cell not in {"", '" "', " "} for cell in cleaned):
            rows.append(cleaned)
    return rows


def get_section(rows: List[List[str]], section_name: str) -> List[List[str]]:
    for i, row in enumerate(rows):
        if len(row) == 1 and row[0] == section_name:
            collected: List[List[str]] = []
            j = i + 1
            while j < len(rows):
                current = rows[j]
                if len(current) == 1 and current[0] in SECTION_NAMES:
                    break
                collected.append(current)
                j += 1
            return collected
    return []


def safe_float(value) -> float:
    try:
        if value is None:
            return np.nan
        text = str(value).strip().replace(",", "")
        if text == "":
            return np.nan
        return float(text)
    except Exception:
        return np.nan


def normalize_columns(df: pd.DataFrame) -> Dict[str, str]:
    return {
        col: str(col).strip().lower().replace("-", " ").replace("_", " ")
        for col in df.columns
    }


def find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    normalized = normalize_columns(df)
    reverse = {v: k for k, v in normalized.items()}
    for candidate in candidates:
        if candidate in reverse:
            return reverse[candidate]
    for original, norm in normalized.items():
        for candidate in candidates:
            if candidate in norm:
                return original
    return None


@st.cache_data(show_spinner=False)
def parse_trinetx_moa_text(text: str, source_name: str) -> Dict[str, object]:
    rows = nonempty_rows_from_text(text)
    if not rows:
        raise ValueError("File appears empty.")

    title = rows[0][0]
    if "Measures of Association Table" not in title:
        raise ValueError("This does not look like a TriNetX Measures of Association export.")

    result: Dict[str, object] = {
        "source_file": source_name,
        "title": title,
        "outcome": Path(source_name).stem,
    }

    cohort_stats = get_section(rows, "Cohort Statistics")
    if len(cohort_stats) >= 3:
        header = cohort_stats[0]
        header_index = {h: idx for idx, h in enumerate(header)}
        for cohort_num, data_row in ((1, cohort_stats[1]), (2, cohort_stats[2])):
            if len(data_row) >= len(header):
                result[f"cohort_{cohort_num}_name"] = data_row[header_index.get("Cohort Name", 1)]
                result[f"cohort_{cohort_num}_patients"] = safe_float(data_row[header_index.get("Patients in Cohort", 2)])
                result[f"cohort_{cohort_num}_with_outcome"] = safe_float(data_row[header_index.get("Patients with Outcome", 3)])
                result[f"cohort_{cohort_num}_risk"] = safe_float(data_row[header_index.get("Risk", 4)])

    risk_difference = get_section(rows, "Risk Difference")
    if len(risk_difference) >= 2:
        header, data = risk_difference[0], risk_difference[1]
        header_index = {h: idx for idx, h in enumerate(header)}
        result["risk_difference"] = safe_float(data[header_index.get("Risk Difference", 0)])
        result["risk_difference_ci_lower"] = safe_float(data[header_index.get("95 % CI Lower", 1)])
        result["risk_difference_ci_upper"] = safe_float(data[header_index.get("95 % CI Upper", 2)])
        result["z_value"] = safe_float(data[header_index.get("z", 3)])
        result["p_raw"] = safe_float(data[header_index.get("p", 4)])

    risk_ratio = get_section(rows, "Risk Ratio")
    if len(risk_ratio) >= 2:
        header, data = risk_ratio[0], risk_ratio[1]
        header_index = {h: idx for idx, h in enumerate(header)}
        result["risk_ratio"] = safe_float(data[header_index.get("Risk Ratio", 0)])
        result["risk_ratio_ci_lower"] = safe_float(data[header_index.get("95 % CI Lower", 1)])
        result["risk_ratio_ci_upper"] = safe_float(data[header_index.get("95 % CI Upper", 2)])

    odds_ratio = get_section(rows, "Odds Ratio")
    if len(odds_ratio) >= 2:
        header, data = odds_ratio[0], odds_ratio[1]
        header_index = {h: idx for idx, h in enumerate(header)}
        result["odds_ratio"] = safe_float(data[header_index.get("Odds Ratio", 0)])
        result["odds_ratio_ci_lower"] = safe_float(data[header_index.get("95 % CI Lower", 1)])
        result["odds_ratio_ci_upper"] = safe_float(data[header_index.get("95 % CI Upper", 2)])

    rr = result.get("risk_ratio")
    if rr is not None and pd.notna(rr):
        if float(rr) < 1:
            result["direction"] = "Lower in Cohort 1"
        elif float(rr) > 1:
            result["direction"] = "Higher in Cohort 1"
        else:
            result["direction"] = "No difference"

    return result


@st.cache_data(show_spinner=False)
def read_tabular_file(file_name: str, raw_bytes: bytes) -> pd.DataFrame:
    suffix = Path(file_name).suffix.lower()
    buffer = io.BytesIO(raw_bytes)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(buffer)
    for sep in [None, ",", "\t", ";"]:
        buffer.seek(0)
        try:
            if sep is None:
                return pd.read_csv(buffer, sep=None, engine="python")
            return pd.read_csv(buffer, sep=sep)
        except Exception:
            continue
    raise ValueError(f"Could not read {file_name} as CSV, TSV, or Excel.")


@st.cache_data(show_spinner=False)
def parse_uploaded_trinetx_files(file_payloads: List[Tuple[str, bytes]]) -> Tuple[pd.DataFrame, List[str]]:
    records: List[Dict[str, object]] = []
    errors: List[str] = []
    for file_name, raw_bytes in file_payloads:
        try:
            text = raw_bytes.decode("utf-8-sig", errors="ignore")
            records.append(parse_trinetx_moa_text(text, file_name))
        except Exception as exc:
            errors.append(f"{file_name}: {exc}")
    return pd.DataFrame(records), errors


def build_manual_dataset(df: pd.DataFrame, outcome_col: str, p_col: str) -> pd.DataFrame:
    out = df.copy()
    out = out.rename(columns={outcome_col: "outcome", p_col: "p_raw"})
    out["p_raw"] = out["p_raw"].apply(safe_float)
    out["include"] = True
    keep = ["outcome", "p_raw", "include"] + [c for c in out.columns if c not in {"outcome", "p_raw", "include"}]
    return out[keep]


def add_corrections(df: pd.DataFrame, alpha: float) -> Tuple[pd.DataFrame, pd.DataFrame]:
    work = df.copy()
    work = work.loc[work["include"]].copy()
    work["p_raw"] = work["p_raw"].apply(safe_float)
    work = work.loc[work["p_raw"].notna()].copy()
    work = work.sort_values("p_raw", ascending=True).reset_index(drop=True)

    if work.empty:
        raise ValueError("No usable p-values were found after filtering.")

    work["rank"] = np.arange(1, len(work) + 1)
    work["significant_raw"] = work["p_raw"] <= alpha

    summary_rows = []
    for display_name, spec in METHOD_SPECS.items():
        reject, adjusted, _, _ = multipletests(work["p_raw"].to_numpy(), alpha=alpha, method=spec["code"])
        method_key = display_name.lower().replace("–", "-").replace(" ", "_")
        work[f"adjusted_p__{method_key}"] = adjusted
        work[f"significant__{method_key}"] = reject
        summary_rows.append(
            {
                "Method": display_name,
                "Error control": spec["family"],
                "Interpretation": spec["purpose"],
                "Significant outcomes": int(np.sum(reject)),
                "Total tested": int(len(work)),
                "Share significant": float(np.mean(reject)),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    return work, summary_df


def make_downloadable_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def plot_pvalue_comparison(results_df: pd.DataFrame, alpha: float, use_log_scale: bool):
    series_map = {
        "Raw p": "p_raw",
        "Bonferroni": "adjusted_p__bonferroni",
        "Holm–Bonferroni": "adjusted_p__holm-bonferroni",
        "Benjamini–Hochberg FDR": "adjusted_p__benjamini-hochberg_fdr",
        "Benjamini–Yekutieli": "adjusted_p__benjamini-yekutieli",
    }

    plot_df = results_df[["outcome", "rank"] + list(series_map.values())].copy()
    plot_df = plot_df.rename(columns={v: k for k, v in series_map.items()})
    long_df = plot_df.melt(id_vars=["outcome", "rank"], var_name="Series", value_name="p_value")

    fig = px.line(
        long_df,
        x="rank",
        y="p_value",
        color="Series",
        markers=True,
        hover_data={"outcome": True, "rank": True, "p_value": ":.4g"},
        labels={"rank": "Outcome rank (sorted by raw p-value)", "p_value": "P-value"},
        title="Raw and adjusted p-values across outcomes",
    )
    fig.add_hline(y=alpha, line_dash="dash", annotation_text=f"alpha = {alpha:g}")
    if use_log_scale:
        fig.update_yaxes(type="log")
    fig.update_layout(legend_title_text="Series", xaxis=dict(dtick=1))
    return fig


def default_manual_column_selection(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    outcome_col = find_column(
        df,
        ["outcome", "outcome name", "endpoint", "result", "label", "name", "comparison", "title"],
    )
    p_col = find_column(
        df,
        ["p", "p value", "p-value", "pvalue", "raw p", "raw p value", "raw p-value"],
    )
    return outcome_col, p_col


st.title("TriNetX Multiple Comparisons Correction Tool")
st.write(
    "Upload raw TriNetX Measures of Association tables or a simple table of outcomes and p-values. "
    "The app will apply Bonferroni, Holm–Bonferroni, Benjamini–Hochberg, and Benjamini–Yekutieli corrections, "
    "then produce a comparison plot, a significance summary, and a CSV export."
)

with st.sidebar:
    st.header("Analysis settings")
    alpha = st.number_input("Alpha", min_value=0.0001, max_value=0.5, value=0.05, step=0.005, format="%.4f")
    input_mode = st.radio(
        "Input mode",
        ["TriNetX MOA files", "Manual p-value table"],
        help="Use raw TriNetX Measures of Association exports or a simple table that already contains p-values.",
    )
    use_log_scale = st.checkbox("Use log scale for the p-value plot", value=True)

st.info(
    "For raw TriNetX MOA exports, the app extracts the p-value from the Risk Difference section, because that is where "
    "TriNetX reports the test statistic and p-value in this export format."
)

source_df: Optional[pd.DataFrame] = None
parse_errors: List[str] = []

if input_mode == "TriNetX MOA files":
    uploads = st.file_uploader(
        "Upload one or more TriNetX Measures of Association CSV files",
        type=["csv", "txt"],
        accept_multiple_files=True,
    )

    if uploads:
        payloads = [(uploaded.name, uploaded.getvalue()) for uploaded in uploads]
        source_df, parse_errors = parse_uploaded_trinetx_files(payloads)
        if source_df is not None and not source_df.empty:
            source_df["include"] = True
            edit_cols = [
                "include",
                "outcome",
                "title",
                "p_raw",
                "risk_ratio",
                "odds_ratio",
                "direction",
                "cohort_1_name",
                "cohort_2_name",
                "source_file",
            ]
            present_cols = [c for c in edit_cols if c in source_df.columns]
            st.subheader("Parsed outcomes")
            st.caption("You can rename outcomes and exclude rows before running the correction.")
            source_df = st.data_editor(
                source_df[present_cols],
                use_container_width=True,
                num_rows="fixed",
                column_config={
                    "include": st.column_config.CheckboxColumn("Include"),
                    "outcome": st.column_config.TextColumn("Outcome"),
                    "p_raw": st.column_config.NumberColumn("Raw p-value", format="%.6g"),
                    "risk_ratio": st.column_config.NumberColumn("Risk Ratio", format="%.4f"),
                    "odds_ratio": st.column_config.NumberColumn("Odds Ratio", format="%.4f"),
                },
                disabled=[c for c in present_cols if c not in {"include", "outcome"}],
                key="trinetx_editor",
            )
    else:
        st.caption("Upload your raw MOA export files to begin.")

else:
    manual_upload = st.file_uploader(
        "Upload a CSV, TSV, or Excel file with at least an outcome column and a p-value column",
        type=["csv", "tsv", "txt", "xlsx", "xls"],
        accept_multiple_files=False,
    )
    pasted_text = st.text_area(
        "Or paste a small CSV/TSV table",
        height=180,
        placeholder="outcome,p\nStroke,0.013\nMyocardial infarction,0.22",
    )

    manual_df: Optional[pd.DataFrame] = None
    if manual_upload is not None:
        try:
            manual_df = read_tabular_file(manual_upload.name, manual_upload.getvalue())
        except Exception as exc:
            st.error(str(exc))
    elif pasted_text.strip():
        try:
            manual_df = pd.read_csv(io.StringIO(pasted_text), sep=None, engine="python")
        except Exception as exc:
            st.error(f"Could not parse pasted text: {exc}")

    if manual_df is not None and not manual_df.empty:
        st.subheader("Manual table preview")
        st.dataframe(manual_df, use_container_width=True)
        default_outcome_col, default_p_col = default_manual_column_selection(manual_df)
        col1, col2 = st.columns(2)
        with col1:
            outcome_col = st.selectbox(
                "Outcome column",
                options=list(manual_df.columns),
                index=list(manual_df.columns).index(default_outcome_col) if default_outcome_col in manual_df.columns else 0,
            )
        with col2:
            p_col = st.selectbox(
                "Raw p-value column",
                options=list(manual_df.columns),
                index=list(manual_df.columns).index(default_p_col) if default_p_col in manual_df.columns else 0,
            )
        source_df = build_manual_dataset(manual_df, outcome_col, p_col)
        st.subheader("Prepared outcomes")
        source_df = st.data_editor(
            source_df,
            use_container_width=True,
            num_rows="fixed",
            column_config={
                "include": st.column_config.CheckboxColumn("Include"),
                "p_raw": st.column_config.NumberColumn("Raw p-value", format="%.6g"),
            },
            disabled=[c for c in source_df.columns if c not in {"include", "outcome", "p_raw"}],
            key="manual_editor",
        )

if parse_errors:
    with st.expander("Parsing issues"):
        for item in parse_errors:
            st.write(f"- {item}")

if source_df is not None and not source_df.empty:
    try:
        results_df, summary_df = add_corrections(source_df, alpha=alpha)

        raw_sig_count = int(results_df["significant_raw"].sum())
        total_tested = int(len(results_df))

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Outcomes tested", total_tested)
        m2.metric("Raw p ≤ alpha", raw_sig_count)
        m3.metric("Bonferroni", int(results_df["significant__bonferroni"].sum()))
        m4.metric("Holm–Bonferroni", int(results_df["significant__holm-bonferroni"].sum()))
        m5.metric("BH / BY", f"{int(results_df['significant__benjamini-hochberg_fdr'].sum())} / {int(results_df['significant__benjamini-yekutieli'].sum())}")

        tab1, tab2, tab3 = st.tabs(["Adjusted results", "Comparison plot", "Method summary"])

        with tab1:
            pretty_results = results_df.copy()
            pretty_results = pretty_results.rename(
                columns={
                    "p_raw": "Raw p",
                    "risk_ratio": "Risk Ratio",
                    "odds_ratio": "Odds Ratio",
                    "direction": "Direction",
                    "adjusted_p__bonferroni": "Bonferroni adjusted p",
                    "adjusted_p__holm-bonferroni": "Holm–Bonferroni adjusted p",
                    "adjusted_p__benjamini-hochberg_fdr": "Benjamini–Hochberg adjusted p",
                    "adjusted_p__benjamini-yekutieli": "Benjamini–Yekutieli adjusted p",
                    "significant_raw": f"Raw p ≤ {alpha:g}",
                    "significant__bonferroni": "Bonferroni significant",
                    "significant__holm-bonferroni": "Holm–Bonferroni significant",
                    "significant__benjamini-hochberg_fdr": "Benjamini–Hochberg significant",
                    "significant__benjamini-yekutieli": "Benjamini–Yekutieli significant",
                }
            )
            preferred_cols = [
                "rank",
                "outcome",
                "Raw p",
                "Bonferroni adjusted p",
                "Holm–Bonferroni adjusted p",
                "Benjamini–Hochberg adjusted p",
                "Benjamini–Yekutieli adjusted p",
                f"Raw p ≤ {alpha:g}",
                "Bonferroni significant",
                "Holm–Bonferroni significant",
                "Benjamini–Hochberg significant",
                "Benjamini–Yekutieli significant",
                "Risk Ratio",
                "Odds Ratio",
                "Direction",
                "title",
                "source_file",
            ]
            display_cols = [c for c in preferred_cols if c in pretty_results.columns]
            st.dataframe(pretty_results[display_cols], use_container_width=True)
            st.download_button(
                "Download adjusted results CSV",
                data=make_downloadable_csv(pretty_results[display_cols]),
                file_name="multiple_comparisons_adjusted_results.csv",
                mime="text/csv",
            )

        with tab2:
            fig = plot_pvalue_comparison(results_df, alpha=alpha, use_log_scale=use_log_scale)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Outcomes are sorted by raw p-value. The dashed horizontal line marks the selected alpha threshold."
            )

        with tab3:
            st.dataframe(summary_df, use_container_width=True)
            st.write(
                "Bonferroni and Holm–Bonferroni control the family-wise error rate. "
                "Benjamini–Hochberg and Benjamini–Yekutieli control the false discovery rate, with BY being more conservative when outcomes may be correlated."
            )

    except Exception as exc:
        st.error(str(exc))
else:
    st.caption("No analysis has been run yet.")
