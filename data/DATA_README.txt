SWOT LakeSP time series — Pattison Lake & Long Lake (Thurston Co., WA)
=====================================================================

Prepared by the UNC Global Hydrology Lab (PI: Tamlin Pavelsky) for
Brian Muirhead, May 2026.

Source: NASA SWOT (Surface Water and Ocean Topography) mission, LakeSP
product, "prior" layer (PLD-matched lake observations). Data extracted
from the lab's local Parquet archive of all SWOT LakeSP granules
(2023-08 through 2025-10 at time of extract).

Lakes
-----

  Pattison Lake   PLD ID 7830178232   lon -122.7744, lat 46.9930
                  PLD reference WSE 46.699 m, reference area 0.6291 km^2

  Long Lake       PLD ID 7830180292   lon -122.7742, lat 47.0181
                  PLD reference WSE 46.313 m, reference area 1.0098 km^2

The lakes are ~2.8 km apart north-to-south, both within the Lacey/Olympia
metro area. "PLD" = SWOT Prior Lake Database (the static reference layer
the mission uses to key observations).

Files
-----

SWOT satellite observations (this directory):

  pattison_lake_7830178232_all.csv       33 rows — every real measurement
  pattison_lake_7830178232_science.csv   31 rows — science-quality subset

  long_lake_7830180292_all.csv           30 rows — every real measurement
  long_lake_7830180292_science.csv        6 rows — science-quality subset

In-situ ground-truth (locss/ subdirectory):

  locss/PAW2_pattison_lake_readings.csv  54 readings, 2021-10 → 2026-02
  locss/LGW2_long_lake_readings.csv      13 readings, 2021-10 → 2024-02
  locss/pattison_locss_vs_swot.png       3-panel comparison plot (Pattison)
  locss/pattison_locss_vs_swot_summary.txt   full alignment stats (Pattison)
  locss/long_locss_vs_swot.png           3-panel comparison plot (Long)
  locss/long_locss_vs_swot_summary.txt   full alignment stats (Long)
  locss/README.md                        LOCSS endpoint documentation

The "_all" files contain all valid SWOT observations of the lake (fill-value
rows and reprocessing duplicates already removed). The "_science" files
additionally apply the standard science-quality filter described below.

Science-quality filter applied to *_science.csv
-----------------------------------------------

A row is kept only if ALL three hold:

  quality_f   <= 1     (overall summary quality: 0=good, 1=suspect)
  ice_clim_f  <= 1     (climatological ice cover: 0=no ice, 1=partial)
  dark_frac   <= 0.5   (fraction of lake area too dark for radar return)

Note on cross-track distance (xtrk_dist)
----------------------------------------

The canonical SWOT science filter for averaging across many features is
  10 km <= |xtrk_dist| <= 60 km
to exclude near-nadir geometry (poor performance) and outer-swath
geometry (also poor).

Both of these lakes sit at xtrk_dist ~ 9.3–10.5 km — right at the inner
swath edge. Applying the strict 10 km cutoff would drop almost every
observation. For two named lakes with fixed geometry, that filter would
just bias the time series toward whichever passes happen to view them
favorably, so we have NOT applied it. The xtrk_dist column is included
so you can apply it yourself if desired.

Columns
-------

  time_str     ISO 8601 UTC timestamp of the SWOT observation
  wse          Water surface elevation, m (EGM2008 geoid)
  wse_u        WSE total uncertainty, m (1-sigma)
  wse_r_u      WSE random uncertainty component, m
  wse_std      Std. dev. of pixel-level WSE within the lake polygon, m
  area_total   Total lake area, km^2 (detected + dark water estimate)
  area_tot_u   area_total uncertainty, km^2
  area_detct   Directly detected (bright) water area, km^2
  area_det_u   area_detct uncertainty, km^2
  xtrk_dist    Cross-track distance from satellite nadir, METERS
  dark_frac    Fraction of lake area inferred as dark water (0–1)
  quality_f    Summary quality flag (0=good, 1=suspect, 2=degraded, 3=bad)
  qual_f_b     Bitwise quality flag (see SWOT product handbook for bits)
  ice_clim_f   Climatological ice flag (0=no, 1=partial, 2=full)
  ice_dyn_f    Dynamic (per-observation) ice flag; -999 if not retrieved
  partial_f    Partial observation flag (1 = lake only partly in scene)
  xovr_cal_q   Crossover calibration quality (0=good ... 3=bad)
  cycle        SWOT orbital cycle number
  pass         SWOT pass number within the cycle
  lake_name    Lake name from PLD
  lake_id      PLD lake ID

