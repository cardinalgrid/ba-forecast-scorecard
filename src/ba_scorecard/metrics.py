"""Forecast-error metrics for BA day-ahead demand forecasts.

Conventions
-----------
* error = forecast - demand (MW). Positive = over-forecast, negative = under-forecast.
* Percent errors are relative to actual demand. Hours with demand <= 0, forecast <= 0, missing
  demand or missing forecast are excluded and counted in ``hours_excluded``.
* Hours where forecast/demand falls outside [1/IMPLAUSIBLE_RATIO, IMPLAUSIBLE_RATIO] are treated as
  data-quality failures (a zero, a unit error, a stale value), not as forecast error: they are
  excluded from the error metrics and counted in ``hours_implausible``. The threshold is
  deliberately loose so that genuine extreme-weather misses (tens of percent) are kept.
* ``peak_hour_pct_error``: forecast error at the hour of the *actual* daily peak, as a share of
  that peak. This is the number that matters for reserve adequacy.
* ``peak_mw_pct_error``: (max forecast - max demand) / max demand for the day, regardless of hour.
* ``imputed_share``: share of scored hours where EIA imputed the demand value.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MIN_HOURS_PER_DAY = 20  # a BA-day with fewer valid hours is not scored
IMPLAUSIBLE_RATIO = 3.0  # forecast/demand outside [1/3, 3] is a data problem, not a forecast miss


def _valid(df: pd.DataFrame) -> pd.Series:
    return df["demand"].gt(0) & df["forecast"].gt(0)


def _implausible(df: pd.DataFrame) -> pd.Series:
    ratio = df["forecast"] / df["demand"]
    return _valid(df) & ((ratio > IMPLAUSIBLE_RATIO) | (ratio < 1 / IMPLAUSIBLE_RATIO))


def daily_scores(df: pd.DataFrame, min_hours: int = MIN_HOURS_PER_DAY) -> pd.DataFrame:
    """Score each (ba, date). Input is the tidy hourly table."""
    d = df.copy()
    d["implausible"] = _implausible(d)
    d["valid"] = _valid(d) & ~d["implausible"]
    d["err"] = np.where(d["valid"], d["forecast"] - d["demand"], np.nan)
    d["abs_pct"] = np.where(d["valid"], np.abs(d["err"]) / d["demand"], np.nan)
    d["pct"] = np.where(d["valid"], d["err"] / d["demand"], np.nan)
    d["sq"] = d["err"] ** 2
    d["imp_valid"] = d["valid"] & d["demand_imputed"].astype(bool)

    g = d.groupby(["ba", "date"], sort=True)
    out = g.agg(
        region=("region", "first"),
        hours_total=("valid", "size"),
        hours_valid=("valid", "sum"),
        mape=("abs_pct", "mean"),
        bias_pct=("pct", "mean"),
        bias_mw=("err", "mean"),
        rmse_mw=("sq", "mean"),
        mean_demand_mw=("demand", "mean"),
        peak_demand_mw=("demand", "max"),
        peak_forecast_mw=("forecast", "max"),
        imputed_hours=("imp_valid", "sum"),
        hours_implausible=("implausible", "sum"),
    ).reset_index()
    out["rmse_mw"] = np.sqrt(out["rmse_mw"])
    out["hours_excluded"] = out["hours_total"] - out["hours_valid"] - out["hours_implausible"]
    out["imputed_share"] = out["imputed_hours"] / out["hours_valid"].replace(0, np.nan)
    out["peak_mw_pct_error"] = (out["peak_forecast_mw"] - out["peak_demand_mw"]) / out["peak_demand_mw"]

    # Error at the hour of the actual peak.
    valid_rows = d[d["valid"]]
    idx = valid_rows.groupby(["ba", "date"])["demand"].idxmax()
    peak_rows = valid_rows.loc[idx, ["ba", "date", "hour", "pct"]].rename(
        columns={"hour": "peak_hour", "pct": "peak_hour_pct_error"}
    )
    out = out.merge(peak_rows, on=["ba", "date"], how="left")

    out["scored"] = out["hours_valid"] >= min_hours
    out.loc[~out["scored"], ["mape", "bias_pct", "bias_mw", "rmse_mw", "peak_hour_pct_error", "peak_mw_pct_error"]] = np.nan
    return out


def aggregate(daily: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Aggregate scored BA-days. MAPE/bias are hour-weighted means of daily values."""
    s = daily[daily["scored"]].copy()
    s["w"] = s["hours_valid"]
    for c in ("mape", "bias_pct"):
        s[f"{c}_w"] = s[c] * s["w"]
    s["sq_w"] = s["rmse_mw"] ** 2 * s["w"]
    s["under_day"] = s["peak_hour_pct_error"] < 0

    g = s.groupby(by, sort=True)
    out = g.agg(
        days=("date", "nunique"),
        hours=("w", "sum"),
        mape_w=("mape_w", "sum"),
        bias_pct_w=("bias_pct_w", "sum"),
        sq_w=("sq_w", "sum"),
        peak_hour_pct_error_mean=("peak_hour_pct_error", "mean"),
        peak_hour_abs_pct_error_mean=("peak_hour_pct_error", lambda x: np.abs(x).mean()),
        worst_under_forecast_pct=("peak_hour_pct_error", "min"),
        under_forecast_day_share=("under_day", "mean"),
        mean_demand_mw=("mean_demand_mw", "mean"),
        imputed_share=("imputed_share", "mean"),
        hours_implausible=("hours_implausible", "sum"),
    ).reset_index()
    out["mape"] = out["mape_w"] / out["hours"]
    out["bias_pct"] = out["bias_pct_w"] / out["hours"]
    out["rmse_mw"] = np.sqrt(out["sq_w"] / out["hours"])
    return out.drop(columns=["mape_w", "bias_pct_w", "sq_w"])


def rank(table: pd.DataFrame, metric: str = "mape", ascending: bool = True) -> pd.DataFrame:
    t = table.dropna(subset=[metric]).sort_values(metric, ascending=ascending).reset_index(drop=True)
    t.insert(0, "rank", np.arange(1, len(t) + 1))
    return t
