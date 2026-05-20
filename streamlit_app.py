"""SWOT Lake Water Levels — Streamlit viewer for Pattison & Long Lakes (WA).

Pulls live data from NASA's Hydrocron API (SWOT satellite observations) and
the LOCSS citizen-science staff-gauge backend on first page load each hour
(cached for 1 hour). If either source is unreachable, falls back transparently
to bundled CSV snapshots so the page never breaks. A "Refresh now" button
clears the cache on demand.

Designed for non-technical viewers: large readable text, plain language,
sensible defaults.
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SWOT Lake Water Levels — Pattison & Long Lakes",
    page_icon="💧",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Constants ────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
SNAPSHOT_DATE = "2026-05-19"
FT_PER_M = 3.280839895

HYDROCRON_URL = "https://soto.podaac.earthdatacloud.nasa.gov/hydrocron/v1/timeseries"
HYDROCRON_FIELDS = [
    "lake_id", "time_str", "wse", "wse_u", "wse_r_u", "wse_std",
    "area_total", "area_tot_u", "area_detct", "area_det_u",
    "xtrk_dist", "dark_frac",
    "quality_f", "qual_f_b", "ice_clim_f", "ice_dyn_f",
    "partial_f", "xovr_cal_q",
    "cycle_id", "pass_id",
]
HYDROCRON_START = "2023-01-01T00:00:00Z"
HYDROCRON_END = "2030-01-01T00:00:00Z"  # stable cache key
HYDROCRON_TIMEOUT_S = 20

LOCSS_URL_TMPL = (
    "https://liquidearthlake.website/index.php/json/getallreadings"
    "?gauge_inc_id={gauge_id}"
)
LOCSS_TIMEOUT_S = 15

LAKES: dict[str, dict] = {
    "Pattison Lake (Lacey, WA)": {
        "pld_id": "7830178232",
        "lake_name": "PATTISON LAKE",
        "lat": 46.9930,
        "lon": -122.7744,
        "pld_ref_wse_m": 46.699,
        "pld_ref_area_km2": 0.6291,
        "csv_fallback": "pattison_lake_7830178232_all.csv",
        # LOCSS
        "locss_gauge_id": 243,
        "locss_code": "PAW2",
        "locss_gauge_zero_m": 46.210,           # EGM2008 m (robust, n=10, std 6 cm)
        "locss_gauge_zero_quality": "robust",
        "locss_gauge_active": True,
        "locss_fallback": "PAW2_pattison_lake_readings.csv",
    },
    "Long Lake (Lacey, WA)": {
        "pld_id": "7830180292",
        "lake_name": "LONG LAKE",
        "lat": 47.0181,
        "lon": -122.7742,
        "pld_ref_wse_m": 46.313,
        "pld_ref_area_km2": 1.0098,
        "csv_fallback": "long_lake_7830180292_all.csv",
        # LOCSS
        "locss_gauge_id": 236,
        "locss_code": "LGW2",
        "locss_gauge_zero_m": 45.312,           # EGM2008 m (preliminary, n=2)
        "locss_gauge_zero_quality": "preliminary",
        "locss_gauge_active": False,            # plate noted missing 2024-02-08
        "locss_fallback": "LGW2_long_lake_readings.csv",
    },
}


# ── SWOT (Hydrocron) ─────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_hydrocron(lake_id: str) -> pd.DataFrame:
    """Fetch all valid SWOT observations for a lake from NASA Hydrocron.

    Raises on any failure. Cached for 1 hour. Call `.clear()` to refetch.
    """
    params = {
        "feature": "PriorLake",
        "feature_id": lake_id,
        "start_time": HYDROCRON_START,
        "end_time": HYDROCRON_END,
        "fields": ",".join(HYDROCRON_FIELDS),
        "output": "csv",
    }
    resp = requests.get(HYDROCRON_URL, params=params, timeout=HYDROCRON_TIMEOUT_S)
    resp.raise_for_status()
    payload = resp.json()
    csv_text = payload.get("results", {}).get("csv", "")
    if not csv_text:
        raise RuntimeError("Hydrocron returned an empty result set")

    df = pd.read_csv(io.StringIO(csv_text))
    df = df[df["time_str"] != "no_data"].copy()
    df = df.drop(columns=[c for c in df.columns if c.endswith("_units")], errors="ignore")
    df = df.rename(columns={"cycle_id": "cycle", "pass_id": "pass"})
    if df.empty:
        raise RuntimeError("Hydrocron returned no valid observations")
    return df


@st.cache_data(show_spinner=False)
def load_swot_fallback(csv_name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / csv_name)


def get_swot_data(lake: dict) -> tuple[pd.DataFrame, str, str | None]:
    try:
        return fetch_hydrocron(lake["pld_id"]), "live", None
    except Exception as exc:
        return load_swot_fallback(lake["csv_fallback"]), "snapshot", f"{type(exc).__name__}: {exc}"


# ── LOCSS (citizen-science staff-gauge readings) ─────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_locss(gauge_id: int) -> pd.DataFrame:
    """Fetch gauge readings from the LOCSS backend (undocumented JSON endpoint)."""
    resp = requests.get(LOCSS_URL_TMPL.format(gauge_id=gauge_id), timeout=LOCSS_TIMEOUT_S)
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        raise RuntimeError("LOCSS returned no readings")
    df = pd.DataFrame(rows)
    df["height_ft"] = pd.to_numeric(df["height"], errors="coerce")
    df = df.dropna(subset=["height_ft"]).copy()
    df["height_m"] = df["height_ft"] / FT_PER_M
    df["datetime_local"] = pd.to_datetime(
        df["date"].astype(str) + " " + df["time"].astype(str),
        errors="coerce",
    )
    df = df.dropna(subset=["datetime_local"]).reset_index(drop=True)
    return df.sort_values("datetime_local").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_locss_fallback(csv_name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / csv_name)
    df["datetime_local"] = pd.to_datetime(df["datetime_local"])
    df["height_ft"] = pd.to_numeric(df["height_ft"], errors="coerce")
    df["height_m"] = pd.to_numeric(df["height_m"], errors="coerce")
    return df.sort_values("datetime_local").reset_index(drop=True)


def get_locss_data(lake: dict) -> tuple[pd.DataFrame, str, str | None]:
    try:
        return fetch_locss(lake["locss_gauge_id"]), "live", None
    except Exception as exc:
        return load_locss_fallback(lake["locss_fallback"]), "snapshot", f"{type(exc).__name__}: {exc}"


# ── Helpers ──────────────────────────────────────────────────────────────────
def apply_science_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Standard SWOT LakeSP science-quality filter."""
    mask = (df["quality_f"] <= 1) & (df["ice_clim_f"] <= 1) & (df["dark_frac"] <= 0.5)
    return df.loc[mask].copy()


