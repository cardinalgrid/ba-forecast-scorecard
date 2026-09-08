"""Command-line interface.

Examples
--------
ba-scorecard download --from 2024H1 --to 2026H1
ba-scorecard score --from 2024H1 --to 2026H1
ba-scorecard update            # refresh the current half-year and rebuild results
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path

from .data import Period, build_tidy, load_tidy, periods_between
from .scorecard import build


def _dirs(root: Path) -> tuple[Path, Path, Path]:
    return root / "data" / "raw", root / "data" / "tidy", root / "results"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ba-scorecard", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path("."), help="project root holding data/ and results/")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_dl = sub.add_parser("download", help="download and tidy EIA-930 six-month files")
    p_dl.add_argument("--from", dest="start", default="2015H2")
    p_dl.add_argument("--to", dest="end", default=str(Period.containing(date.today())))
    p_dl.add_argument("--force", action="store_true")

    p_sc = sub.add_parser("score", help="build scorecard tables from tidy data")
    p_sc.add_argument("--from", dest="start", default=None)
    p_sc.add_argument("--to", dest="end", default=None)
    p_sc.add_argument("--recent-days", type=int, default=30)

    p_up = sub.add_parser("update", help="re-download the current half-year and rebuild results")
    p_up.add_argument("--recent-days", type=int, default=30)

    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if a.verbose else logging.WARNING, format="%(levelname)s %(message)s")
    raw, tidy_dir, results = _dirs(a.root)

    if a.cmd == "download":
        build_tidy(periods_between(a.start, a.end), raw, tidy_dir, force=a.force)
        return 0

    if a.cmd == "update":
        current = Period.containing(date.today())
        build_tidy([current], raw, tidy_dir, force=True)
        df = load_tidy(tidy_dir)
        summary = build(df, results, recent_days=a.recent_days)
        print(json.dumps(summary, indent=2, default=str))
        return 0

    if a.cmd == "score":
        periods = periods_between(a.start, a.end) if a.start and a.end else None
        df = load_tidy(tidy_dir, periods)
        summary = build(df, results, recent_days=a.recent_days)
        print(json.dumps(summary, indent=2, default=str))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