Geophysical correction columns (geoid, solid/load/pole tides, troposphere,
ionosphere) are NOT included — they are already applied to the reported `wse`.

Practical notes
---------------

- Long Lake has only 6 science-quality observations out of 30 valid passes.
  Most observations are flagged degraded (quality_f >= 2). The lake is small
  (~1 km^2) and sits at the inner swath edge; both factors contribute.
  We recommend using *_all.csv and inspecting per-row flags if you need a
  longer record, OR treating the 6 science-quality points as the reliable
  set and the rest as supplementary.

- Pattison fares better: 31 of 33 valid observations pass science quality.

- Both lakes sit on the same SWOT pass (pass 345, ascending) and appear
  together every overpass — so trends in one lake should usually be
  comparable to trends in the other.

In-situ comparison (LOCSS)
--------------------------

Both lakes carry staff gauges operated by LOCSS (Lake Observations by Citizen
Scientists), a NASA/UNC project that supplies SWOT cal/val ground truth.
LOCSS readings are the height of the water surface above the local gauge
zero, recorded in FEET by citizen observers. The locss/ subdirectory ships
the complete reading record for both gauges, pulled directly from the LOCSS
backend on 2026-05-19.

  Pattison (PAW2):  54 readings, 2021-10 → 2026-02-22  (gauge active)
  Long (LGW2):      13 readings, 2021-10 → 2024-02-08  (gauge plate noted
                                                        missing on the last
                                                        reading — likely
                                                        offline since)

Pattison alignment to SWOT
~~~~~~~~~~~~~~~~~~~~~~~~~~

The LOCSS readings are referenced to a local gauge zero with no published
elevation tie. By aligning the LOCSS height series to the SWOT WSE series in
time, we can recover the gauge zero in EGM2008 m as a constant offset:

  swot_wse  =  locss_height_m  +  offset

Using a robust subset (SWOT quality_f<=1 and LOCSS reading within 21 days
of the SWOT overpass, n=10):

  Gauge-zero estimate:        46.210 m  EGM2008
  Std of offset estimate:      0.058 m
  Robust subset residual range:           [-0.067, +0.117]  m
  Full residual range (n=31 obs):         [-0.700, +2.864]  m (one outlier
                                                              +2.864 m at
                                                              2024-02-06,
                                                              quality_f=2)
  After excluding |residual| > 1 m (n=30):
                   residual std 0.203 m, range [-0.700, +0.724] m

The agreement is sub-decimeter — inside the joint noise floor of SWOT (~10
cm spec) and citizen-science staff-gauge readings (~3 cm precision). For
practical comparison, add 46.210 m to any LOCSS height_m value to get a
SWOT-comparable orthometric WSE.

Caveat: this gauge-zero estimate is derived from satellite alignment, not
a field survey. We are awaiting confirmation from the LOCSS team on whether
an OPUS / RTK gauge-zero survey has been performed at PAW2.

See locss/pattison_locss_vs_swot.png and locss/pattison_locss_vs_swot_summary.txt
for the full comparison.

Long Lake alignment to SWOT
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The LGW2 gauge produced only 13 readings before the staff plate went
missing in February 2024. Of the 30 SWOT obs, only 7 fall inside the
LOCSS time span, and just 2 of those are science-quality (qual_f<=1).
No SWOT obs sit within 21 days of a LOCSS reading inside the overlap
window, so the robust criterion used for Pattison cannot be applied.
A fallback offset using the 2 in-range qual_f<=1 obs (median):

  Gauge-zero estimate (preliminary):   45.312 m  EGM2008
  n used:                              2  (large LOCSS interp gaps;
                                           weak constraint)
  Residual stats after excluding
    |residual| > 1 m (n=5):            std 0.294 m,
                                       range [-0.085, +0.663] m

Treat 45.312 m as a working estimate only — the small n and the long
LOCSS interpolation distances mean the uncertainty is far larger than
Pattison's ~6 cm. A real datum tie requires either re-instrumenting LGW2
and collecting more concurrent observations, or a direct RTK / OPUS
survey of the gauge zero.

See locss/long_locss_vs_swot.png and locss/long_locss_vs_swot_summary.txt
for the full comparison.

References
----------

- SWOT LakeSP Product Handbook (JPL D-105505):
  https://podaac.jpl.nasa.gov/SWOT?tab=mission-objectives&sections=about%2Bdata
- PLD = Prior Lake Database, see SWOT mission documentation.
- Lake ID encoding: first digits indicate continent and basin (7=NA, 7830=...).

Questions: james.gearon@unc.edu