def m_to_ft(m: float | pd.Series) -> float | pd.Series:
    return m * FT_PER_M


# ── Header ───────────────────────────────────────────────────────────────────
st.title("💧 SWOT Lake Water Levels")
st.markdown(
    "**Satellite and citizen-science water level data for two lakes near Lacey, "
    "Washington.** Satellite observations come from NASA's SWOT mission via the "
    "[Hydrocron](https://podaac.jpl.nasa.gov/hydrocron) API. In-situ readings come "
    "from [LOCSS](https://locss.org/), the volunteer staff-gauge network led by "
    "UNC and Tennessee Tech."
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
    st.caption(f"Coordinates: {lake['lat']:.4f}° N, {abs(lake['lon']):.4f}° W")

# ── Fetch both data sources ──────────────────────────────────────────────────
with st.spinner("Loading observations…"):
    swot_df, swot_source, swot_err = get_swot_data(lake)
    locss_df, locss_source, locss_err = get_locss_data(lake)

swot_df["time"] = pd.to_datetime(swot_df["time_str"], utc=True).dt.tz_convert(None)
swot_df = swot_df.sort_values("time").reset_index(drop=True)

# ── Data-source banner ───────────────────────────────────────────────────────
status_col, refresh_col = st.columns([4, 1])
with status_col:
    bits = []
    if swot_source == "live":
        bits.append(f"📡 SWOT live ({len(swot_df)} obs)")
    else:
        bits.append(f"⚠️ SWOT snapshot ({SNAPSHOT_DATE})")
    if locss_source == "live":
        bits.append(f"👥 LOCSS live ({len(locss_df)} readings)")
    else:
        bits.append(f"⚠️ LOCSS snapshot ({SNAPSHOT_DATE})")

    if swot_source == "live" and locss_source == "live":
        st.success(" · ".join(bits) + "   (cached for up to 1 hour)")
    else:
        st.warning(" · ".join(bits))
        if swot_err:
            st.caption(f"_SWOT: {swot_err}_")
        if locss_err:
            st.caption(f"_LOCSS: {locss_err}_")

with refresh_col:
    if st.button("🔄 Refresh", use_container_width=True,
                 help="Re-fetch live data from NASA and LOCSS"):
        fetch_hydrocron.clear()
        fetch_locss.clear()
        st.rerun()

# ── Controls ─────────────────────────────────────────────────────────────────
col_q, col_u = st.columns([3, 2])
with col_q:
    science_only = st.checkbox(
        "Show only the most reliable satellite measurements  (recommended)",
        value=True,
        help=(
            "When checked, only the highest-quality SWOT observations are shown. "
            "Unchecked, every valid satellite measurement is plotted, including "
            "ones the mission flagged as degraded."
        ),
    )
with col_u:
    units = st.radio(
        "Units",
        options=["meters", "feet"],
        index=0,
        horizontal=True,
        help="Heights above sea level (EGM2008 geoid).",
    )

# ── Apply science filter ─────────────────────────────────────────────────────
swot_plot = apply_science_filter(swot_df) if science_only else swot_df

# ── Unit conversion (display copies) ─────────────────────────────────────────
swot_disp = swot_plot.copy()
if units == "feet":
    elev_label = "Water level (feet above sea level)"
    area_unit = "acres"
    swot_disp["wse_disp"] = m_to_ft(swot_disp["wse"])
    swot_disp["wse_u_disp"] = m_to_ft(swot_disp["wse_u"])
    swot_disp["area_disp"] = swot_disp["area_total"] * 247.105
    swot_disp["area_u_disp"] = swot_disp["area_tot_u"] * 247.105
else:
    elev_label = "Water level (meters above sea level)"
    area_unit = "square kilometers"
    swot_disp["wse_disp"] = swot_disp["wse"]
    swot_disp["wse_u_disp"] = swot_disp["wse_u"]
    swot_disp["area_disp"] = swot_disp["area_total"]
    swot_disp["area_u_disp"] = swot_disp["area_tot_u"]

# Align LOCSS readings to satellite elevation via gauge-zero offset
locss_disp = locss_df.copy()
locss_disp["wse_m_aligned"] = locss_disp["height_m"] + lake["locss_gauge_zero_m"]
if units == "feet":
    locss_disp["wse_disp"] = m_to_ft(locss_disp["wse_m_aligned"])
else:
    locss_disp["wse_disp"] = locss_disp["wse_m_aligned"]

# ── Headline metrics ─────────────────────────────────────────────────────────
n_swot = len(swot_disp)
n_swot_total = len(swot_df)
n_locss = len(locss_disp)

m1, m2, m3 = st.columns(3)
m1.metric("Satellite obs (shown)", f"{n_swot:,}",
          help=f"Out of {n_swot_total:,} total SWOT measurements.")
m2.metric("Gauge readings", f"{n_locss:,}",
          help=f"Citizen-science readings at {lake['locss_code']}.")
last_combined = max(
    [t for t in [
        swot_disp["time"].max() if n_swot else None,
        locss_disp["datetime_local"].max() if n_locss else None,
    ] if t is not None],
    default=None,
)
m3.metric("Most recent reading",
          last_combined.strftime("%b %Y") if last_combined is not None else "—")

st.divider()

# ── Water-level chart (SWOT + LOCSS overlay) ─────────────────────────────────
st.subheader("Water level over time")

fig_wse = go.Figure()
if n_swot > 0:
    fig_wse.add_trace(go.Scatter(
        x=swot_disp["time"], y=swot_disp["wse_disp"],
        mode="markers",
        marker=dict(size=9, color="#1f77b4"),
        error_y=dict(type="data", array=swot_disp["wse_u_disp"], visible=True,
                     thickness=1.2, width=4),
        name="Satellite (SWOT)",
        hovertemplate=(
            "<b>%{x|%b %-d, %Y}</b><br>"
            "SWOT satellite: %{y:.2f} "
            + ("ft" if units == "feet" else "m")
            + "<br>± %{customdata:.2f}<extra></extra>"
        ),
        customdata=swot_disp["wse_u_disp"],
    ))
if n_locss > 0:
    fig_wse.add_trace(go.Scatter(
        x=locss_disp["datetime_local"], y=locss_disp["wse_disp"],
        mode="markers",
        marker=dict(size=7, color="#ff7f0e", symbol="diamond",
                    line=dict(width=0.5, color="#5a3a00")),
        name=f"LOCSS gauge ({lake['locss_code']})",
        hovertemplate=(
            "<b>%{x|%b %-d, %Y}</b><br>"
            "LOCSS volunteer reading: %{y:.2f} "
            + ("ft" if units == "feet" else "m")
            + " (aligned to satellite via gauge zero)<extra></extra>"
        ),
    ))
if n_swot == 0 and n_locss == 0:
    st.info("No measurements to show with the current settings.")
else:
    fig_wse.update_layout(
        height=440,
        margin=dict(l=40, r=10, t=10, b=40),
        xaxis_title="Date",
        yaxis_title=elev_label,
        font=dict(size=15),
        hoverlabel=dict(font_size=14),
        legend=dict(orientation="h", y=1.05, x=0),
    )
    st.plotly_chart(fig_wse, use_container_width=True)

quality_note = (
    f"Gauge-zero alignment is **{lake['locss_gauge_zero_quality']}** "
    f"(offset = {lake['locss_gauge_zero_m']:.3f} m above sea level)."
)
if not lake["locss_gauge_active"]:
    quality_note += (
        f"  The {lake['locss_code']} gauge plate was noted missing in its last "
        "reading, so no new volunteer readings are coming in."
    )

st.caption(
    "**Blue dots** are satellite measurements from SWOT (vertical lines are the "
    "measurement uncertainty). **Orange diamonds** are volunteer readings from "
    "the LOCSS staff gauge at the lake, converted to the same sea-level reference "
    f"so the two series can be compared.  {quality_note}"
)

# ── Area chart (SWOT only) ───────────────────────────────────────────────────
st.subheader("Lake surface area over time")
if n_swot == 0:
    st.info("No satellite measurements to show with the current settings.")
else:
    fig_area = go.Figure()
    fig_area.add_trace(go.Scatter(
        x=swot_disp["time"], y=swot_disp["area_disp"],
        mode="markers",
        marker=dict(size=9, color="#2ca02c"),
        error_y=dict(type="data", array=swot_disp["area_u_disp"], visible=True,
                     thickness=1.2, width=4),
        name="Surface area",
        hovertemplate=(
            "<b>%{x|%b %-d, %Y}</b><br>"
            f"Surface area: %{{y:.3f}} {area_unit}<extra></extra>"
        ),
    ))
    fig_area.update_layout(
        height=350, margin=dict(l=40, r=10, t=10, b=40),
        xaxis_title="Date", yaxis_title=f"Lake surface area ({area_unit})",
        font=dict(size=15), hoverlabel=dict(font_size=14),
    )
    st.plotly_chart(fig_area, use_container_width=True)

st.caption(
    "Surface area is how big the lake's visible water surface is from above. "
    "Volunteer staff-gauge readings don't measure area — only the satellite can."
)

st.divider()

# ── Download ─────────────────────────────────────────────────────────────────
st.subheader("Download the data")
swot_dl_label = (
    f"⬇  Download satellite CSV  ({n_swot} rows"
    f"{', science-quality' if science_only else ', all'})"
)
st.download_button(
    label=swot_dl_label,
    data=swot_plot.to_csv(index=False).encode("utf-8"),
    file_name=f"{lake['pld_id']}_swot_{'science' if science_only else 'all'}.csv",
    mime="text/csv",
    use_container_width=True,
    key="dl_swot",
)
st.download_button(
    label=f"⬇  Download LOCSS gauge readings CSV  ({n_locss} rows)",
    data=locss_df.to_csv(index=False).encode("utf-8"),
    file_name=f"{lake['locss_code']}_locss_readings.csv",
    mime="text/csv",
    use_container_width=True,
    key="dl_locss",
)
st.caption(
    "Plain CSV files. Open in Excel, Numbers, or any text editor. "
    "Satellite file has every column NASA publishes for this lake."
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

**Two data sources**

- **SWOT satellite** — Surface Water and Ocean Topography mission (NASA / France
  / Canada / UK), launched December 2022. Measures inland and coastal water
  surface heights with ~10 cm accuracy. Visits each lake roughly every 21 days.
  Data fetched live via the [Hydrocron](https://podaac.jpl.nasa.gov/hydrocron) API.

- **LOCSS gauge** — Lake Observations by Citizen Scientists, a NASA-funded
  network operated by UNC and Tennessee Tech. Volunteers read a staff gauge
  (a yardstick mounted on a post in the lake) and submit the height. The
  {lake["locss_code"]} gauge for {lake_name} has gauge_inc_id = {lake["locss_gauge_id"]}.

**Aligning the two**  LOCSS readings are heights above a *local* gauge zero,
not a known elevation. The viewer adds an offset of
**{lake["locss_gauge_zero_m"]:.3f} m above sea level** (EGM2008) to put them on
the same scale as the satellite. This offset was derived by matching the two
series in time. The current alignment quality is **{lake["locss_gauge_zero_quality"]}**.
{"It is based on only n=2 useful satellite/gauge matches and should be confirmed by an RTK or OPUS field survey of the gauge zero." if lake["locss_gauge_zero_quality"] == "preliminary" else "Sub-decimeter agreement; well inside the joint noise floor of SWOT and citizen-science readings."}

**"Most reliable satellite measurements"** keeps observations that pass NASA's
standard quality filter:
- Summary quality flag ≤ 1  (good or only slightly suspect)
- Ice cover flag ≤ 1  (no ice, or partial ice)
- Less than half the lake area flagged as too dark for the radar

**Why error bars on satellite obs?**  Each SWOT measurement is the average over
many pixels covering the lake. The bar shows the uncertainty of that average.
LOCSS readings are made by eye and have an unstated uncertainty of roughly
± 3 cm (a tick mark on the staff gauge).

**Data freshness**  This page asks NASA and LOCSS for fresh data on the first
visit each hour and caches the result. Use the *Refresh* button to pull
immediately. If either service is unreachable, the page falls back to a
snapshot from {SNAPSHOT_DATE}.
"""
    )

with st.expander("Citation / contact"):
    st.markdown(
        """
**Prepared by** the UNC Global Hydrology Lab (PI: Tamlin Pavelsky)

**Contact**: [james.gearon@unc.edu](mailto:james.gearon@unc.edu)

**Data citations**
- NASA / JPL **SWOT LakeSP** product, via [Hydrocron](https://podaac.jpl.nasa.gov/hydrocron)
- **LOCSS** — Lake Observations by Citizen Scientists ([locss.org](https://locss.org/)),
  operated by UNC Chapel Hill (T. Pavelsky) and Tennessee Tech (S. Ghafoor)

**Source code**:
[github.com/jameshgrn/swot-lake-viewer](https://github.com/jameshgrn/swot-lake-viewer)
"""
    )
