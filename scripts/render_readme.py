"""Refresh the results block in README.md from results/summary.json (between the results markers)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- results:start -->", "<!-- results:end -->"


def main() -> int:
    j = json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))
    w = j["worst_single_day_under_forecast_at_peak_eligible"]
    top = ", ".join(f"{r['ba']} ({r['mape'] * 100:.1f}%)" for r in j["ranking_overall_top5"])
    bot = ", ".join(f"{r['ba']} ({r['mape'] * 100:.1f}%)" for r in j["ranking_overall_bottom5"])
    mm = ", ".join(f"{r['ba']} ({r['median_daily_bias_pct'] * 100:+.0f}%)" for r in j["excluded_for_series_mismatch"]) or "none"
    first, last = j["first_date"], j["last_date"]
    p99 = j["p99_under_forecast_at_peak_eligible"]
    block = f"""{START}
> Status: **pipeline live (v{j['package_version']})**. Download, tidy, scoring, event slicing, data-quality rules, tests and a daily GitHub Action are in this repository. Results for the full public record, {first} to {last}, are in [`results/`](results/) and refreshed daily. The dashboard at [cardinalgrid.com/scorecard](https://cardinalgrid.com/scorecard) follows in October 2026.

## Results ({first} to {last}, generated {j['generated_at_utc'][:10]})

Read these as a first pass from public data, with the caveats below, not as a verdict on any operator.

- {j['balancing_authorities_total']} balancing authorities appear in the files; {j['balancing_authorities_scored']} report both demand and a day-ahead forecast; **{j['eligible_balancing_authorities']} are eligible for ranking** ({j['eligibility_rule']}). {j['ba_days_scored']:,} BA-days and {j['hours_scored']:,} hours were scored.
- **Demand-weighted day-ahead MAPE across eligible BAs: {j['demand_weighted_mape_eligible'] * 100:.2f}%**; median BA: {j['median_ba_mape_eligible'] * 100:.2f}%.
- **At the hour of the actual daily peak, the forecast was below actual demand on {j['share_of_ba_days_under_forecast_at_peak_eligible'] * 100:.0f}% of eligible BA-days.** One eligible BA-day in a hundred under-forecasts the peak by more than {abs(p99) * 100:.1f}%.
- Lowest MAPE: {top}. Highest among eligible: {bot}.
- Excluded for series mismatch (median daily bias beyond +/-25%, i.e. forecast and demand do not describe the same quantity): {mm}. Listed in `results/excluded_series_mismatch.csv`, not ranked.
- Worst single eligible BA-day at the peak hour: {w['ba']} on {w['date']}, forecast {abs(w['peak_hour_pct_error']) * 100:.0f}% below a {w['peak_demand_mw']:,.0f} MW peak. Single-day extremes may still be data problems; the percentile above is the robust figure.
- {j['hours_flagged_implausible']:,} hours were flagged implausible ({j['implausible_rule']}) and excluded from error metrics; EIA-imputed demand was {j['share_of_scored_hours_imputed'] * 100:.4f}% of scored hours.

Event slices (Winter Storm Uri, Elliott, the January 2024 Arctic storms, the January 2025 cold wave, and others) are in `results/events_by_ba.csv`; monthly and yearly tables per BA in `results/ba_monthly.csv` and `results/ba_yearly.csv`.

{END}
"""
    p = ROOT / "README.md"
    t = p.read_text(encoding="utf-8")
    a, b = t.index(START), t.index(END) + len(END) + 1
    p.write_text(t[:a] + block + t[b:], encoding="utf-8")
    print("README results block refreshed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
