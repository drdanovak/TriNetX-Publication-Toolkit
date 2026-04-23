import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import re

st.set_page_config(layout="wide")
st.title("Novak's Competing Risks / Cumulative Incidence Function Plotter")
st.markdown(
    "Standard Kaplan-Meier curves treat competing events (e.g., death before the primary outcome) "
    "as censored, which overestimates cumulative incidence. This tool uses the **Aalen-Johansen estimator** "
    "to correctly compute and plot **Cumulative Incidence Functions (CIF)** for two cohorts."
)

with st.expander("📋 Expected Data Format"):
    st.markdown("""
Upload a CSV with one row per patient and these columns:

| Column | Values | Description |
|--------|--------|-------------|
| `time` | numeric | Days to event or censoring |
| `event` | 0, 1, or 2 | 0 = censored, 1 = primary event, 2 = competing event |
| `cohort` | 1 or 2 | Treatment group assignment |

**Example:** In a study of cancer recurrence with death as the competing risk:
- Event = 1 → cancer recurred
- Event = 2 → patient died before recurrence (competing event)
- Event = 0 → censored (lost to follow-up or end of study)

The tool computes CIF separately for each cohort and event type.
""")
    sample_df = pd.DataFrame({
        "time": [30, 45, 60, 90, 120, 35, 50, 80, 100, 150],
        "event": [1, 2, 0, 1, 2, 0, 1, 2, 1, 0],
        "cohort": [1, 1, 1, 1, 1, 2, 2, 2, 2, 2]
    })
    st.dataframe(sample_df, use_container_width=False)
    csv_sample = sample_df.to_csv(index=False)
    st.download_button("Download Sample CSV", data=csv_sample, file_name="sample_competing_risks.csv", mime="text/csv")


def aalen_johansen_cif(times, events, event_of_interest):
    """
    Compute the Aalen-Johansen CIF for a given event type.
    Returns arrays of (unique_times, cif_values).
    """
    times = np.array(times)
    events = np.array(events)

    unique_times = np.sort(np.unique(times[events > 0]))
    n_total = len(times)
    cif = 0.0
    overall_survival = 1.0
    cif_values = []
    prev_unique = []

    at_risk = n_total
    t_prev = 0

    for t in unique_times:
        # number at risk just before time t
        at_risk = np.sum(times >= t)
        if at_risk == 0:
            break
        d_primary = np.sum((times == t) & (events == 1))
        d_competing = np.sum((times == t) & (events == 2))
        d_total = d_primary + d_competing

        # CIF increment for event of interest
        d_event = np.sum((times == t) & (events == event_of_interest))
        cif += overall_survival * (d_event / at_risk)

        # Update overall survival
        overall_survival *= (1 - d_total / at_risk)

        prev_unique.append(t)
        cif_values.append(cif)

    return np.array(prev_unique), np.array(cif_values)


def make_step_arrays(times, cif_vals, max_time):
    """Extend step function to max_time for plotting."""
    if len(times) == 0:
        return np.array([0, max_time]), np.array([0, 0])
    t_step = np.concatenate([[0], np.repeat(times, 2)[:-1], [max_time]])
    c_step = np.concatenate([[0], np.repeat(cif_vals, 2)])
    # trim to max_time
    mask = t_step <= max_time
    return t_step[mask], c_step[mask]


# ---- File Upload ----
uploaded = st.file_uploader("Upload patient-level CSV", type=["csv"])

