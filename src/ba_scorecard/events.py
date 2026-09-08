"""Named grid events used to slice the scorecard.

The calendar lives in ``data/events.csv`` with a public source for every row. Regions use
EIA-930 region codes (CAL, CAR, CENT, FLA, MIDA, MIDW, NE, NW, NY, SE, SW, TEN, TEX).
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import pandas as pd


def load_events(path: Path | None = None) -> pd.DataFrame:
    if path is None:
        with resources.as_file(resources.files("ba_scorecard") / "data" / "events.csv") as p:
            ev = pd.read_csv(p)
    else:
        ev = pd.read_csv(path)
    ev["start_date"] = pd.to_datetime(ev["start_date"]).dt.date
    ev["end_date"] = pd.to_datetime(ev["end_date"]).dt.date
    ev["regions"] = ev["regions"].fillna("").apply(lambda s: [r for r in s.split(",") if r])
    return ev


def tag_events(daily: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Return BA-day rows that fall inside an event window (and region, if the event lists regions)."""
    parts = []
    for _, e in events.iterrows():
        m = (daily["date"] >= e["start_date"]) & (daily["date"] <= e["end_date"])
        if e["regions"]:
            m &= daily["region"].isin(e["regions"])
        sub = daily[m].copy()
        sub["event_id"] = e["event_id"]
        sub["event_name"] = e["name"]
        parts.append(sub)
    if not parts:
        return daily.iloc[0:0].assign(event_id=pd.Series(dtype=str), event_name=pd.Series(dtype=str))
    return pd.concat(parts, ignore_index=True)
