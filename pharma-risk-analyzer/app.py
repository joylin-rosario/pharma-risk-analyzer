"""Mini Pharma Supply Chain Risk Analyzer.

Run: streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from risk_engine import score_shipments, validate_columns

DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "pharma_supply_chain.xlsx"

# --- palette (see CLAUDE.md / dataviz skill reference) ---------------------
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
STATUS = {"Low": "#0ca30c", "Medium": "#fab219", "High": "#ec835a", "Critical": "#d03b3b"}
RISK_ORDER = ["Low", "Medium", "High", "Critical"]
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SURFACE = "#fcfcfb"

st.set_page_config(page_title="Pharma Supply Chain Risk Analyzer", layout="wide")


def base_layout(fig: go.Figure, title: str, height: int = 360) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=INK_PRIMARY)),
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font=dict(color=INK_SECONDARY, family="system-ui, -apple-system, 'Segoe UI', sans-serif"),
        margin=dict(l=10, r=10, t=48, b=10),
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRIDLINE, tickfont=dict(color=INK_MUTED))
    fig.update_yaxes(showgrid=True, gridcolor=GRIDLINE, zeroline=False, tickfont=dict(color=INK_MUTED))
    return fig


@st.cache_data
def load_workbook(file) -> pd.DataFrame:
    return pd.read_excel(file, sheet_name="Shipments")


st.title("Pharma Supply Chain Risk Analyzer")
st.caption("Upload a shipment workbook or use the bundled sample data to flag high-risk pharma shipments.")

with st.sidebar:
    st.header("Data source")
    uploaded = st.file_uploader("Shipment workbook (.xlsx)", type=["xlsx"])
    source = uploaded if uploaded is not None else DEFAULT_DATA_PATH
    if uploaded is None:
        st.caption(f"Using bundled sample: {DEFAULT_DATA_PATH.name}")

try:
    raw_df = load_workbook(source)
except Exception as exc:
    st.error(f"Could not read the workbook: {exc}")
    st.stop()

missing = validate_columns(raw_df)
if missing:
    st.error(
        "The workbook is missing required columns: " + ", ".join(missing) +
        ". See CLAUDE.md for the expected schema."
    )
    st.stop()

df = score_shipments(raw_df)

with st.sidebar:
    st.header("Filters")
    categories = st.multiselect(
        "Product category", sorted(df["Product_Category"].unique()),
        default=sorted(df["Product_Category"].unique()),
    )
    destinations = st.multiselect(
        "Destination country", sorted(df["Destination_Country"].unique()),
        default=sorted(df["Destination_Country"].unique()),
    )
    risk_categories = st.multiselect(
        "Risk category", RISK_ORDER, default=RISK_ORDER,
    )
    min_score = st.slider("Minimum risk score", 0, 100, 0, step=5)

filtered = df[
    df["Product_Category"].isin(categories)
    & df["Destination_Country"].isin(destinations)
    & df["Risk_Category"].isin(risk_categories)
    & (df["Risk_Score"] >= min_score)
]

if filtered.empty:
    st.warning("No shipments match the current filters.")
    st.stop()

# --- KPI row -----------------------------------------------------------
high_risk = filtered[filtered["Risk_Category"].isin(["High", "Critical"])]
kpi_cols = st.columns(5)
kpi_cols[0].metric("Shipments in view", len(filtered))
kpi_cols[1].metric("High + Critical risk", len(high_risk))
kpi_cols[2].metric(
    "% high risk",
    f"{(len(high_risk) / len(filtered) * 100):.1f}%" if len(filtered) else "0%",
)
kpi_cols[3].metric("Avg risk score", f"{filtered['Risk_Score'].mean():.1f}")
kpi_cols[4].metric("Value at risk (USD)", f"${high_risk['Value_USD'].sum():,.0f}")

st.divider()

# --- Charts --------------------------------------------------------------
chart_row1 = st.columns(2)

with chart_row1[0]:
    counts = filtered["Risk_Category"].value_counts().reindex(RISK_ORDER, fill_value=0)
    fig = go.Figure(go.Bar(
        x=counts.index, y=counts.values,
        marker_color=[STATUS[c] for c in counts.index],
        text=counts.values, textposition="outside",
        hovertemplate="%{x}: %{y} shipments<extra></extra>",
    ))
    st.plotly_chart(base_layout(fig, "Shipments by risk category"), use_container_width=True)

with chart_row1[1]:
    avg_by_cat = filtered.groupby("Product_Category")["Risk_Score"].mean().sort_values(ascending=False)
    cat_colors = {cat: CATEGORICAL[i % len(CATEGORICAL)] for i, cat in enumerate(sorted(filtered["Product_Category"].unique()))}
    fig = go.Figure(go.Bar(
        x=avg_by_cat.index, y=avg_by_cat.values,
        marker_color=[cat_colors[c] for c in avg_by_cat.index],
        text=[f"{v:.0f}" for v in avg_by_cat.values], textposition="outside",
        hovertemplate="%{x}: avg score %{y:.1f}<extra></extra>",
    ))
    st.plotly_chart(base_layout(fig, "Average risk score by product category"), use_container_width=True)

chart_row2 = st.columns(2)

with chart_row2[0]:
    top_dest = (
        filtered[filtered["Risk_Category"].isin(["High", "Critical"])]["Destination_Country"]
        .value_counts().head(8).sort_values()
    )
    fig = go.Figure(go.Bar(
        x=top_dest.values, y=top_dest.index, orientation="h",
        marker_color="#2a78d6",
        text=top_dest.values, textposition="outside",
        hovertemplate="%{y}: %{x} high-risk shipments<extra></extra>",
    ))
    st.plotly_chart(base_layout(fig, "Top destinations by high-risk shipment count"), use_container_width=True)

with chart_row2[1]:
    cold_chain = filtered[filtered["Requires_Cold_Chain"]]
    fig = go.Figure()
    for cat in RISK_ORDER:
        subset = cold_chain[cold_chain["Risk_Category"] == cat]
        if subset.empty:
            continue
        fig.add_trace(go.Scatter(
            x=subset["Temp_Excursion_C"], y=subset["Risk_Score"],
            mode="markers", name=cat,
            marker=dict(color=STATUS[cat], size=9, line=dict(width=1, color=SURFACE)),
            hovertemplate="Excursion: %{x:.1f}°C<br>Risk score: %{y:.1f}<extra></extra>",
        ))
    fig.update_xaxes(title="Temperature excursion (°C beyond range)")
    fig.update_yaxes(title="Risk score")
    st.plotly_chart(base_layout(fig, "Cold-chain temperature excursions vs. risk score"), use_container_width=True)

st.divider()

# --- Flagged shipments table ----------------------------------------------
st.subheader(f"High-risk shipments ({len(high_risk)})")
st.caption("Sorted by risk score, most severe first. Risk_Factors explains which rules fired.")

display_cols = [
    "Shipment_ID", "Product_Name", "Product_Category", "Origin_Country",
    "Destination_Country", "Carrier", "Risk_Score", "Risk_Category",
    "Value_USD", "Risk_Factors",
]
table = high_risk.sort_values("Risk_Score", ascending=False)[display_cols]

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Risk_Score": st.column_config.ProgressColumn(
            "Risk_Score", min_value=0, max_value=100, format="%.0f",
        ),
        "Value_USD": st.column_config.NumberColumn("Value_USD", format="$%.0f"),
    },
)

st.download_button(
    "Download flagged shipments (CSV)",
    data=table.to_csv(index=False).encode("utf-8"),
    file_name="high_risk_shipments.csv",
    mime="text/csv",
)
