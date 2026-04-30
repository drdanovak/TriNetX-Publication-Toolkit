import streamlit as st
import pandas as pd
import csv
import io
import re
import html
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Novak's TriNetX Outcomes Table 2 Generator
# Supports both TriNetX Measures of Association CSV exports and
# TriNetX Kaplan-Meier CSV exports. The app automatically detects
# the uploaded export type and normalizes each file into a single
# manuscript-style outcomes table.
# ============================================================

st.set_page_config(page_title="TriNetX Outcomes Table 2 Generator", layout="wide")


# -----------------------------
# Utility functions
# -----------------------------

def clean_cell(value: Any) -> str:
    """Return a stripped string while preserving meaningful text."""
    if value is None:
        return ""
    return str(value).replace("\ufeff", "").strip().strip('"').strip()


def norm_text(value: Any) -> str:
    """Normalize labels so exported header variants can be matched reliably."""
    value = clean_cell(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def is_blank_row(row: List[Any]) -> bool:
    return all(clean_cell(cell) == "" for cell in row)


def nonempty_count(row: List[Any]) -> int:
    return sum(1 for cell in row if clean_cell(cell) != "")


def safe_float(value: Any) -> Optional[float]:
    text = clean_cell(value)
    if text == "":
        return None
    text = text.replace(",", "").replace("%", "")
    try:
        return float(text)
    except Exception:
        return None


def safe_int(value: Any) -> Optional[int]:
    number = safe_float(value)
    if number is None:
        return None
    return int(round(number))


def html_escape(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def br_join(values: List[Any]) -> str:
    return "<br>".join(html_escape(v) for v in values)


def strip_leading_zero(text: str) -> str:
    if text.startswith("0."):
        return text[1:]
    if text.startswith("-0."):
        return "-." + text[3:]
    return text


def format_int(value: Any) -> str:
    number = safe_int(value)
    if number is None:
        return clean_cell(value)
    return f"{number:,}"


def format_percent_from_proportion(
    value: Any,
    decimals: int = 2,
    include_percent_symbol: bool = True,
    strip_zero: bool = False,
) -> str:
    """Format a proportion such as 0.0008 as 0.08% or 0.08."""
    number = safe_float(value)
    if number is None:
        return clean_cell(value)
    text = f"{number * 100:.{decimals}f}"
    if strip_zero:
        text = strip_leading_zero(text)
    if include_percent_symbol:
        text += "%"
    return text


def format_ratio(value: Any, decimals: int = 2, strip_zero: bool = False) -> str:
    number = safe_float(value)
    if number is None:
        return clean_cell(value)
    text = f"{number:.{decimals}f}"
    if strip_zero:
        text = strip_leading_zero(text)
    return text


def format_p_value(value: Any, decimals: int = 3, threshold: float = 0.001) -> str:
    number = safe_float(value)
    if number is None:
        raw = clean_cell(value)
        return raw
    if number < threshold:
        return "<.001"
    text = f"{number:.{decimals}f}"
    return strip_leading_zero(text)


def humanize_file_name(name: str) -> str:
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", name)
    stem = stem.replace("_", " ").replace("-", " ")
    stem = re.sub(r"\s+", " ", stem).strip()
    outcome_match = re.search(r"outcome\s*(\d+)", stem, flags=re.I)
    if outcome_match:
        return f"Outcome {outcome_match.group(1)}"
    return stem or "Outcome"


def infer_compact_cohort_label(raw_name: str, cohort_number: int) -> str:
    """Infer a compact display label while allowing the user to edit it later."""
    lowered = clean_cell(raw_name).lower()
    if "control" in lowered:
        return "Control"
    if "statin" in lowered:
        return "Statin"
    if cohort_number == 1 and re.search(r"\bxp\b|exposure|exposed|treated|treatment", lowered):
        return "Statin"
    if raw_name:
        return raw_name
    return f"Cohort {cohort_number}"


# -----------------------------
# TriNetX parsing functions
# -----------------------------

KNOWN_SECTION_LABELS = {
    "cohort statistics",
    "risk difference",
    "risk ratio",
    "odds ratio",
    "hazard ratio",
    "log rank test",
    "proportionality",
    "notes",
}

EXPORT_MOA = "Measures of Association"
EXPORT_KM = "Kaplan-Meier"
EXPORT_UNKNOWN = "Unknown"


def read_csv_rows(file_bytes: bytes) -> List[List[str]]:
    """Read TriNetX CSV bytes into rows without assuming a rectangular table."""
    text = file_bytes.decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    return [[clean_cell(cell) for cell in row] for row in rows]


def detect_export_type(rows: List[List[str]]) -> str:
    """Classify a TriNetX export as MOA or Kaplan-Meier using title and section labels."""
    joined = "\n".join(" ".join(clean_cell(cell) for cell in row) for row in rows)
    normalized = norm_text(joined)

    if "kaplan meier" in normalized:
        return EXPORT_KM
    if "measures of association" in normalized:
        return EXPORT_MOA

    section_labels = {norm_text(row[0]) for row in rows if row and nonempty_count(row) == 1}
    if "log rank test" in section_labels or ("hazard ratio" in section_labels and "proportionality" in section_labels):
        return EXPORT_KM
    if "risk difference" in section_labels or "risk ratio" in section_labels or "odds ratio" in section_labels:
        return EXPORT_MOA
    return EXPORT_UNKNOWN


def find_table_after_section(rows: List[List[str]], section_label: str) -> Tuple[List[str], List[List[str]]]:
    """
    Return the header row and data rows following a section label.
    This avoids hard-coded row numbers and tolerates blank spacer rows.
    """
    wanted = norm_text(section_label)
    start_index = None
    for idx, row in enumerate(rows):
        if not row:
            continue
        first_cell = norm_text(row[0])
        if first_cell == wanted:
            start_index = idx
            break

    if start_index is None:
        return [], []

    header_index = start_index + 1
    while header_index < len(rows) and is_blank_row(rows[header_index]):
        header_index += 1

    if header_index >= len(rows):
        return [], []

    headers = [clean_cell(cell) for cell in rows[header_index]]
    data_rows: List[List[str]] = []
    row_index = header_index + 1

    while row_index < len(rows):
        row = rows[row_index]
        if is_blank_row(row):
            break
        if nonempty_count(row) == 1 and norm_text(row[0]) in KNOWN_SECTION_LABELS:
            break
        data_rows.append([clean_cell(cell) for cell in row])
        row_index += 1

    return headers, data_rows


def table_rows_to_dicts(headers: List[str], rows: List[List[str]]) -> List[Dict[str, str]]:
    normalized_headers = [norm_text(h) for h in headers]
    output: List[Dict[str, str]] = []
    for row in rows:
        padded = row + [""] * max(0, len(headers) - len(row))
        record: Dict[str, str] = {}
        for raw_header, normalized_header, value in zip(headers, normalized_headers, padded):
            record[normalized_header] = clean_cell(value)
            record[clean_cell(raw_header)] = clean_cell(value)
        output.append(record)
    return output


def get_record_value(record: Dict[str, str], aliases: List[str]) -> str:
    normalized_aliases = [norm_text(alias) for alias in aliases]
    for alias in normalized_aliases:
        if alias in record:
            return record[alias]
    for alias in aliases:
        if alias in record:
            return record[alias]
    return ""


@dataclass
class ParsedOutcome:
    source_key: str
    source_file: str
    default_outcome: str
    export_type: str = EXPORT_UNKNOWN
    cohort1_raw: str = ""
    cohort2_raw: str = ""
    cohort1_label: str = "Cohort 1"
    cohort2_label: str = "Cohort 2"
    patients1: Optional[float] = None
    patients2: Optional[float] = None
    events1: Optional[float] = None
    events2: Optional[float] = None

    # Observed event proportions from Events / N, or TriNetX MOA Risk when present.
    risk1: Optional[float] = None
    risk2: Optional[float] = None

    # KM-specific fields.
    median_survival1: Optional[float] = None
    median_survival2: Optional[float] = None
    survival_probability_end1: Optional[float] = None
    survival_probability_end2: Optional[float] = None
    km_event_probability_end1: Optional[float] = None
    km_event_probability_end2: Optional[float] = None
    proportionality_p_value: Optional[float] = None

    # MOA-specific fields.
    risk_difference: Optional[float] = None
    risk_difference_lower: Optional[float] = None
    risk_difference_upper: Optional[float] = None
    risk_ratio: Optional[float] = None
    risk_ratio_lower: Optional[float] = None
    risk_ratio_upper: Optional[float] = None
    odds_ratio: Optional[float] = None
    odds_ratio_lower: Optional[float] = None
    odds_ratio_upper: Optional[float] = None

    # KM effect estimate.
    hazard_ratio: Optional[float] = None
    hazard_ratio_lower: Optional[float] = None
    hazard_ratio_upper: Optional[float] = None

    # Main p value and effect estimate used in the manuscript table.
    p_value: Optional[float] = None
    p_value_source: str = ""
    effect_measure_label: str = ""
    effect_measure_abbrev: str = ""
    effect_value: Optional[float] = None
    effect_lower: Optional[float] = None
    effect_upper: Optional[float] = None

    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def extract_notes(rows: List[List[str]]) -> List[str]:
    notes: List[str] = []
    for idx, row in enumerate(rows):
        if row and norm_text(row[0]) == "notes":
            note_idx = idx + 1
            while note_idx < len(rows) and not is_blank_row(rows[note_idx]):
                note_text = " ".join(clean_cell(cell) for cell in rows[note_idx] if clean_cell(cell))
                if note_text:
                    notes.append(note_text)
                note_idx += 1
            break
    return notes


def parse_cohort_statistics(parsed: ParsedOutcome, rows: List[List[str]]) -> None:
    cohort_headers, cohort_rows = find_table_after_section(rows, "Cohort Statistics")
    cohort_records = table_rows_to_dicts(cohort_headers, cohort_rows)
    if len(cohort_records) < 2:
        parsed.warnings.append("Could not find two cohort rows under 'Cohort Statistics'.")
        return

    c1, c2 = cohort_records[0], cohort_records[1]
    parsed.cohort1_raw = get_record_value(c1, ["Cohort Name", "Name"])
    parsed.cohort2_raw = get_record_value(c2, ["Cohort Name", "Name"])
    parsed.cohort1_label = infer_compact_cohort_label(parsed.cohort1_raw, 1)
    parsed.cohort2_label = infer_compact_cohort_label(parsed.cohort2_raw, 2)

    parsed.patients1 = safe_float(get_record_value(c1, ["Patients in Cohort", "Patients", "Patients N", "N"]))
    parsed.patients2 = safe_float(get_record_value(c2, ["Patients in Cohort", "Patients", "Patients N", "N"]))
    parsed.events1 = safe_float(get_record_value(c1, ["Patients with Outcome", "Events", "Patients with Events", "Event Count"]))
    parsed.events2 = safe_float(get_record_value(c2, ["Patients with Outcome", "Events", "Patients with Events", "Event Count"]))

    parsed.risk1 = safe_float(get_record_value(c1, ["Risk", "Incidence", "Cumulative Incidence"]))
    parsed.risk2 = safe_float(get_record_value(c2, ["Risk", "Incidence", "Cumulative Incidence"]))
    if parsed.risk1 is None and parsed.events1 is not None and parsed.patients1:
        parsed.risk1 = parsed.events1 / parsed.patients1
    if parsed.risk2 is None and parsed.events2 is not None and parsed.patients2:
        parsed.risk2 = parsed.events2 / parsed.patients2

    parsed.median_survival1 = safe_float(get_record_value(c1, ["Median Survival (Days)", "Median Survival", "Median"] ))
    parsed.median_survival2 = safe_float(get_record_value(c2, ["Median Survival (Days)", "Median Survival", "Median"] ))
    parsed.survival_probability_end1 = safe_float(get_record_value(c1, ["Survival Probability at End of Time Window", "Survival Probability"] ))
    parsed.survival_probability_end2 = safe_float(get_record_value(c2, ["Survival Probability at End of Time Window", "Survival Probability"] ))

    if parsed.survival_probability_end1 is not None:
        parsed.km_event_probability_end1 = 1 - parsed.survival_probability_end1
    if parsed.survival_probability_end2 is not None:
        parsed.km_event_probability_end2 = 1 - parsed.survival_probability_end2


def parse_moa_sections(parsed: ParsedOutcome, rows: List[List[str]]) -> None:
    rd_headers, rd_rows = find_table_after_section(rows, "Risk Difference")
    rd_records = table_rows_to_dicts(rd_headers, rd_rows)
    if rd_records:
        rd = rd_records[0]
        parsed.risk_difference = safe_float(get_record_value(rd, ["Risk Difference"]))
        parsed.risk_difference_lower = safe_float(get_record_value(rd, ["95 % CI Lower", "95 CI Lower", "CI Lower", "Lower"]))
        parsed.risk_difference_upper = safe_float(get_record_value(rd, ["95 % CI Upper", "95 CI Upper", "CI Upper", "Upper"]))
        parsed.p_value = safe_float(get_record_value(rd, ["p", "p Value", "p-value", "P Value"]))
        parsed.p_value_source = "Risk difference z test"
    else:
        parsed.warnings.append("Could not find a 'Risk Difference' section in this MOA export.")

    rr_headers, rr_rows = find_table_after_section(rows, "Risk Ratio")
    rr_records = table_rows_to_dicts(rr_headers, rr_rows)
    if rr_records:
        rr = rr_records[0]
        parsed.risk_ratio = safe_float(get_record_value(rr, ["Risk Ratio", "RR"]))
        parsed.risk_ratio_lower = safe_float(get_record_value(rr, ["95 % CI Lower", "95 CI Lower", "CI Lower", "Lower"]))
        parsed.risk_ratio_upper = safe_float(get_record_value(rr, ["95 % CI Upper", "95 CI Upper", "CI Upper", "Upper"]))
        parsed.effect_measure_label = "Risk Ratio"
        parsed.effect_measure_abbrev = "RR"
        parsed.effect_value = parsed.risk_ratio
        parsed.effect_lower = parsed.risk_ratio_lower
        parsed.effect_upper = parsed.risk_ratio_upper
    else:
        parsed.warnings.append("Could not find a 'Risk Ratio' section in this MOA export.")

    or_headers, or_rows = find_table_after_section(rows, "Odds Ratio")
    or_records = table_rows_to_dicts(or_headers, or_rows)
    if or_records:
        odds = or_records[0]
        parsed.odds_ratio = safe_float(get_record_value(odds, ["Odds Ratio", "OR"]))
        parsed.odds_ratio_lower = safe_float(get_record_value(odds, ["95 % CI Lower", "95 CI Lower", "CI Lower", "Lower"]))
        parsed.odds_ratio_upper = safe_float(get_record_value(odds, ["95 % CI Upper", "95 CI Upper", "CI Upper", "Upper"]))


def parse_km_sections(parsed: ParsedOutcome, rows: List[List[str]]) -> None:
    lr_headers, lr_rows = find_table_after_section(rows, "Log-Rank Test")
    lr_records = table_rows_to_dicts(lr_headers, lr_rows)
    if lr_records:
        log_rank = lr_records[0]
        parsed.p_value = safe_float(get_record_value(log_rank, ["p", "p Value", "p-value", "P Value"]))
        parsed.p_value_source = "Log-rank test"
    else:
        parsed.warnings.append("Could not find a 'Log-Rank Test' section in this Kaplan-Meier export.")

    hr_headers, hr_rows = find_table_after_section(rows, "Hazard Ratio")
    hr_records = table_rows_to_dicts(hr_headers, hr_rows)
    if hr_records:
        hr = hr_records[0]
        parsed.hazard_ratio = safe_float(get_record_value(hr, ["Hazard Ratio", "HR"]))
        parsed.hazard_ratio_lower = safe_float(get_record_value(hr, ["95 % CI Lower", "95 CI Lower", "CI Lower", "Lower"]))
        parsed.hazard_ratio_upper = safe_float(get_record_value(hr, ["95 % CI Upper", "95 CI Upper", "CI Upper", "Upper"]))
        parsed.effect_measure_label = "Hazard Ratio"
        parsed.effect_measure_abbrev = "HR"
        parsed.effect_value = parsed.hazard_ratio
        parsed.effect_lower = parsed.hazard_ratio_lower
        parsed.effect_upper = parsed.hazard_ratio_upper
    else:
        parsed.warnings.append("Could not find a 'Hazard Ratio' section in this Kaplan-Meier export.")

    prop_headers, prop_rows = find_table_after_section(rows, "Proportionality")
    prop_records = table_rows_to_dicts(prop_headers, prop_rows)
    if prop_records:
        prop = prop_records[0]
        parsed.proportionality_p_value = safe_float(get_record_value(prop, ["p", "p Value", "p-value", "P Value"]))


def parse_trinetx_outcome_file(uploaded_file: Any, source_index: int) -> ParsedOutcome:
    file_bytes = uploaded_file.getvalue()
    rows = read_csv_rows(file_bytes)
    source_key = f"{source_index}:{uploaded_file.name}"

    parsed = ParsedOutcome(
        source_key=source_key,
        source_file=uploaded_file.name,
        default_outcome=humanize_file_name(uploaded_file.name),
        export_type=detect_export_type(rows),
    )

    parsed.notes = extract_notes(rows)
    parse_cohort_statistics(parsed, rows)

    if parsed.export_type == EXPORT_MOA:
        parse_moa_sections(parsed, rows)
    elif parsed.export_type == EXPORT_KM:
        parse_km_sections(parsed, rows)
    else:
        parsed.warnings.append("Could not confidently detect export type. Attempted to parse both MOA and KM sections.")
        parse_moa_sections(parsed, rows)
        parse_km_sections(parsed, rows)
        if parsed.hazard_ratio is not None:
            parsed.export_type = EXPORT_KM
        elif parsed.risk_ratio is not None:
            parsed.export_type = EXPORT_MOA

    return parsed


# -----------------------------
# Formatting helpers for display records
# -----------------------------

def ratio_with_ci(value: Any, lower: Any, upper: Any, decimals: int = 2, prefix: str = "") -> str:
    if safe_float(value) is None:
        return ""
    estimate = format_ratio(value, decimals)
    if safe_float(lower) is not None and safe_float(upper) is not None:
        estimate = f"{estimate} ({format_ratio(lower, decimals)} to {format_ratio(upper, decimals)})"
    if prefix:
        return f"{prefix} {estimate}"
    return estimate


def percent_with_ci(value: Any, lower: Any, upper: Any, decimals: int = 2) -> str:
    if safe_float(value) is None:
        return ""
    if safe_float(lower) is None or safe_float(upper) is None:
        return format_percent_from_proportion(value, decimals, include_percent_symbol=True)
    return (
        f"{format_percent_from_proportion(value, decimals, include_percent_symbol=True)} "
        f"({format_percent_from_proportion(lower, decimals, include_percent_symbol=True)} to "
        f"{format_percent_from_proportion(upper, decimals, include_percent_symbol=True)})"
    )


def km_probability_for_display(parsed: ParsedOutcome, cohort_number: int, km_event_percent_mode: str) -> Optional[float]:
    if parsed.export_type != EXPORT_KM:
        return parsed.risk1 if cohort_number == 1 else parsed.risk2

    if km_event_percent_mode.startswith("1 - survival"):
        km_prob = parsed.km_event_probability_end1 if cohort_number == 1 else parsed.km_event_probability_end2
        if km_prob is not None:
            return km_prob

    return parsed.risk1 if cohort_number == 1 else parsed.risk2


def events_cell(
    parsed: ParsedOutcome,
    event_decimals: int,
    include_symbol: bool,
    km_event_percent_mode: str,
) -> str:
    risk1 = km_probability_for_display(parsed, 1, km_event_percent_mode)
    risk2 = km_probability_for_display(parsed, 2, km_event_percent_mode)
    return br_join([
        f"{format_int(parsed.events1)} ({format_percent_from_proportion(risk1, event_decimals, include_symbol)})",
        f"{format_int(parsed.events2)} ({format_percent_from_proportion(risk2, event_decimals, include_symbol)})",
    ])


def determine_effect_column_title(effect_labels: List[str]) -> str:
    unique_labels = {label for label in effect_labels if label}
    if unique_labels == {"Risk Ratio"}:
        return "Risk Ratio (95% CI)"
    if unique_labels == {"Hazard Ratio"}:
        return "Hazard Ratio (95% CI)"
    if unique_labels == {"Odds Ratio"}:
        return "Odds Ratio (95% CI)"
    return "Risk/Hazard Ratio (95% CI)"


# -----------------------------
# Table construction functions
# -----------------------------

def build_display_records(
    parsed_outcomes: List[ParsedOutcome],
    metadata_df: pd.DataFrame,
    event_decimals: int,
    rd_decimals: int,
    ratio_decimals: int,
    p_decimals: int,
    include_percent_symbol_in_events: bool,
    include_risk_difference: bool,
    include_odds_ratio: bool,
    include_detected_type_column: bool,
    km_event_percent_mode: str,
    effect_column_title_override: str,
    prefix_effect_estimates: bool,
) -> Tuple[List[Dict[str, Any]], List[str], str]:
    metadata = {}
    for _, row in metadata_df.iterrows():
        metadata[str(row["Source key"])] = row.to_dict()

    selected: List[Tuple[int, str, ParsedOutcome, Dict[str, Any]]] = []
    for parsed in parsed_outcomes:
        meta = metadata.get(parsed.source_key, {})
        include = bool(meta.get("Include", True))
        if not include:
            continue
        try:
            display_order = int(meta.get("Display order", 9999))
        except Exception:
            display_order = 9999
        section = clean_cell(meta.get("Section", ""))
        selected.append((display_order, section, parsed, meta))

    selected.sort(key=lambda item: (item[0], item[1], item[2].source_file))

    effect_labels = [parsed.effect_measure_label for _, _, parsed, _ in selected]
    auto_effect_title = determine_effect_column_title(effect_labels)
    effect_column_title = clean_cell(effect_column_title_override) or auto_effect_title

    records: List[Dict[str, Any]] = []
    active_section: Optional[str] = None

    unique_effect_labels = {label for label in effect_labels if label}
    should_prefix = prefix_effect_estimates or len(unique_effect_labels) > 1

    for _, section, parsed, meta in selected:
        if section and section != active_section:
            records.append({"_row_type": "section", "Section": section})
            active_section = section

        outcome_label = clean_cell(meta.get("Outcome", parsed.default_outcome)) or parsed.default_outcome
        c1_label = clean_cell(meta.get("Cohort 1 label", parsed.cohort1_label)) or parsed.cohort1_label
        c2_label = clean_cell(meta.get("Cohort 2 label", parsed.cohort2_label)) or parsed.cohort2_label

        record = {
            "_row_type": "data",
            "Outcome": outcome_label,
            "Cohort": br_join([c1_label, c2_label]),
            "Patients, N": br_join([format_int(parsed.patients1), format_int(parsed.patients2)]),
            "Events, n (%)": events_cell(
                parsed=parsed,
                event_decimals=event_decimals,
                include_symbol=include_percent_symbol_in_events,
                km_event_percent_mode=km_event_percent_mode,
            ),
            "p Value": html_escape(format_p_value(parsed.p_value, p_decimals)),
            effect_column_title: html_escape(
                ratio_with_ci(
                    parsed.effect_value,
                    parsed.effect_lower,
                    parsed.effect_upper,
                    ratio_decimals,
                    prefix=parsed.effect_measure_abbrev if should_prefix else "",
                )
            ),
        }
        if include_risk_difference:
            record["Risk Difference (95% CI)"] = html_escape(
                percent_with_ci(
                    parsed.risk_difference,
                    parsed.risk_difference_lower,
                    parsed.risk_difference_upper,
                    rd_decimals,
                )
            )
        if include_odds_ratio:
            record["Odds Ratio (95% CI)"] = html_escape(
                ratio_with_ci(parsed.odds_ratio, parsed.odds_ratio_lower, parsed.odds_ratio_upper, ratio_decimals)
            )
        if include_detected_type_column:
            record["Detected Table"] = html_escape(parsed.export_type)
        records.append(record)

    columns = [
        "Outcome",
        "Cohort",
        "Patients, N",
        "Events, n (%)",
    ]
    if include_risk_difference:
        columns.append("Risk Difference (95% CI)")
    columns.extend(["p Value", effect_column_title])
    if include_odds_ratio:
        columns.append("Odds Ratio (95% CI)")
    if include_detected_type_column:
        columns.append("Detected Table")

    return records, columns, effect_column_title


def build_html_table(
    title: str,
    records: List[Dict[str, Any]],
    columns: List[str],
    font_family: str,
    font_size_pt: int,
    table_width_percent: int,
    show_gridlines: bool,
    compact_spacing: bool,
    shade_section_rows: bool,
) -> str:
    border = "1px solid #000" if show_gridlines else "none"
    padding = "4px 6px" if compact_spacing else "7px 8px"
    section_bg = "#f2f2f2" if shade_section_rows else "#ffffff"

    title_html = f"<div class='table-title'>{html_escape(title)}</div>" if clean_cell(title) else ""

    css = f"""
<style>
.table-title {{
    font-family: {font_family};
    font-size: {font_size_pt + 1}pt;
    font-weight: bold;
    margin: 0 0 8px 0;
}}
table.outcomes-table {{
    border-collapse: collapse;
    width: {table_width_percent}%;
    font-family: {font_family};
    font-size: {font_size_pt}pt;
    line-height: 1.2;
}}
table.outcomes-table th,
table.outcomes-table td {{
    border: {border};
    padding: {padding};
    vertical-align: top;
}}
table.outcomes-table th {{
    font-weight: bold;
    text-align: center;
}}
table.outcomes-table td {{
    text-align: center;
}}
table.outcomes-table td.outcome-cell {{
    text-align: left;
    width: 27%;
}}
table.outcomes-table tr.section-row td {{
    background: {section_bg};
    font-weight: bold;
    text-align: left;
}}
</style>
"""

    html_parts = [css, title_html, "<table class='outcomes-table'>"]
    html_parts.append("<thead><tr>")
    for column in columns:
        html_parts.append(f"<th>{html_escape(column)}</th>")
    html_parts.append("</tr></thead>")
    html_parts.append("<tbody>")

    for record in records:
        if record.get("_row_type") == "section":
            html_parts.append(
                f"<tr class='section-row'><td colspan='{len(columns)}'>{html_escape(record.get('Section', ''))}</td></tr>"
            )
            continue
        html_parts.append("<tr>")
        for column in columns:
            css_class = " class='outcome-cell'" if column == "Outcome" else ""
            html_parts.append(f"<td{css_class}>{record.get(column, '')}</td>")
        html_parts.append("</tr>")

    html_parts.append("</tbody></table>")
    return "".join(html_parts)


def build_word_document_html(table_html: str) -> str:
    """Wrap table HTML in a minimal Word-compatible HTML document."""
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>TriNetX Outcomes Table</title>
</head>
<body>
{table_html}
</body>
</html>"""


def records_to_plain_dataframe(records: List[Dict[str, Any]], columns: List[str]) -> pd.DataFrame:
    plain_rows: List[Dict[str, str]] = []
    for record in records:
        if record.get("_row_type") == "section":
            plain_rows.append({columns[0]: record.get("Section", ""), **{col: "" for col in columns[1:]}})
        else:
            plain_record = {}
            for col in columns:
                text = str(record.get(col, ""))
                text = text.replace("<br>", "\n")
                text = re.sub(r"<[^>]+>", "", text)
                plain_record[col] = html.unescape(text)
            plain_rows.append(plain_record)
    return pd.DataFrame(plain_rows, columns=columns)


# -----------------------------
# Streamlit interface
# -----------------------------

st.title("Novak's TriNetX Outcomes Table 2 Generator")
st.write(
    "Upload one or more TriNetX Measures of Association or Kaplan-Meier CSV exports. "
    "The app will automatically detect the export type and combine the files into a single manuscript-style outcomes table."
)

uploaded_files = st.file_uploader(
    "Upload TriNetX outcome CSV files: Measures of Association or Kaplan-Meier",
    type=["csv", "txt"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Upload at least one TriNetX Measures of Association or Kaplan-Meier CSV file to begin.")
    st.stop()

parsed_outcomes: List[ParsedOutcome] = []
for idx, uploaded_file in enumerate(uploaded_files):
    try:
        parsed_outcomes.append(parse_trinetx_outcome_file(uploaded_file, idx))
    except Exception as exc:
        st.error(f"Could not parse {uploaded_file.name}: {exc}")

if not parsed_outcomes:
    st.stop()

moa_count = sum(1 for outcome in parsed_outcomes if outcome.export_type == EXPORT_MOA)
km_count = sum(1 for outcome in parsed_outcomes if outcome.export_type == EXPORT_KM)
unknown_count = sum(1 for outcome in parsed_outcomes if outcome.export_type == EXPORT_UNKNOWN)
st.info(
    f"Detected {moa_count} Measures of Association table(s), "
    f"{km_count} Kaplan-Meier table(s), and {unknown_count} unknown table(s)."
)

has_moa = moa_count > 0
has_km = km_count > 0

with st.sidebar:
    st.header("Table Options")
    table_title = st.text_area(
        "Table title",
        value=(
            "Table 2: Outcomes for Statins for the Primary Analysis of Alzheimer’s Disease, "
            "Related Outcomes, and All-Cause Mortality by statin group versus control"
        ),
        height=110,
    )
    default_section = st.text_input(
        "Default section heading",
        value="Main Analysis: All Statins Versus Control",
    )

    st.subheader("Number Formatting")
    event_decimals = st.number_input("Event percentage decimals", min_value=0, max_value=5, value=2, step=1)
    rd_decimals = st.number_input("Risk difference percentage decimals", min_value=0, max_value=5, value=2, step=1)
    ratio_decimals = st.number_input("Ratio decimals", min_value=0, max_value=5, value=2, step=1)
    p_decimals = st.number_input("p value decimals", min_value=1, max_value=5, value=3, step=1)
    include_percent_symbol_in_events = st.checkbox(
        "Include % sign in Events column parentheses",
        value=False,
        help="The Word example uses values such as 710 (0.08), while the column header supplies the percent sign.",
    )

    km_event_percent_mode = st.radio(
        "For Kaplan-Meier files, calculate the Events column percentage using:",
        options=[
            "Observed events / patients in cohort",
            "1 - survival probability at end of time window",
        ],
        index=0,
        help=(
            "Observed events / patients in cohort matches the usual n (%) convention. "
            "The KM option uses the end-of-window cumulative event probability implied by survival probability."
        ),
    )

    st.subheader("Columns")
    include_risk_difference = st.checkbox(
        "Show Risk Difference column",
        value=has_moa,
        help="MOA exports include risk difference. Kaplan-Meier exports generally do not, so the cell will be blank for KM rows.",
    )
    effect_column_title_override = st.text_input(
        "Effect estimate column title override",
        value="",
        placeholder="Leave blank for automatic title: Risk Ratio, Hazard Ratio, or Risk/Hazard Ratio",
    )
    prefix_effect_estimates = st.checkbox(
        "Prefix effect estimates with RR/HR",
        value=(has_moa and has_km),
        help="Useful when a table mixes MOA and KM rows in one effect-estimate column.",
    )
    include_odds_ratio = st.checkbox(
        "Add Odds Ratio column",
        value=False,
        help="Odds Ratio is parsed from MOA files and can be added if needed.",
    )
    include_detected_type_column = st.checkbox(
        "Add detected table type column",
        value=False,
        help="Useful for QA while mixing MOA and KM exports; usually hide this before manuscript export.",
    )

    st.subheader("Word-style Formatting")
    font_family = st.selectbox(
        "Font family",
        ["Times New Roman, Times, serif", "Arial, sans-serif", "Calibri, Arial, sans-serif", "Georgia, serif"],
        index=0,
    )
    font_size_pt = st.slider("Font size", min_value=8, max_value=14, value=10, step=1)
    table_width_percent = st.slider("Table width (%)", min_value=60, max_value=100, value=100, step=5)
    show_gridlines = st.checkbox("Show table gridlines", value=True)
    compact_spacing = st.checkbox("Compact spacing", value=True)
    shade_section_rows = st.checkbox("Shade section rows", value=False)

metadata_rows = []
for order, parsed in enumerate(parsed_outcomes, start=1):
    metadata_rows.append(
        {
            "Include": True,
            "Display order": order,
            "Section": default_section,
            "Outcome": parsed.default_outcome,
            "Cohort 1 label": parsed.cohort1_label,
            "Cohort 2 label": parsed.cohort2_label,
            "Detected table type": parsed.export_type,
            "Effect measure": parsed.effect_measure_label,
            "p value source": parsed.p_value_source,
            "Source file": parsed.source_file,
            "Source key": parsed.source_key,
        }
    )

metadata_df = pd.DataFrame(metadata_rows)

st.subheader("1. Review detected files and edit outcome labels")
st.caption(
    "The app automatically classifies each uploaded file as a Measures of Association or Kaplan-Meier export. "
    "Edit the Outcome, Section, and Cohort labels before generating the manuscript table. "
    "The Source key column is used internally so files remain matched correctly."
)

edited_metadata = st.data_editor(
    metadata_df,
    key="metadata_editor",
    use_container_width=True,
    hide_index=True,
    disabled=["Detected table type", "Effect measure", "p value source", "Source file", "Source key"],
    column_order=[
        "Include",
        "Display order",
        "Section",
        "Outcome",
        "Cohort 1 label",
        "Cohort 2 label",
        "Detected table type",
        "Effect measure",
        "p value source",
        "Source file",
        "Source key",
    ],
)

records, columns, effect_column_title = build_display_records(
    parsed_outcomes=parsed_outcomes,
    metadata_df=edited_metadata,
    event_decimals=int(event_decimals),
    rd_decimals=int(rd_decimals),
    ratio_decimals=int(ratio_decimals),
    p_decimals=int(p_decimals),
    include_percent_symbol_in_events=include_percent_symbol_in_events,
    include_risk_difference=include_risk_difference,
    include_odds_ratio=include_odds_ratio,
    include_detected_type_column=include_detected_type_column,
    km_event_percent_mode=km_event_percent_mode,
    effect_column_title_override=effect_column_title_override,
    prefix_effect_estimates=prefix_effect_estimates,
)

if not records:
    st.warning("No outcomes are currently selected for display.")
    st.stop()

st.subheader("2. Preview manuscript-style outcomes table")
st.caption(f"Current effect estimate column: {effect_column_title}")

table_html = build_html_table(
    title=table_title,
    records=records,
    columns=columns,
    font_family=font_family,
    font_size_pt=int(font_size_pt),
    table_width_percent=int(table_width_percent),
    show_gridlines=show_gridlines,
    compact_spacing=compact_spacing,
    shade_section_rows=shade_section_rows,
)

st.markdown(table_html, unsafe_allow_html=True)

warnings = []
for parsed in parsed_outcomes:
    for warning in parsed.warnings:
        warnings.append(f"{parsed.source_file}: {warning}")

if warnings:
    with st.expander("Parsing warnings", expanded=False):
        for warning in warnings:
            st.warning(warning)

with st.expander("Parsed source details", expanded=False):
    for parsed in parsed_outcomes:
        st.markdown(f"**{parsed.source_file}**")
        st.write(
            {
                "Detected table type": parsed.export_type,
                "Cohort 1 raw name": parsed.cohort1_raw,
                "Cohort 2 raw name": parsed.cohort2_raw,
                "Patients 1": parsed.patients1,
                "Events 1": parsed.events1,
                "Observed risk/event proportion 1": parsed.risk1,
                "KM survival probability at end 1": parsed.survival_probability_end1,
                "KM event probability at end 1": parsed.km_event_probability_end1,
                "Patients 2": parsed.patients2,
                "Events 2": parsed.events2,
                "Observed risk/event proportion 2": parsed.risk2,
                "KM survival probability at end 2": parsed.survival_probability_end2,
                "KM event probability at end 2": parsed.km_event_probability_end2,
                "Risk Difference": parsed.risk_difference,
                "Risk Difference CI Lower": parsed.risk_difference_lower,
                "Risk Difference CI Upper": parsed.risk_difference_upper,
                "Risk Ratio": parsed.risk_ratio,
                "Risk Ratio CI Lower": parsed.risk_ratio_lower,
                "Risk Ratio CI Upper": parsed.risk_ratio_upper,
                "Odds Ratio": parsed.odds_ratio,
                "Odds Ratio CI Lower": parsed.odds_ratio_lower,
                "Odds Ratio CI Upper": parsed.odds_ratio_upper,
                "Hazard Ratio": parsed.hazard_ratio,
                "Hazard Ratio CI Lower": parsed.hazard_ratio_lower,
                "Hazard Ratio CI Upper": parsed.hazard_ratio_upper,
                "Main p Value": parsed.p_value,
                "p Value Source": parsed.p_value_source,
                "Proportionality p Value": parsed.proportionality_p_value,
            }
        )
        if parsed.notes:
            st.caption("Notes: " + " ".join(parsed.notes))

st.subheader("3. Download outputs")

plain_df = records_to_plain_dataframe(records, columns)
word_html = build_word_document_html(table_html)

col1, col2, col3 = st.columns(3)
with col1:
    st.download_button(
        "Download Word-compatible .doc",
        data=word_html.encode("utf-8"),
        file_name="trinetx_outcomes_table2.doc",
        mime="application/msword",
    )
with col2:
    st.download_button(
        "Download HTML",
        data=word_html.encode("utf-8"),
        file_name="trinetx_outcomes_table2.html",
        mime="text/html",
    )
with col3:
    st.download_button(
        "Download CSV",
        data=plain_df.to_csv(index=False).encode("utf-8"),
        file_name="trinetx_outcomes_table2.csv",
        mime="text/csv",
    )

with st.expander("Copy table HTML", expanded=False):
    st.code(table_html, language="html")
