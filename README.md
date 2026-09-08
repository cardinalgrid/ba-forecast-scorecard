# BA Forecast Scorecard

**How well do U.S. balancing authorities forecast their own load?**

EIA's Hourly Electric Grid Monitor (Form EIA-930) publishes, for every balancing authority in the Lower 48, the hourly demand that occurred and the day-ahead demand forecast the BA itself submitted, back to July 2015. That means the real forecast error of every U.S. grid operator is public. This project measures it, continuously.

> Status: **launching October 2026**. The pipeline and metric definitions are published here first; the dashboard at [cardinalgrid.com/scorecard](https://cardinalgrid.com/scorecard) follows.

## What it measures

- Day-ahead error by BA: MAPE, RMSE, bias, and error at the daily peak hour.
- Error on extreme-weather days (defined from NOAA station data) versus ordinary days.
- Named events: Winter Storm Uri (Feb 2021), Winter Storm Elliott (Dec 2022), the January 2024 Arctic storms, summer heat waves, and events of the current season as they happen.
- Trends 2015–2026 and a monthly ranking.
- A data-quality layer: missing hours, EIA-imputed values, implausible jumps, and genuine extremes versus telemetry faults (via [grid-data-sentinel](https://github.com/cardinalgrid/grid-data-sentinel)).

## Data

- EIA-930 hourly demand (`D`) and day-ahead demand forecast (`DF`) per BA: https://www.eia.gov/electricity/gridmonitor/ (API key required, free).
- NOAA ISD / GHCN station weather.
- Event calendar with sources in `data/events.csv`.

## Planned layout

```
ba-forecast-scorecard/
  src/scorecard/      download, clean, score, rank
  notebooks/          reproducible analyses behind each report
  data/               event calendar, BA metadata (no raw data committed)
  reports/            monthly PDF reports (each archived on Zenodo with a DOI)
  .github/workflows/  daily update
```

## Known limitations

- Forecasts are as submitted by each BA to EIA and may be revised later.
- Imputed values are flagged, not corrected, in the headline metrics.
- Weather attribution uses public stations, not each BA's internal weather zones.

## Citing

Each monthly report has its own Zenodo DOI; the concept DOI for the project will be listed here with the first release.

## License

Apache-2.0. Reports: CC BY 4.0.
