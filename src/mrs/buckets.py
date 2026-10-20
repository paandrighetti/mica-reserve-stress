"""Liquidity buckets of a reserve snapshot (draft RTS EBA/RTS/2024/10, article 1), under two readings of fund units.

- look-through: assets held in the Circle Reserve Fund are classified by their own maturity;
- strict: on our reading of the EBA's draft RTS on highly liquid financial instruments, units of a US government
  money market fund are not eligible reserve assets (neither level 1 assets nor units of a UCITS), so they count
  in no bucket.
"""

from __future__ import annotations

from datetime import date

import holidays
import numpy as np

CALENDARS = {"USD": lambda years: holidays.US(years=years), "EUR": lambda years: holidays.financial_holidays("XECB", years=years)}


def working_days_between(start: date, end: date, currency: str) -> int:
    """Working days in (start, end]: weekdays that are not holidays of the currency's calendar."""
    if end <= start:
        return 0
    closed = sorted(CALENDARS[currency](range(start.year, end.year + 1)))
    one = np.timedelta64(1, "D")
    return int(np.busday_count(np.datetime64(start, "D") + one, np.datetime64(end, "D") + one, holidays=closed))


def bucket_of(kind: str, maturity: date | None, report_date: date, currency: str) -> int | None:
    """1 or 5 (working days to liquidity), 0 for longer, None for timing adjustments."""
    if kind == "timing":
        return None
    if kind in ("bank_cash", "repo", "fund_cash"):
        return 1  # sight deposits (assumed: notice periods are not disclosed), overnight repos, fund cash
    days = working_days_between(report_date, maturity, currency)
    return 1 if days <= 1 else 5 if days <= 5 else 0


def shares(rows: list[dict], reserve: float, currency: str) -> dict:
    """Shares of the reserve per bucket and reading, deposits, fund units and Treasury bills."""
    out = {"deposit_share": 0.0, "fund_share": 0.0, "sovereign_share": 0.0, "sovereign_share_direct": 0.0}
    for reading in ("look_through", "strict"):
        out[f"daily_share_{reading}"] = out[f"weekly_share_{reading}"] = 0.0
    for r in rows:
        w = r["amount"] / reserve
        if r["pool"] == "fund":
            out["fund_share"] += w
        if r["kind"] == "bank_cash":
            out["deposit_share"] += w
        if r["kind"] == "tbill":
            out["sovereign_share"] += w
            out["sovereign_share_direct"] += w if r["pool"] == "direct" else 0.0
        b = bucket_of(r["kind"], r.get("maturity"), r["report_date"], currency)
        if b is None or b == 0:
            continue
        for reading in ("look_through", "strict"):
            if reading == "strict" and r["pool"] == "fund":
                continue
            out[f"weekly_share_{reading}"] += w
            if b == 1:
                out[f"daily_share_{reading}"] += w
    return out
