"""Download and tidy EIA-930 balance data.

Source: EIA Hourly Electric Grid Monitor, six-month bulk files
https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_<YEAR>_<Jan_Jun|Jul_Dec>.csv

No API key is required. Files are cached under ``data/raw`` and tidied into one parquet
file per half-year under ``data/tidy``. Column names below are those published by EIA.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

log = logging.getLogger(__name__)

BASE_URL = "https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_{year}_{half}.csv"
HALVES = ("Jan_Jun", "Jul_Dec")
FIRST_PERIOD = "2015H2"  # EIA-930 starts July 2015

# EIA column names -> tidy names
COLUMNS = {
    "Balancing Authority": "ba",
    "Data Date": "date",
    "Hour Number": "hour",
    "Local Time at End of Hour": "local_end",
    "UTC Time at End of Hour": "utc_end",
    "Demand Forecast (MW)": "forecast",
    "Demand (MW)": "demand",
    "Demand (MW) (Imputed)": "demand_imputed",
    "Demand (MW) (Adjusted)": "demand_adjusted",
    "Region": "region",
}


@dataclass(frozen=True)
class Period:
    """A half-year period such as 2024H1."""

    year: int
    half: int  # 1 or 2

    @classmethod
    def parse(cls, text: str) -> "Period":
        text = text.strip().upper()
        if len(text) != 6 or text[4] != "H" or text[5] not in "12":
            raise ValueError(f"Bad period {text!r}; expected like 2024H1")
        return cls(int(text[:4]), int(text[5]))

    @classmethod
    def containing(cls, d: date) -> "Period":
        return cls(d.year, 1 if d.month <= 6 else 2)

    def __str__(self) -> str:
        return f"{self.year}H{self.half}"

    @property
    def url(self) -> str:
        return BASE_URL.format(year=self.year, half=HALVES[self.half - 1])

    def next(self) -> "Period":
        return Period(self.year + 1, 1) if self.half == 2 else Period(self.year, 2)

    def __le__(self, other: "Period") -> bool:
        return (self.year, self.half) <= (other.year, other.half)


def periods_between(start: str | Period, end: str | Period) -> list[Period]:
    a = Period.parse(start) if isinstance(start, str) else start
    b = Period.parse(end) if isinstance(end, str) else end
    out: list[Period] = []
    p = a
    while p <= b:
        out.append(p)
        p = p.next()
    return out


def download(period: Period, raw_dir: Path, force: bool = False, timeout: int = 300) -> Path:
    """Download one six-month CSV to ``raw_dir``; skip if present unless ``force``."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / f"EIA930_BALANCE_{period}.csv"
    if dest.exists() and not force:
        log.info("cached %s", dest.name)
        return dest
    log.info("downloading %s", period.url)
    with requests.get(period.url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        tmp.replace(dest)
    return dest


def _to_number(s: pd.Series) -> pd.Series:
    # EIA writes thousands separators in some files; strip them before parsing.
    if s.dtype == object:
        s = s.str.replace(",", "", regex=False)
    return pd.to_numeric(s, errors="coerce")


def tidy(csv_path: Path) -> pd.DataFrame:
    """Read one raw EIA-930 CSV and return a tidy hourly table.

    Columns: ba, region, date, hour, local_end, utc_end, forecast, demand, demand_adjusted,
    demand_imputed (bool: EIA imputed the demand value).
    """
    header = pd.read_csv(csv_path, nrows=0).columns
    wanted = [c for c in COLUMNS if c in header]
    df = pd.read_csv(csv_path, usecols=wanted, dtype=str, low_memory=False)
    df = df.rename(columns={c: COLUMNS[c] for c in wanted})

    for col in ("forecast", "demand", "demand_adjusted", "demand_imputed"):
        if col in df:
            df[col] = _to_number(df[col])
    # The imputed column holds the imputed value where EIA imputed, else blank.
    df["demand_imputed"] = df["demand_imputed"].notna() if "demand_imputed" in df else False

    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y").dt.date
    df["hour"] = pd.to_numeric(df["hour"], errors="coerce").astype("Int64")
    df["utc_end"] = pd.to_datetime(df["utc_end"], format="%m/%d/%Y %I:%M:%S %p", errors="coerce", utc=True)
    df["local_end"] = pd.to_datetime(df["local_end"], format="%m/%d/%Y %I:%M:%S %p", errors="coerce")
    if "region" not in df:
        df["region"] = pd.NA
    if "demand_adjusted" not in df:
        df["demand_adjusted"] = pd.NA

    cols = ["ba", "region", "date", "hour", "local_end", "utc_end", "forecast", "demand", "demand_adjusted", "demand_imputed"]
    return df[cols].sort_values(["ba", "utc_end"]).reset_index(drop=True)


def build_tidy(periods: Iterable[Period], raw_dir: Path, tidy_dir: Path, force: bool = False) -> list[Path]:
    """Download (if needed) and tidy each period into ``tidy_dir/<period>.parquet``."""
    tidy_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for p in periods:
        dest = tidy_dir / f"{p}.parquet"
        if dest.exists() and not force:
            out.append(dest)
            continue
        raw = download(p, raw_dir, force=force)
        tidy(raw).to_parquet(dest, index=False)
        out.append(dest)
        log.info("tidied %s", dest.name)
    return out


def load_tidy(tidy_dir: Path, periods: Iterable[Period] | None = None) -> pd.DataFrame:
    files = sorted(tidy_dir.glob("*.parquet")) if periods is None else [tidy_dir / f"{p}.parquet" for p in periods]
    frames = [pd.read_parquet(f) for f in files if f.exists()]
    if not frames:
        raise FileNotFoundError(f"No tidy files in {tidy_dir}")
    return pd.concat(frames, ignore_index=True)
