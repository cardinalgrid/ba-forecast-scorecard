# BA Forecast Scorecard

[![Tests](https://github.com/cardinalgrid/ba-forecast-scorecard/actions/workflows/tests.yml/badge.svg)](https://github.com/cardinalgrid/ba-forecast-scorecard/actions/workflows/tests.yml)
[![Daily update](https://github.com/cardinalgrid/ba-forecast-scorecard/actions/workflows/daily.yml/badge.svg)](https://github.com/cardinalgrid/ba-forecast-scorecard/actions/workflows/daily.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**How well do U.S. balancing authorities forecast their own load?**

EIA's Hourly Electric Grid Monitor (Form EIA-930) publishes, for every balancing authority in the Lower 48, the hourly demand that occurred and the day-ahead demand forecast the BA itself submitted, back to July 2015. That means the real forecast error of every U.S. grid operator is public. This project measures it, continuously.

> Status: **pipeline live (v0.1.0, September 2026)**. Download, tidy, scoring, event slicing, tests and a daily GitHub Action are in this repository. Results for 2024-01-01 to 2026-06-30 are in [`results/`](results/). The dashboard at [cardinalgrid.com/scorecard](https://cardinalgrid.com/scorecard) follows in October 2026.

## First results (2024H1–2026H1, generated 2026-09-08)

Read these as a first pass from public data, with the caveats below, not as a verdict on any operator.

- 64 balancing authorities in the files; 55 report both demand and a day-ahead forecast; **43 are eligible for ranking** (at least 180 scored days and mean demand >= 500 MW).
- **Demand-weighted day-ahead MAPE across eligible BAs: 4.19%**; median BA: 4.02%.
- **At the hour of the actual daily peak, the forecast was below actual demand on 66% of eligible BA-days.** Under-forecasting at the peak is the direction that costs reserves.
- Lowest MAPE: PGE (1.4%), SOCO (1.5%), AVA (1.7%), BPAT (2.0%), GCPD (2.0%). Highest: LDWP (9.8%), WALC (12.5%), WACM (15.3%), FPC (23.6%), PSEI (30.6%). The highest values are dominated by data-quality problems in the reported series (see below), which is why the data-quality layer exists.
- Worst single eligible BA-day at the peak hour: PSEI on 2026-01-30, forecast 67% below a 3508 MW peak. Treat as a data problem until verified.
- 4,314 hours were flagged implausible (forecast/demand outside [1/3, 3], or forecast <= 0; excluded from error metrics) and excluded from error metrics; EIA-imputed demand was 0.001% of scored hours.

Event slices (Winter Storm Elliott, the January 2024 Arctic storms, January 2025 cold wave, and others) are in `results/events_by_ba.csv`; monthly and yearly tables per BA in `results/ba_monthly.csv` and `results/ba_yearly.csv`.

## What it measures

- Day-ahead error by BA: MAPE, RMSE, bias, and error at the daily peak hour.
- Error on extreme-weather days (defined from NOAA station data) versus ordinary days.
- Named events: Winter Storm Uri (Feb 2021), Winter Storm Elliott (Dec 2022), the January 2024 Arctic storms, summer heat waves, and events of the current season as they happen.
- Trends 2015–2026 and a monthly ranking.
- A data-quality layer: missing hours, EIA-imputed values, implausible jumps, and genuine extremes versus telemetry faults (via [grid-data-sentinel](https://github.com/cardinalgrid/grid-data-sentinel)).

## Data

- EIA-930 six-month balance files (hourly demand, day-ahead demand forecast, EIA imputation flags, region), no API key needed: `https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_<YEAR>_<Jan_Jun|Jul_Dec>.csv`, back to July 2015.
- Event calendar with a public source per row: `src/ba_scorecard/data/events.csv`.
- NOAA station weather for extreme-day definitions: planned for v0.2.

## Usage

```bash
pip install -e .
ba-scorecard -v download --from 2024H1 --to 2026H1   # ~45 MB per half-year, cached in data/raw
ba-scorecard -v score    --from 2024H1 --to 2026H1   # writes results/
ba-scorecard -v update                               # refresh current half-year, rebuild results
pytest -q
```

## Metric definitions

- `error = forecast - demand` (MW); positive = over-forecast.
- `mape`, `bias_pct`, `rmse_mw` per BA-day, then hour-weighted across days.
- `peak_hour_pct_error`: error at the hour of the *actual* daily peak, as a share of that peak.
- `peak_mw_pct_error`: (max forecast - max demand) / max demand for the day.
- A BA-day needs at least 20 valid hours to be scored. Hours with demand or forecast <= 0 are excluded; hours with forecast/demand outside [1/3, 3] are flagged `implausible` and excluded (a data problem, not a forecast miss; the band is loose on purpose so real extreme-weather misses are kept).
- Rankings include BAs with at least 180 scored days and mean demand of at least 500 MW.

## Layout

```
ba-forecast-scorecard/
  src/ba_scorecard/   data.py (download/tidy), metrics.py, events.py, scorecard.py, cli.py
  src/ba_scorecard/data/events.csv
  tests/              unit tests and a real-header fixture
  results/            summary.json, rankings, monthly/yearly/event tables (committed; daily CSV is not)
  .github/workflows/  daily update (15:30 UTC)
```

## Known limitations

- Forecasts are as submitted by each BA to EIA and may be revised later; EIA's own quality checks apply to demand, not to forecasts.
- Several BAs report forecast or demand series with unit errors, zeros or stale values. The implausibility rule catches the gross cases; subtler ones remain and can inflate a BA's MAPE. High values in the ranking should be read as "data or forecast problem", not as "forecast problem".
- Imputed values are flagged, not corrected, in the headline metrics.
- Weather attribution (extreme-day definitions) is not yet implemented; event slices use fixed date windows from the public inquiries.
- No BA has been contacted for comment on these figures.

## Citing

Citation metadata is in `CITATION.cff` (GitHub shows a "Cite this repository" button) and `.zenodo.json`. Each release will be archived on Zenodo with a DOI; the concept DOI will be listed here with the first release.

## License

Apache-2.0. Reports: CC BY 4.0.
