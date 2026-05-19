"""SWOT Lake Water Levels — Streamlit viewer for Pattison & Long Lakes (WA).

Designed for non-technical viewers: large readable text, plain language, no
required setup. Data is shipped in /data and updated by re-pushing the repo.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SWOT Lake Water Levels — Pattison & Long Lakes",
    page_icon="💧",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Lake metadata ────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
DATA_SNAPSHOT = "2026-05-19"

LAKES: dict[str, dict] = {
    "Pattison Lake (Lacey, WA)": {
        "pld_id": "7830178232",
        "lat": 46.9930,
        "lon": -122.7744,
        "pld_ref_wse_m": 46.699,
        "pld_ref_area_km2": 0.6291,
        "csv_all": "pattison_lake_7830178232_all.csv",
        "csv_science": "pattison_lake_7830178232_science.csv",
    },
    "Long Lake (Lacey, WA)": {
        "pld_id": "7830180292",
        "lat": 47.0181,
        "lon": -122.7742,
        "pld_ref_wse_m": 46.313,
        "pld_ref_area_km2": 1.0098,
        "csv_all": "long_lake_7830180292_all.csv",
        "csv_science": "long_lake_7830180292_science.csv",
    },
}


@st.cache_data
def load_lake(csv_name: str) -> pd.DataFrame:
    """Load a SWOT lake CSV from /data and parse times."""
    df = pd.read_csv(DATA_DIR / csv_name)
    df["time"] = pd.to_datetime(df["time_str"], utc=True).dt.tz_convert(None)
    return df.sort_values("time").reset_index(drop=True)


def m_to_ft(m: float) -> float:
    return m * 3.280839895


# ── Header ───────────────────────────────────────────────────────────────────
st.title("💧 SWOT Lake Water Levels")
st.markdown(
    "**Satellite-measured water levels and surface area for two lakes near Lacey, "
    "Washington.** Data come from NASA's SWOT mission and were last updated on "
    f"**{DATA_SNAPSHOT}**."
)

# ── Lake picker ──────────────────────────────────────────────────────────────
lake_name = st.selectbox(
    "Which lake?",
    options=list(LAKES.keys()),
    index=0,
    help="Pick the lake you want to see.",
)
lake = LAKES[lake_name]

# ── Map (collapsible) ────────────────────────────────────────────────────────
with st.expander(f"Where is {lake_name}?  (click to show on a map)"):
    st.map(
        pd.DataFrame({"lat": [lake["lat"]], "lon": [lake["lon"]]}),
        zoom=11,
        use_container_width=True,
    )
    st.caption(
        f"Coordinates: {lake['lat']:.4f}° N, {abs(lake['lon']):.4f}° W"
    )

# ── Controls ─────────────────────────────────────────────────────────────────
col_q, col_u = st.columns([3, 2])
with col_q:
    science_only = st.checkbox(
        "Show only the most reliable measurements  (recommended)",
        value=True,
        help=(
            "When checked, only the highest-quality SWOT observations are shown. "
            "Unchecked, every valid measurement is plotted, including ones the "
            "mission flagged as degraded."
        ),
    )
with col_u:
    units = st.radio(
        "Units",
        options=["meters", "feet"],
        index=0,
        horizontal=True,
        help="Both meters and feet are above the EGM2008 geoid (a global sea-level model).",
    )

# ── Load data ────────────────────────────────────────────────────────────────
df_full = load_lake(lake["csv_all"])
df_sci = load_lake(lake["csv_science"])
df = df_sci if science_only else df_full

# Apply unit conversion to a working copy
df_disp = df.copy()
if units == "feet":
    elev_label = "Water level (feet above sea level)"
    area_unit = "acres"
    df_disp["wse_disp"] = m_to_ft(df_disp["wse"])
    df_disp["wse_u_disp"] = m_to_ft(df_disp["wse_u"])
    df_disp["area_disp"] = df_disp["area_total"] * 247.105   # km² → acres
    df_disp["area_u_disp"] = df_disp["area_tot_u"] * 247.105
else:
    elev_label = "Water level (meters above sea level)"
    area_unit = "square kilometers"
    df_disp["wse_disp"] = df_disp["wse"]
    df_disp["wse_u_disp"] = df_disp["wse_u"]
    df_disp["area_disp"] = df_disp["area_total"]
    df_disp["area_u_disp"] = df_disp["area_tot_u"]

# ── Headline metrics ─────────────────────────────────────────────────────────
n_show = len(df_disp)
n_total = len(df_full)
first = df_disp["time"].min() if n_show else None
last = df_disp["time"].max() if n_show else None

m1, m2, m3 = st.columns(3)
m1.metric("Observations shown", f"{n_show:,}", help=f"Out of {n_total:,} total measurements on file.")
m2.metric(
    "First measurement",
    first.strftime("%b %Y") if first is not None else "—",
)
m3.metric(
    "Latest measurement",
    last.strftime("%b %Y") if last is not None else "—",
)

st.divider()

# ── Water-level chart ────────────────────────────────────────────────────────
st.subheader("Water level over time")
if n_show == 0:
    st.info("No measurements to show with the current settings.")
else:
    fig_wse = go.Figure()
    fig_wse.add_trace(
        go.Scatter(
            x=df_disp["time"],
            y=df_disp["wse_disp"],
            mode="markers",
            marker=dict(size=9, color="#1f77b4"),
            error_y=dict(
                type="data",
                array=df_disp["wse_u_disp"],
                visible=True,
                thickness=1.2,
                width=4,
            ),
            name="Water level",
            hovertemplate=(
                "<b>%{x|%b %-d, %Y}</b><br>"
                "Water level: %{y:.2f} "
                + ("ft" if units == "feet" else "m")
                + "<br>± %{customdata:.2f}"
                + ("<extra></extra>")
            ),
            customdata=df_disp["wse_u_disp"],
        )
    )
    fig_wse.update_layout(
        height=400,
        margin=dict(l=40, r=10, t=10, b=40),
        xaxis_title="Date",
        yaxis_title=elev_label,
        font=dict(size=15),
        hoverlabel=dict(font_size=14),
    )
    st.plotly_chart(fig_wse, use_container_width=True)

st.caption(
    "Each dot is one SWOT satellite measurement. The thin vertical line through "
    "each dot is the measurement uncertainty (one standard deviation)."
)

# ── Area chart ───────────────────────────────────────────────────────────────
st.subheader("Lake surface area over time")
if n_show == 0:
    st.info("No measurements to show with the current settings.")
else:
    fig_area = go.Figure()
    fig_area.add_trace(
        go.Scatter(
            x=df_disp["time"],
            y=df_disp["area_disp"],
            mode="markers",
            marker=dict(size=9, color="#2ca02c"),
            error_y=dict(
                type="data",
                array=df_disp["area_u_disp"],
                visible=True,
                thickness=1.2,
                width=4,
            ),
            name="Surface area",
            hovertemplate=(
                "<b>%{x|%b %-d, %Y}</b><br>"
                f"Surface area: %{{y:.3f}} {area_unit}"
                "<extra></extra>"
            ),
        )
    )
    fig_area.update_layout(
        height=350,
        margin=dict(l=40, r=10, t=10, b=40),
        xaxis_title="Date",
        yaxis_title=f"Lake surface area ({area_unit})",
        font=dict(size=15),
        hoverlabel=dict(font_size=14),
    )
    st.plotly_chart(fig_area, use_container_width=True)

st.caption(
    "Surface area is how big the lake's visible water surface is from above. "
    "Small day-to-day wobbles can come from how much of the lake is "
    "obscured by clouds or vegetation."
)

st.divider()

# ── Download ─────────────────────────────────────────────────────────────────
st.subheader("Download the data")

csv_bytes = df.to_csv(index=False).encode("utf-8")
filename_suffix = "science" if science_only else "all"
st.download_button(
    label=f"⬇  Download CSV  ({n_show} rows)",
    data=csv_bytes,
    file_name=f"{lake['pld_id']}_{filename_suffix}.csv",
    mime="text/csv",
    use_container_width=True,
)
st.caption(
    "Plain CSV file. Opens in Excel, Numbers, or any text editor. "
    "Includes every column from NASA's SWOT data product."
)

st.divider()

# ── About panel ──────────────────────────────────────────────────────────────
with st.expander("About this data"):
    st.markdown(
        f"""