if uploaded:
    df = pd.read_csv(uploaded)
    df.columns = df.columns.str.strip().str.lower()

    # Auto-detect columns
    time_col = next((c for c in df.columns if "time" in c or "day" in c or "duration" in c), None)
    event_col = next((c for c in df.columns if "event" in c or "status" in c or "outcome" in c), None)
    cohort_col = next((c for c in df.columns if "cohort" in c or "group" in c or "arm" in c), None)

    st.subheader("Column Mapping")
    col1, col2, col3 = st.columns(3)
    time_col = col1.selectbox("Time column", df.columns.tolist(), index=df.columns.tolist().index(time_col) if time_col else 0)
    event_col = col2.selectbox("Event column (0/1/2)", df.columns.tolist(), index=df.columns.tolist().index(event_col) if event_col else 0)
    cohort_col = col3.selectbox("Cohort column (1/2)", df.columns.tolist(), index=df.columns.tolist().index(cohort_col) if cohort_col else 0)

    df = df[[time_col, event_col, cohort_col]].dropna()
    df.columns = ["time", "event", "cohort"]
    df["time"] = pd.to_numeric(df["time"], errors="coerce")
    df["event"] = pd.to_numeric(df["event"], errors="coerce").astype(int)
    df["cohort"] = pd.to_numeric(df["cohort"], errors="coerce").astype(int)
    df = df.dropna()

    cohorts = sorted(df["cohort"].unique())
    if len(cohorts) < 2:
        st.error("Data must contain exactly 2 cohorts (values 1 and 2).")
    else:
        st.markdown(f"**{len(df):,} patients** across {len(cohorts)} cohorts loaded.")

        # ---- Sidebar customization ----
        st.sidebar.header("🎨 Plot Customization")
        plot_title = st.sidebar.text_input("Plot Title", "Cumulative Incidence Function")
        label1 = st.sidebar.text_input("Cohort 1 Label", "Cohort 1")
        label2 = st.sidebar.text_input("Cohort 2 Label", "Cohort 2")
        x_label = st.sidebar.text_input("X-axis Label", "Time (Days)")
        y_label = st.sidebar.text_input("Y-axis Label", "Cumulative Incidence")
        primary_label = st.sidebar.text_input("Primary Event Label", "Primary Event")
        competing_label = st.sidebar.text_input("Competing Event Label", "Competing Event")

        show_primary = st.sidebar.checkbox("Show Primary Event CIF", value=True)
        show_competing = st.sidebar.checkbox("Show Competing Event CIF", value=True)

        color_scheme = st.sidebar.radio("Color Scheme", ["Color", "Black & White"])
        if color_scheme == "Color":
            color1 = st.sidebar.color_picker("Cohort 1 Color", "#1f77b4")
            color2 = st.sidebar.color_picker("Cohort 2 Color", "#d62728")
        else:
            color1, color2 = "black", "gray"

        line_width = st.sidebar.slider("Line Width", 1.0, 5.0, 2.0)
        style2 = st.sidebar.selectbox("Cohort 2 Line Style", ["dashed", "solid", "dotted", "dashdot"])
        show_grid = st.sidebar.checkbox("Show Grid", value=True)
        fig_width = st.sidebar.slider("Figure Width (inches)", 6, 16, 10)
        fig_height = st.sidebar.slider("Figure Height (inches)", 4, 10, 6)
        title_fs = st.sidebar.slider("Title Font Size", 10, 28, 16)
        label_fs = st.sidebar.slider("Axis Label Font Size", 10, 20, 13)
        tick_fs = st.sidebar.slider("Tick Font Size", 8, 16, 11)
        legend_fs = st.sidebar.slider("Legend Font Size", 8, 16, 11)

        max_time_val = int(df["time"].max())
        max_time = st.sidebar.number_input("Maximum Time to Display", min_value=1, max_value=max_time_val, value=max_time_val)

        y_max = st.sidebar.slider("Y-axis Maximum", 0.1, 1.0, 1.0, step=0.05)

        # ---- Compute CIFs ----
        df1 = df[df["cohort"] == cohorts[0]]
        df2 = df[df["cohort"] == cohorts[1]]

        t1_p, cif1_p = aalen_johansen_cif(df1["time"], df1["event"], event_of_interest=1)
        t1_c, cif1_c = aalen_johansen_cif(df1["time"], df1["event"], event_of_interest=2)
        t2_p, cif2_p = aalen_johansen_cif(df2["time"], df2["event"], event_of_interest=1)
        t2_c, cif2_c = aalen_johansen_cif(df2["time"], df2["event"], event_of_interest=2)

        # ---- Summary Table ----
        st.subheader("Cumulative Incidence at Key Time Points")
        timepoints = st.multiselect(
            "Select time points for summary table",
            options=sorted(df["time"].unique()),
            default=sorted(df["time"].unique())[:min(5, len(df["time"].unique()))]
        )

        if timepoints:
            rows = []
            for tp in sorted(timepoints):
                def cif_at(t_arr, cif_arr, tp):
                    if len(t_arr) == 0:
                        return 0.0
                    idx = np.searchsorted(t_arr, tp, side="right") - 1
                    return float(cif_arr[idx]) if idx >= 0 else 0.0

                rows.append({
                    "Time": tp,
                    f"{label1} – {primary_label}": f"{cif_at(t1_p, cif1_p, tp):.3f}",
                    f"{label1} – {competing_label}": f"{cif_at(t1_c, cif1_c, tp):.3f}",
                    f"{label2} – {primary_label}": f"{cif_at(t2_p, cif2_p, tp):.3f}",
                    f"{label2} – {competing_label}": f"{cif_at(t2_c, cif2_c, tp):.3f}",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # ---- Plot ----
        st.subheader("Cumulative Incidence Function Plot")
        if st.button("Generate CIF Plot"):
            fig, ax = plt.subplots(figsize=(fig_width, fig_height))

            linestyle2 = style2

            if show_primary:
                ts, cs = make_step_arrays(t1_p, cif1_p, max_time)
                ax.step(ts, cs, where="post", color=color1, linewidth=line_width,
                        label=f"{label1} – {primary_label}")
                ts, cs = make_step_arrays(t2_p, cif2_p, max_time)
                ax.step(ts, cs, where="post", color=color2, linewidth=line_width,
                        linestyle=linestyle2, label=f"{label2} – {primary_label}")

            if show_competing:
                ts, cs = make_step_arrays(t1_c, cif1_c, max_time)
                ax.step(ts, cs, where="post", color=color1, linewidth=line_width,
                        linestyle="dotted", label=f"{label1} – {competing_label}")
                ts, cs = make_step_arrays(t2_c, cif2_c, max_time)
                ax.step(ts, cs, where="post", color=color2, linewidth=line_width,
                        linestyle="dashdot" if linestyle2 != "dashdot" else "dotted",
                        label=f"{label2} – {competing_label}")

            ax.set_xlim(0, max_time)
            ax.set_ylim(0, y_max)
            ax.set_title(plot_title, fontsize=title_fs)
            ax.set_xlabel(x_label, fontsize=label_fs)
            ax.set_ylabel(y_label, fontsize=label_fs)
            ax.tick_params(axis="both", labelsize=tick_fs)
            ax.legend(fontsize=legend_fs, loc="upper left")
            if show_grid:
                ax.grid(True, alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig)

            img_bytes = io.BytesIO()
            fig.savefig(img_bytes, format="png", dpi=300, bbox_inches="tight")
            img_bytes.seek(0)
            cleaned_title = re.sub(r"[^\w\- ]", "", plot_title).strip().replace(" ", "_")
            st.download_button(
                "Download Plot (PNG)", data=img_bytes,
                file_name=f"{cleaned_title or 'cif_plot'}.png", mime="image/png"
            )

        # ---- Event counts ----
        with st.expander("Event Count Summary"):
            count_rows = []
            for c_val, c_label in zip(cohorts, [label1, label2]):
                sub = df[df["cohort"] == c_val]
                count_rows.append({
                    "Cohort": c_label,
                    "N": len(sub),
                    "Primary Events (event=1)": int((sub["event"] == 1).sum()),
                    "Competing Events (event=2)": int((sub["event"] == 2).sum()),
                    "Censored (event=0)": int((sub["event"] == 0).sum()),
                    "Median Follow-up (days)": f"{sub['time'].median():.1f}"
                })
            st.dataframe(pd.DataFrame(count_rows), use_container_width=True, hide_index=True)

else:
    st.info("Upload a CSV file to begin. See the data format guide above.")

with st.expander("📖 Why use Competing Risks analysis instead of Kaplan-Meier?"):
    st.markdown("""
**Kaplan-Meier** treats competing events (e.g., death from another cause) as **censored** observations.
This assumes that the competing event provides no information about the primary event probability —
an assumption that is rarely met in practice.

When competing events are common, KM **overestimates** the cumulative incidence of the primary event
because it implicitly assumes censored patients would have the same event rate as those still at risk.

**The Aalen-Johansen estimator** correctly accounts for competing events by estimating the probability
of experiencing event *k* before any other event. The CIF for event *k* at time *t* is:

> CIF_k(t) = Σ S(t⁻) × [d_k(t) / n(t)]

where S(t⁻) is the overall survival just before time t, d_k(t) is the number of event-k occurrences
at time t, and n(t) is the risk set.

**When to use this tool:**
- Mortality studies where patients may die from unrelated causes (competing with the primary cause)
- Time-to-readmission studies where death prevents readmission
- Any time-to-event analysis with multiple possible event types
""")
