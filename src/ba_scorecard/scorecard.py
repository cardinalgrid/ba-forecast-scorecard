"""Build the scorecard tables from tidy data and write them to ``results/``."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from . import __version__
from .events import load_events, tag_events
from .metrics import aggregate, daily_scores, rank

log = logging.getLogger(__name__)

SERIES_MISMATCH_BIAS = 0.25  # |median daily bias| above this means forecast and demand are not the same quantity

# BAs that report no demand (generation-only or aggregators) are dropped from rankings automatically
# because they never reach MIN_HOURS_PER_DAY valid hours.


def build(tidy: pd.DataFrame, results_dir: Path, recent_days: int = 30) -> dict:
    results_dir.mkdir(parents=True, exist_ok=True)
    daily = daily_scores(tidy)
    daily["month"] = pd.to_datetime(daily["date"]).dt.to_period("M").astype(str)
    daily["year"] = pd.to_datetime(daily["date"]).dt.year

    daily.to_csv(results_dir / "ba_daily.csv", index=False, float_format="%.6f")

    monthly = aggregate(daily, ["ba", "region", "month"])
    yearly = aggregate(daily, ["ba", "region", "year"])
    overall = aggregate(daily, ["ba", "region"])
    monthly.to_csv(results_dir / "ba_monthly.csv", index=False, float_format="%.6f")
    yearly.to_csv(results_dir / "ba_yearly.csv", index=False, float_format="%.6f")

    # Rankings: only BAs with meaningful coverage (>= 180 scored days), material demand (>= 500 MW mean)
    # and no series mismatch. A BA whose *median* daily bias exceeds +/-25% is reporting a forecast and a
    # demand that do not describe the same quantity (unit, footprint or column error); that is a data
    # problem, not a forecast problem, so it is listed separately instead of ranked.
    med_bias = daily[daily["scored"]].groupby("ba")["bias_pct"].median().rename("median_daily_bias_pct")
    overall = overall.merge(med_bias, on="ba", how="left")
    mismatch = overall[overall["median_daily_bias_pct"].abs() > SERIES_MISMATCH_BIAS]
    eligible = overall[
        (overall["days"] >= 180) & (overall["mean_demand_mw"] >= 500) & (overall["median_daily_bias_pct"].abs() <= SERIES_MISMATCH_BIAS)
    ]
    mismatch[["ba", "region", "days", "mean_demand_mw", "median_daily_bias_pct", "mape"]].to_csv(
        results_dir / "excluded_series_mismatch.csv", index=False, float_format="%.6f"
    )
    ranking = rank(eligible, "mape")
    ranking.to_csv(results_dir / "ranking_overall.csv", index=False, float_format="%.6f")

    # Events
    events = load_events()
    ev_days = tag_events(daily, events)
    ev_table = aggregate(ev_days, ["event_id", "event_name", "ba", "region"]) if len(ev_days) else ev_days
    ev_table.to_csv(results_dir / "events_by_ba.csv", index=False, float_format="%.6f")

    # Recent window
    last_date = max(daily["date"])
    cutoff = pd.Timestamp(last_date) - pd.Timedelta(days=recent_days - 1)
    recent = daily[pd.to_datetime(daily["date"]) >= cutoff]
    recent_table = rank(aggregate(recent, ["ba", "region"]).query("days >= 10 and mean_demand_mw >= 500"), "mape")
    recent_table.to_csv(results_dir / "ranking_recent.csv", index=False, float_format="%.6f")

    # Headline summary for the site and the README
    scored = daily[daily["scored"]]
    scored_elig = scored[scored["ba"].isin(eligible["ba"])]
    w = scored_elig["mean_demand_mw"] * scored_elig["hours_valid"]
    demand_weighted_mape = float((scored_elig["mape"] * w).sum() / w.sum()) if len(scored_elig) else None
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "package_version": __version__,
        "source": "EIA-930 six-month balance files, https://www.eia.gov/electricity/gridmonitor/",
        "first_date": str(min(daily["date"])),
        "last_date": str(last_date),
        "balancing_authorities_total": int(daily["ba"].nunique()),
        "balancing_authorities_scored": int(scored["ba"].nunique()),
        "ba_days_scored": len(scored),
        "hours_scored": int(scored["hours_valid"].sum()),
        "eligible_balancing_authorities": len(eligible),
        "eligibility_rule": "at least 180 scored days, mean demand >= 500 MW, and |median daily bias| <= 25%",
        "excluded_for_series_mismatch": mismatch[["ba", "region", "median_daily_bias_pct"]].round(4).to_dict(orient="records"),
        "demand_weighted_mape_eligible": demand_weighted_mape,
        "median_ba_mape_eligible": float(eligible["mape"].median()) if len(eligible) else None,
        "share_of_ba_days_under_forecast_at_peak_eligible": float((scored_elig["peak_hour_pct_error"] < 0).mean()),
        "p99_under_forecast_at_peak_eligible": float(scored_elig["peak_hour_pct_error"].quantile(0.01)) if len(scored_elig) else None,
        "worst_single_day_under_forecast_at_peak_eligible": _row_to_dict(
            scored_elig.loc[scored_elig["peak_hour_pct_error"].idxmin(), ["ba", "date", "peak_hour_pct_error", "peak_demand_mw"]]
        ),
        "share_of_scored_hours_imputed": float(scored["imputed_hours"].sum() / scored["hours_valid"].sum()),
        "hours_flagged_implausible": int(daily["hours_implausible"].sum()),
        "implausible_rule": "forecast/demand outside [1/2, 2], or forecast <= 0; excluded from error metrics",
        "recent_window_days": recent_days,
        "ranking_overall_top5": ranking.head(5)[["rank", "ba", "region", "mape", "days"]].to_dict(orient="records"),
        "ranking_overall_bottom5": ranking.tail(5)[["rank", "ba", "region", "mape", "days"]].to_dict(orient="records"),
    }
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    log.info("wrote results to %s", results_dir)
    return summary


def _row_to_dict(row: pd.Series) -> dict:
    return {k: (str(v) if isinstance(v, date) else (float(v) if hasattr(v, "__float__") and not isinstance(v, str) else v)) for k, v in row.items()}
