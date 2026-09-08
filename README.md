# BA Forecast Scorecard

[![Tests](https://github.com/cardinalgrid/ba-forecast-scorecard/actions/workflows/tests.yml/badge.svg)](https://github.com/cardinalgrid/ba-forecast-scorecard/actions/workflows/tests.yml)
[![Daily update](https://github.com/cardinalgrid/ba-forecast-scorecard/actions/workflows/daily.yml/badge.svg)](https://github.com/cardinalgrid/ba-forecast-scorecard/actions/workflows/daily.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**How well do U.S. balancing authorities forecast their own load?**

EIA's Hourly Electric Grid Monitor (Form EIA-930) publishes, for every balancing authority in the Lower 48, the hourly demand that occurred and the day-ahead demand forecast the BA itself submitted, back to July 2015. That means the real forecast error of every U.S. grid operator is public. This project measures it, continuously.

> Status: **pipeline live (v0.1.0, September 2026)**. Download, tidy, scoring, event slicing, data-quality rules, tests and a daily GitHub Action are in this repository. Results for the full public record, 2015-07-01 to 2026-06-30, are in [`results/`](results/). The dashboard at [cardinalgrid.com/scorecard](https://cardinalgrid.com/scorecard) follows in October 2026.

## First results (July 2015 – June 2026, generated 2026-09-08)

Read these as a first pass from public data, with the caveats below, not as a verdict on any operator.

- 72 balancing authorities appear in the files; 58 report both demand and a day-ahead forecast; **42 are eligible for ranking** (at least 180 scored days, mean demand >= 500 MW, and |median daily bias| <= 25%). 210,968 BA-days and 5,057,438 hours were scored.
- **Demand-weighted day-ahead MAPE across eligible BAs: 3.61%**; median BA: 4.21%.
- **At the hour of the actual daily peak, the forecast was below actual demand on 59% of eligible BA-days.** Under-forecasting at the peak is the direction that costs reserves.
- Lowest MAPE: PGE (1.8%), BPAT (2.0%), TVA (2.2%), GCPD (2.4%), ERCO (2.5%). Highest among eligible: LDWP (7.8%), WACM (8.6%), WALC (10.0%), TEPC (13.2%), FPC (22.1%).
- Excluded for series mismatch (median daily bias beyond ±25%, i.e. forecast and demand do not describe the same quantity): AEC (+93%), PSEI (-39%). These are data problems and are listed in `results/excluded_series_mismatch.csv`, not ranked.
- Worst single eligible BA-day at the peak hour: TVA on 2020-04-21, forecast 67% below a 43,225 MW peak. Treat as a data problem until verified.
- 22,836 hours were flagged implausible (forecast/demand outside [1/3, 3], or forecast <= 0; excluded from error metrics) and excluded from error metrics; EIA-imputed demand was 0.0008% of scored hours.

Event slices (Winter Storm Uri, Elliott, the January 2024 Arctic storms, the January 2025 cold wave, and others) are in `results/events_by_ba.csv`; monthly and yearly tables per BA in `results/ba_monthly.csv` and `results/ba_yearly.csv`.

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
- Rankings include BAs with at least 180 scored days, mean demand of at least 500 MW, and |median daily bias| <= 25%; BAs beyond that bias are listed in `results/excluded_series_mismatch.csv` as series mismatches.

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
