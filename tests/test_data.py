from datetime import date
from pathlib import Path

from ba_scorecard.data import Period, periods_between, tidy
from ba_scorecard.events import load_events

FIXTURE = Path(__file__).parent / "fixtures" / "eia930_sample.csv"


def test_period_parsing_and_iteration():
    assert str(Period.parse("2024h1")) == "2024H1"
    assert Period.containing(date(2026, 9, 8)) == Period(2026, 2)
    assert [str(p) for p in periods_between("2024H2", "2025H2")] == ["2024H2", "2025H1", "2025H2"]
    assert Period(2024, 1).url.endswith("EIA930_BALANCE_2024_Jan_Jun.csv")


def test_tidy_parses_real_header_and_imputed_flag():
    df = tidy(FIXTURE)
    assert list(df.columns) == [
        "ba", "region", "date", "hour", "local_end", "utc_end", "forecast", "demand", "demand_adjusted", "demand_imputed",
    ]
    assert df["ba"].iloc[0] == "AECI"
    assert df["region"].iloc[0] == "MIDW"
    assert df["forecast"].iloc[0] == 2706
    assert df["demand"].iloc[0] == 2625
    assert df["utc_end"].dt.tz is not None
    assert df["demand_imputed"].dtype == bool
    assert not df["demand_imputed"].iloc[0]


def test_events_have_sources():
    ev = load_events()
    assert len(ev) >= 4
    assert ev["source_url"].str.startswith("http").all()
    assert (ev["end_date"] >= ev["start_date"]).all()
