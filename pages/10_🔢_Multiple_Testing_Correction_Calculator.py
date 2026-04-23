import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

st.set_page_config(layout="wide")
st.title("Novak's Multiple Testing Correction Calculator")
st.markdown(
    "TriNetX studies often test many outcomes simultaneously, inflating the false-positive rate. "
    "Enter your raw p-values to apply Bonferroni, Holm–Bonferroni, or Benjamini–Hochberg (FDR) corrections "
    "and identify which outcomes remain significant after adjustment."
)

# ---- Sidebar ----
st.sidebar.header("⚙️ Settings")
alpha = st.sidebar.number_input(
    "Significance Threshold (α)", min_value=0.001, max_value=0.20,
    value=0.05, step=0.005, format="%.3f"
)
methods = st.sidebar.multiselect(
    "Correction Methods to Apply",
    ["Bonferroni", "Holm–Bonferroni", "Benjamini–Hochberg (FDR)", "Benjamini–Yekutieli"],
    default=["Bonferroni", "Benjamini–Hochberg (FDR)"]
)

# ---- Data Input ----
st.subheader("1. Enter Outcomes and Raw P-values")
input_mode = st.radio("Input Mode", ["Manual Entry", "Upload CSV"], horizontal=True)

df_input = None
if input_mode == "Upload CSV":
    uploaded = st.file_uploader(
        "Upload CSV with columns: Outcome, P-value", type=["csv"]
    )
    if uploaded:
        df_input = pd.read_csv(uploaded)
        st.dataframe(df_input, use_container_width=True)
else:
    default_data = pd.DataFrame({
        "Outcome": [
            "Acute MI", "Stroke", "Heart Failure", "Atrial Fibrillation",
            "DVT/PE", "All-cause Mortality", "Sepsis", "AKI"
        ],
        "P-value": [0.03, 0.01, 0.12, 0.048, 0.002, 0.18, 0.007, 0.09]
    })
    df_input = st.data_editor(default_data, num_rows="dynamic", use_container_width=True)

# ---- Correction Logic ----
def bonferroni_correction(pvals, alpha):
    adj = np.minimum(np.array(pvals) * len(pvals), 1.0)
    return adj, adj <= alpha


def holm_bonferroni_correction(pvals, alpha):
    pvals = np.array(pvals)
    n = len(pvals)
    order = np.argsort(pvals)
    adj = np.zeros(n)
    for rank, idx in enumerate(order):
        adj[idx] = min(pvals[idx] * (n - rank), 1.0)
    # enforce non-decreasing monotonicity in the sorted order
    for i in range(1, n):
        adj[order[i]] = max(adj[order[i]], adj[order[i - 1]])
    adj = np.minimum(adj, 1.0)
    reject = adj <= alpha
    return adj, reject


def bh_fdr_correction(pvals, alpha):
    pvals = np.array(pvals)
    n = len(pvals)
    order = np.argsort(pvals)
    adj = np.zeros(n)
    for rank, idx in enumerate(order):
        adj[idx] = pvals[idx] * n / (rank + 1)
    # enforce non-increasing monotonicity stepping backwards
    for i in range(n - 2, -1, -1):
        adj[order[i]] = min(adj[order[i]], adj[order[i + 1]])
    adj = np.minimum(adj, 1.0)
    return adj, adj <= alpha


def by_correction(pvals, alpha):
    pvals = np.array(pvals)
    n = len(pvals)
    c_m = np.sum(1.0 / np.arange(1, n + 1))
    order = np.argsort(pvals)
    adj = np.zeros(n)
    for rank, idx in enumerate(order):
        adj[idx] = pvals[idx] * n * c_m / (rank + 1)
    for i in range(n - 2, -1, -1):
        adj[order[i]] = min(adj[order[i]], adj[order[i + 1]])
    adj = np.minimum(adj, 1.0)
    return adj, adj <= alpha


METHOD_FNS = {
    "Bonferroni": bonferroni_correction,
    "Holm–Bonferroni": holm_bonferroni_correction,
    "Benjamini–Hochberg (FDR)": bh_fdr_correction,
    "Benjamini–Yekutieli": by_correction,
}

