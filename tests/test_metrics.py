import numpy as np
import pandas as pd

from ba_scorecard.metrics import aggregate, daily_scores, rank


def _day(ba="TEST", region="TEX", day="2024-01-15", demand=None, forecast=None, imputed=None):
    hours = np.arange(1, 25)
    demand = np.full(24, 1000.0) if demand is None else np.asarray(demand, dtype=float)
    forecast = demand.copy() if forecast is None else np.asarray(forecast, dtype=float)
    imputed = np.zeros(24, dtype=bool) if imputed is None else np.asarray(imputed, dtype=bool)
    d = pd.to_datetime(day).date()
    return pd.DataFrame(
        {
            "ba": ba,
            "region": region,
            "date": d,
            "hour": hours,
            "local_end": pd.date_range(day, periods=24, freq="h"),
            "utc_end": pd.date_range(day, periods=24, freq="h", tz="UTC"),
            "forecast": forecast,
            "demand": demand,
            "demand_adjusted": demand,
            "demand_imputed": imputed,
        }
    )


def test_perfect_forecast_has_zero_error():
    out = daily_scores(_day())
    row = out.iloc[0]
    assert row["scored"]
    assert row["mape"] == 0
    assert row["bias_mw"] == 0
    assert row["rmse_mw"] == 0
    assert row["peak_hour_pct_error"] == 0


def test_under_forecast_sign_and_magnitude():
    demand = np.full(24, 1000.0)
    demand[17] = 2000.0  # actual peak at hour 18
    forecast = np.full(24, 1000.0)
    forecast[17] = 1768.0  # 11.6% under at the peak hour
    out = daily_scores(_day(demand=demand, forecast=forecast))
    row = out.iloc[0]
    assert row["peak_hour"] == 18
    assert np.isclose(row["peak_hour_pct_error"], -0.116)
    assert row["bias_mw"] < 0
    assert np.isclose(row["mape"], 0.116 / 24)


def test_excludes_invalid_hours_and_flags_low_coverage():
    demand = np.full(24, 1000.0)
    demand[:10] = np.nan  # 14 valid hours only
    out = daily_scores(_day(demand=demand))
    row = out.iloc[0]
    assert row["hours_valid"] == 14
    assert row["hours_excluded"] == 10
    assert not row["scored"]
    assert np.isnan(row["mape"])


def test_imputed_share_counts_only_valid_hours():
    imputed = np.zeros(24, dtype=bool)
    imputed[:6] = True
    out = daily_scores(_day(imputed=imputed))
    assert np.isclose(out.iloc[0]["imputed_share"], 0.25)


def test_aggregate_is_hour_weighted_and_rank_orders_ascending():
    a = _day(ba="A", forecast=np.full(24, 1100.0))  # 10% over
    b = _day(ba="B", forecast=np.full(24, 1020.0))  # 2% over
    daily = daily_scores(pd.concat([a, b], ignore_index=True))
    agg = aggregate(daily, ["ba", "region"])
    assert np.isclose(agg.set_index("ba").loc["A", "mape"], 0.10)
    assert np.isclose(agg.set_index("ba").loc["B", "bias_pct"], 0.02)
    r = rank(agg, "mape")
    assert list(r["ba"]) == ["B", "A"]
    assert list(r["rank"]) == [1, 2]


def test_zero_or_negative_forecast_is_excluded_not_scored_as_error():
    forecast = np.full(24, 1000.0)
    forecast[5] = 0.0
    forecast[6] = -12.0
    out = daily_scores(_day(forecast=forecast))
    row = out.iloc[0]
    assert row["hours_valid"] == 22
    assert row["hours_excluded"] == 2
    assert row["mape"] == 0


def test_implausible_ratio_is_flagged_and_excluded_but_large_miss_is_kept():
    forecast = np.full(24, 1000.0)
    forecast[3] = 5000.0  # 5x: unit error -> implausible
    forecast[10] = 600.0  # 40% under: a real miss, kept
    out = daily_scores(_day(forecast=forecast))
    row = out.iloc[0]
    assert row["hours_implausible"] == 1
    assert row["hours_valid"] == 23
    assert np.isclose(row["mape"], 0.4 / 23)
