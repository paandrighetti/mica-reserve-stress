"""Daily supply from DefiLlama, net outflows over 1, 7 and 30 days, and the reference episodes (METHOD.md)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

MIN_UNITS = 1e6
MIN_SHARE_OF_LATEST = 0.10
SKIP_FIRST_DAYS = 90
MIN_SHARE_DAYS_CHANGED = 0.5
DATA_CHANGE_MIN_MOVE = 0.02  # moves smaller than 2% of supply are never treated as data changes
DATA_CHANGE_OFFSET = 0.8
HORIZONS = (1, 7, 30)
EPISODES = {  # token, first day, last day
    "USDC, Silicon Valley Bank, March 2023": ("USDC", "2023-03-08", "2023-03-31"),
    "BUSD, stop of minting, February to April 2023": ("BUSD", "2023-02-10", "2023-04-15"),
    "USDT, Terra collapse, May 2022": ("USDT", "2022-05-07", "2022-05-31"),
    "TUSD, January 2024": ("TUSD", "2024-01-10", "2024-01-31"),
}


def supply(path: Path) -> pd.DataFrame:
    """Daily circulating supply and issuer-held unreleased tokens, in the token's own unit."""
    rows = json.loads(path.read_text())
    df = pd.DataFrame([{"date": pd.Timestamp(int(r["date"]), unit="s"),
                        "circulating": next(iter(r["totalCirculating"].values())),
                        "unreleased": next(iter((r.get("totalUnreleased") or {"x": np.nan}).values()))}
                       for r in rows if r.get("totalCirculating")])
    df = df.drop_duplicates("date").set_index("date").sort_index()
    return df.asfreq("D")


def data_changes(df: pd.DataFrame) -> set[pd.Timestamp]:
    """Days whose move in circulating supply is a change in the data rather than issuance or redemption.

    A move of at least 2% of supply is flagged if moves in the other direction within two days on either side
    offset at least 80% of it: a spike that undoes itself, as when a chain's pre-minted tokens are counted as
    circulating for a day or two. Moves of issuer-held tokens are not used: a redeemed USDT returns to Tether's
    treasury before it is burned, so a fall in circulating supply with a rise in unreleased tokens is a real
    redemption there.
    """
    c = df.circulating
    dc = c.diff()
    flagged = set()
    for day, move in dc.items():
        prev = c.shift(1).get(day)
        if pd.isna(move) or not prev or abs(move) < DATA_CHANGE_MIN_MOVE * prev:
            continue
        near = dc.loc[day - pd.Timedelta(days=2): day + pd.Timedelta(days=2)].drop(day)
        offset = -near[np.sign(near) == -np.sign(move)].sum() * np.sign(move)
        if offset >= DATA_CHANGE_OFFSET * abs(move):
            flagged.add(day)
    return flagged


def own_history(s: pd.Series) -> pd.Series:
    """Days that measure a token of its present size: supply at least 10% of the latest and one million units,
    after the first 90 days of the series. Other days are set to NaN."""
    floor = max(MIN_UNITS, MIN_SHARE_OF_LATEST * s.dropna().iloc[-1])
    kept = s.where(s >= floor)
    kept.iloc[:SKIP_FIRST_DAYS] = np.nan
    return kept


def outflows(s: pd.Series, h: int, flagged: set[pd.Timestamp] = frozenset()) -> pd.Series:
    """Net outflow over h days as a share of the supply h days before (positive = outflow); windows that contain
    a flagged day are left out."""
    o = (s.shift(h) - s) / s.shift(h)
    if flagged:
        bad = pd.Series(0.0, index=s.index)
        bad.loc[bad.index.intersection(sorted(flagged))] = 1.0
        o[bad.rolling(h, min_periods=1).max() > 0] = np.nan
    return o


def informative(s: pd.Series) -> tuple[bool, float]:
    """Whether the series changes on at least half of its days, and that share."""
    d = s.dropna().diff().dropna()
    share = float((d != 0).mean()) if len(d) else 0.0
    return share >= MIN_SHARE_DAYS_CHANGED, share


def worst(df: pd.DataFrame, h: int) -> tuple[float, pd.Timestamp | None]:
    """Largest net outflow over h days in the token's own history, data changes left out."""
    o = outflows(own_history(df.circulating), h, data_changes(df)).dropna()
    return (float(o.max()), o.idxmax()) if len(o) else (float("nan"), None)


def episode(df: pd.DataFrame, first: str, last: str, h: int) -> tuple[float, pd.Timestamp | None]:
    o = outflows(df.circulating.where(df.circulating >= MIN_UNITS), h, data_changes(df)).loc[first:last].dropna()
    return (float(o.max()), o.idxmax()) if len(o) else (float("nan"), None)