if df_input is not None and not df_input.empty:
    # Auto-detect columns
    cols = list(df_input.columns)
    p_col = next(
        (c for c in cols if any(k in c.lower() for k in ["p-val", "pval", "p_val", "p value"])),
        cols[1] if len(cols) > 1 else cols[0]
    )
    outcome_col = next(
        (c for c in cols if any(k in c.lower() for k in ["outcome", "variable", "test", "name"])),
        cols[0]
    )

    df_work = df_input[[outcome_col, p_col]].copy()
    df_work.columns = ["Outcome", "P-value"]
    df_work["P-value"] = pd.to_numeric(df_work["P-value"], errors="coerce")
    df_work = df_work.dropna(subset=["P-value"]).reset_index(drop=True)
    n = len(df_work)

    if n == 0:
        st.error("No valid numeric p-values found.")
    elif not methods:
        st.warning("Select at least one correction method in the sidebar.")
    else:
        pvals_arr = df_work["P-value"].values.astype(float)
        result = df_work.copy()
        result.rename(columns={"P-value": "Raw P-value"}, inplace=True)

        for method in methods:
            if method in METHOD_FNS:
                adj_p, sig = METHOD_FNS[method](pvals_arr, alpha)
                label = method.replace("Benjamini–", "").replace(" (FDR)", " FDR").replace("–", "-")
                result[f"Adj. P ({label})"] = adj_p.round(4)
                result[f"Sig. ({label})"] = ["✓" if s else "✗" for s in sig]

        # ---- Results Table ----
        st.subheader("2. Corrected P-values")
        fmt_result = result.copy()
        fmt_result["Raw P-value"] = fmt_result["Raw P-value"].apply(lambda x: f"{x:.4f}")
        for col in fmt_result.columns:
            if col.startswith("Adj. P"):
                fmt_result[col] = fmt_result[col].apply(lambda x: f"{x:.4f}" if isinstance(x, (int, float)) else x)
        st.dataframe(fmt_result, use_container_width=True)

        csv_out = result.to_csv(index=False)
        st.download_button(
            "Download Table (CSV)", data=csv_out,
            file_name="corrected_pvalues.csv", mime="text/csv"
        )

        # ---- Summary ----
        st.subheader("3. Significance Summary")
        raw_sig = int(np.sum(pvals_arr <= alpha))
        cols_summary = st.columns(1 + len(methods))
        with cols_summary[0]:
            st.metric("Raw Significant", f"{raw_sig} / {n}")
        for i, method in enumerate(methods):
            label = method.replace("Benjamini–", "").replace(" (FDR)", " FDR").replace("–", "-")
            sig_col = f"Sig. ({label})"
            if sig_col in result.columns:
                n_sig = int(result[sig_col].apply(lambda x: x == "✓").sum())
                with cols_summary[i + 1]:
                    st.metric(method.split("(")[0].strip(), f"{n_sig} / {n}")

        # ---- Plot ----
        st.subheader("4. Ranked P-value Plot")
        show_plot = st.checkbox("Show comparison plot", value=True)
        if show_plot:
            col_w, col_h = st.columns(2)
            fig_w = col_w.slider("Figure Width", 6, 18, 10)
            fig_h = col_h.slider("Figure Height", 4, 10, 5)
            log_scale = st.checkbox("Log scale Y-axis", value=False)

            order = np.argsort(pvals_arr)
            x = np.arange(1, n + 1)
            outcomes_sorted = result["Outcome"].values[order]
            raw_sorted = pvals_arr[order]

            fig, ax = plt.subplots(figsize=(fig_w, fig_h))
            ax.scatter(x, raw_sorted, label="Raw p-value", color="#2196F3", zorder=4, s=70, marker="D")

            palette = ["#F44336", "#4CAF50", "#FF9800", "#9C27B0"]
            for ci, method in enumerate(methods):
                label = method.replace("Benjamini–", "").replace(" (FDR)", " FDR").replace("–", "-")
                adj_col = f"Adj. P ({label})"
                if adj_col in result.columns:
                    adj_vals = result[adj_col].values[order]
                    ax.plot(x, adj_vals, label=method, color=palette[ci % len(palette)],
                            marker="o", markersize=5, linewidth=1.5)

            ax.axhline(alpha, color="black", linestyle="--", linewidth=1.2, label=f"α = {alpha}")
            ax.set_xticks(x)
            ax.set_xticklabels(outcomes_sorted, rotation=45, ha="right", fontsize=9)
            ax.set_ylabel("P-value" + (" (log scale)" if log_scale else ""))
            ax.set_title("Raw vs. Corrected P-values by Outcome")
            ax.legend(fontsize=9, loc="upper left")
            ax.grid(True, alpha=0.3)
            if log_scale:
                ax.set_yscale("log")
            plt.tight_layout()
            st.pyplot(fig)

            img_bytes = io.BytesIO()
            fig.savefig(img_bytes, format="png", dpi=300, bbox_inches="tight")
            img_bytes.seek(0)
            st.download_button(
                "Download Plot (PNG)", data=img_bytes,
                file_name="multiple_testing_correction.png", mime="image/png"
            )

        # ---- Method Explainer ----
        with st.expander("📖 Which correction method should I use?"):
            st.markdown("""
| Method | Controls | When to Use |
|--------|----------|-------------|
| **Bonferroni** | Family-Wise Error Rate (FWER) | Conservative; use when any false positive is costly (e.g., primary endpoint) |
| **Holm–Bonferroni** | FWER (less conservative) | Preferred over Bonferroni; uniformly more powerful |
| **Benjamini–Hochberg (FDR)** | False Discovery Rate | Exploratory analyses with many outcomes; allows some false positives |
| **Benjamini–Yekutieli** | FDR (under dependence) | When outcomes are correlated (e.g., related conditions in TriNetX) |

For TriNetX multi-outcome studies, **Benjamini–Hochberg** is typically recommended for secondary outcomes, while **Bonferroni** or **Holm** is appropriate for primary endpoints.
""")