**Lake**: {lake_name}  &nbsp;·&nbsp;  Prior Lake Database ID **{lake["pld_id"]}**

**Reference values from NASA's static lake database (PLD)**
- Typical water level: {lake["pld_ref_wse_m"]:.2f} m  ({m_to_ft(lake["pld_ref_wse_m"]):.1f} ft)
- Typical surface area: {lake["pld_ref_area_km2"]:.2f} km²  ({lake["pld_ref_area_km2"] * 247.105:.0f} acres)

**Data source**  &nbsp; NASA SWOT mission, LakeSP product. SWOT is the Surface
Water and Ocean Topography satellite (launched December 2022), a joint
NASA / French / Canadian / UK mission. It measures the height of inland and
coastal water surfaces from space with ~10 cm accuracy.

**"Most reliable measurements"** means observations that pass NASA's standard
quality filter:
- Summary quality flag ≤ 1  (good or only slightly suspect)
- Ice cover flag ≤ 1  (no ice, or partial ice)
- Less than half the lake area flagged as too dark for the radar

**Why error bars?**  Each SWOT measurement is the average over many pixels
covering the lake. The error bar shows the uncertainty of that average — wider
bars mean noisier conditions (often clouds, wind, or off-nadir viewing geometry).

**Why the time series isn't evenly spaced**  SWOT visits these lakes roughly
every 21 days, but not every visit produces a usable observation.

**Updated**: {DATA_SNAPSHOT} (snapshot data; ask for a refresh if you want newer
observations included).
"""
    )

with st.expander("Citation / contact"):
    st.markdown(
        """
**Prepared by** the UNC Global Hydrology Lab (PI: Tamlin Pavelsky)

**Contact**: [james.gearon@unc.edu](mailto:james.gearon@unc.edu)

**Citation (data)**: NASA/JPL SWOT LakeSP Product, accessible via
[Hydrocron](https://podaac.jpl.nasa.gov/hydrocron) (PO.DAAC / NASA JPL).

**Source code**:
[github.com/jameshgrn/swot-lake-viewer](https://github.com/jameshgrn/swot-lake-viewer)
"""
    )
