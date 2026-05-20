# SWOT Lake Water Levels — Pattison & Long Lakes (Washington)

A simple Streamlit viewer for NASA SWOT satellite measurements of two lakes
near Lacey, Washington.

**Live app**: https://swot-lake-viewer.streamlit.app/

## What it shows

For each lake (Pattison and Long), the app displays:

- **Water level** over time, in meters or feet, with measurement uncertainty
  shown as error bars
- **Lake surface area** over time
- A **map** showing where the lake is
- A **CSV download** button for the data on screen

## Run locally

Requires Python 3.11 or newer.

```bash
git clone https://github.com/jameshgrn/swot-lake-viewer.git
cd swot-lake-viewer
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app will open in your web browser at `http://localhost:8501`.

## Data

The `data/` folder contains a snapshot of NASA SWOT LakeSP observations for
each lake. See `data/DATA_README.txt` for column definitions and details on
the quality filtering used to produce the `_science.csv` subsets.

Snapshot date: **2026-05-19**.

To update the snapshot, re-extract from your SWOT archive (or pull from
[Hydrocron](https://podaac.jpl.nasa.gov/hydrocron)) and replace the CSVs in
`data/`. The app picks them up on the next reload.

## Lakes

| Lake | PLD ID | Location | Reference WSE | Reference area |
|------|--------|----------|---------------|----------------|
| Pattison Lake | 7830178232 | 46.9930° N, 122.7744° W | 46.699 m EGM2008 | 0.6291 km² |
| Long Lake     | 7830180292 | 47.0181° N, 122.7742° W | 46.313 m EGM2008 | 1.0098 km² |

Both lakes sit on SWOT pass 345 (ascending) and are observed together each
overpass.

## Credits

Prepared by the **UNC Global Hydrology Lab** (PI: Tamlin Pavelsky).

Contact: [james.gearon@unc.edu](mailto:james.gearon@unc.edu)

Data: NASA / JPL **SWOT LakeSP** product, accessed via
[Hydrocron](https://podaac.jpl.nasa.gov/hydrocron).

## License

MIT — see [LICENSE](LICENSE).
