"""Every output of the study, from the files in sources/. Usage: python scripts/build.py --sources sources --out outputs"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrs import buckets, circle, flows, pages, rules

# USDC: classified significant by the EBA on 14 October 2026, EBA supervision from 12 November 2026. Its
# snapshot is tested against both regimes.
REGIMES = {"USDC": (("not significant, until 11 November 2026", False), ("significant, from 12 November 2026", True))}
NOT_SIGNIFICANT = (("not significant", False),)
CURRENCY = {"USDC": "USD", "EURC": "EUR", "EURCV": "EUR", "USDCV": "USD", "EURQ": "EUR", "USDQ": "USD"}
SERIES = {"USDC": 2, "EURC": 50, "EURCV": 254, "USDCV": 307, "EURQ": 274, "USDQ": 275, "USDT": 1, "BUSD": 4,
          "TUSD": 7}
SCOPE = {"USDC": "global reserve; MiCA binds the EU issuer's reserve, not published separately"}
# 13 March 2023: 2.9 bn USDC redeemed and 0.7 bn issued (Reuters, 14 March 2023): gross over net outflow.
GROSS_OVER_NET = 2.9 / (2.9 - 0.7)


def holdings_and_snapshots(src: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    holdings, snaps = [], []
    for pdf in sorted(src.glob("circle_*.pdf")):
        h, s = circle.parse(pdf)
        holdings += [asdict(x) for x in h]
        snaps += s
    hold = pd.DataFrame(holdings)
    rows = []
    for s in snaps:
        mine = hold[(hold.token == s["token"]) & (hold.report_date == s["report_date"])].to_dict("records")
        rows.append({**s, **buckets.shares(mine, s["reserve"], CURRENCY[s["token"]]), "largest_bank_share": None})
    for p in pages.sgforge((src / "sgforge_coinvertible.html").read_text(errors="replace")) + \
            pages.quantoz((src / "quantoz_transparency.html").read_text(errors="replace")):
        cash = p["composition"].get("bank_cash", 0.0)
        row = {"token": p["token"], "report_date": p["report_date"], "circulation": p["circulation"],
               "reserve": p["circulation"] * p.get("reserve_ratio", 1.0), "source": p["source"],
               "deposit_share": cash, "fund_share": 0.0,
               # Quantoz does not give the split of its government bonds by issuer (METHOD.md)
               "sovereign_share": float("nan") if p["composition"].get("government_bonds") else 0.0,
               "sovereign_share_direct": float("nan") if p["composition"].get("government_bonds") else 0.0,
               "largest_bank_share": max(p["bank_shares"].values()) if p["bank_shares"] else None}
        for reading in ("look_through", "strict"):  # no fund units; bonds have no disclosed maturity
            row[f"daily_share_{reading}"] = row[f"weekly_share_{reading}"] = cash
        rows.append(row)
    snap = pd.DataFrame(rows).sort_values(["token", "report_date"]).reset_index(drop=True)
    snap["backing"] = snap.reserve / snap.circulation
    return hold, snap


def compliance(snap: pd.DataFrame) -> pd.DataFrame:
    latest = snap.sort_values("report_date").groupby("token").tail(1)
    out = []
    for _, s in latest.iterrows():
        for regime, significant in REGIMES.get(s.token, NOT_SIGNIFICANT):
            for r in rules.RULES:
                if not rules.applicable(r, significant):
                    continue
                fund = s.fund_share > 0
                readings = ("look_through", "strict") if fund and r.metric in ("daily_share", "weekly_share") else ("",)
                for reading in readings:
                    metric = None if r.metric is None else (
                        f"{r.metric}_{reading or 'look_through'}" if r.metric in ("daily_share", "weekly_share") else r.metric)
                    value = float("nan") if metric is None else s[metric]
                    note = ""
                    if r.metric == "fund_share" and fund:
                        note = "applied as if the fund's units were eligible, the reading most favourable to the issuer"
                    if r.metric == "sovereign_share" and fund:
                        note = "Treasury bills held through the fund included"
                    if r.metric == "largest_bank_share":
                        note = "tested at 25%, the cap for a systemically important bank; 15% or 5% apply otherwise"
                    result = ("not testable from the disclosures" if metric is None else
                              "not disclosed" if pd.isna(value) else "meets" if r.passes(value) else "misses")
                    out.append({"token": s.token, "report_date": s.report_date, "regime": regime,
                                "scope": SCOPE.get(s.token, "issuer's reserve"), "rule": r.rule, "reading": reading,
                                "value": value, "op": r.op, "threshold": r.threshold, "status": r.status,
                                "applies_to": r.applies_to, "source": r.source, "result": result, "note": note})
    return pd.DataFrame(out)


def flow_tables(src: Path, snap: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    series = {t: flows.supply(next(src.glob(f"defillama_chart_{t}_{i}.json"))) for t, i in SERIES.items()}
    changes = []
    stats = []
    for t in ("USDC", "EURC", "EURCV", "USDCV", "EURQ", "USDQ"):
        df = series[t]
        s = df.circulating
        flagged = flows.data_changes(df)
        changes += [{"token": t, "date": d.date(), "move": float(s.diff()[d]), "supply_before": float(s.shift(1)[d])}
                    for d in sorted(flagged)]
        row = {"token": t, "first_day": s.dropna().index.min().date(), "last_day": s.dropna().index.max().date(),
               "data_changes": len(flagged)}
        for h in flows.HORIZONS:
            v, d = flows.worst(df, h)
            row[f"worst_{h}d"], row[f"worst_{h}d_date"] = v, d.date() if d is not None else None
        o1 = flows.outflows(flows.own_history(s), 1, flagged).dropna()
        row["days"] = len(o1)
        row["p99_1d"] = float(o1.quantile(0.99)) if len(o1) else float("nan")
        row["informative"], row["share_days_changed"] = flows.informative(s)
        stats.append(row)
    episodes = []
    for name, (t, first, last) in flows.EPISODES.items():
        for h in flows.HORIZONS:
            v, d = flows.episode(series[t], first, last, h)
            episodes.append({"episode": name, "token": t, "horizon_days": h, "outflow": v,
                             "date": d.date() if d is not None else None})
    episodes = pd.DataFrame(episodes)
    # DefiLlama against the attested circulation at Circle's report dates
    cross = []
    for _, s in snap[snap.source.str.startswith("circle_")].iterrows():
        dl = series[s.token].circulating.get(pd.Timestamp(s.report_date), float("nan"))
        cross.append({"token": s.token, "report_date": s.report_date, "attested": s.circulation, "defillama": dl,
                      "difference": dl / s.circulation - 1})
    params = {"gross_over_net": GROSS_OVER_NET, "min_units": flows.MIN_UNITS,
              "min_share_of_latest": flows.MIN_SHARE_OF_LATEST, "skip_first_days": flows.SKIP_FIRST_DAYS,
              "min_share_days_changed": flows.MIN_SHARE_DAYS_CHANGED}
    params["data_changes"] = changes
    return pd.DataFrame(stats), episodes, pd.DataFrame(cross), params


def stress(snap: pd.DataFrame, stats: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    """Coverage of stressed outflows by the one-day and five-day buckets, latest snapshot of each token."""
    latest = snap.sort_values("report_date").groupby("token").tail(1).set_index("token")
    st = stats.set_index("token")
    ep = episodes.groupby("horizon_days").outflow.max()  # episodes.csv leaves out one-day moves that span days
    out = []
    for token, s in latest.iterrows():
        for h, bucket in ((1, "daily"), (7, "weekly")):
            own = st.loc[token, f"worst_{h}d"] if token in st.index and st.loc[token, "informative"] else float("nan")
            for scenario, outflow in (("own worst", own), ("worst reference episode", ep[h]),
                                      ("worst reference episode, gross", ep[h] * GROSS_OVER_NET)):
                for reading in ("look_through", "strict"):
                    liquid = s[f"{bucket}_share_{reading}"] * s.reserve / s.circulation
                    row = {"token": token, "horizon_days": h, "scenario": scenario, "reading": reading,
                           "outflow": outflow, "liquid": liquid,
                           "coverage": liquid / outflow if outflow and outflow > 0 else float("nan")}
                    if h == 1:  # share of bank deposits that can be frozen before the one-day bucket falls short
                        dep = s.deposit_share * s.reserve / s.circulation
                        row["deposits_frozen_tolerated"] = min(1.0, max(0.0, (liquid - outflow) / dep)) if dep > 0 and not pd.isna(outflow) else float("nan")
                    out.append(row)
    return pd.DataFrame(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", type=Path, default=ROOT / "sources")
    ap.add_argument("--out", type=Path, default=ROOT / "outputs")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    hold, snap = holdings_and_snapshots(args.sources)
    hold.to_csv(args.out / "holdings.csv", index=False)
    snap.to_csv(args.out / "snapshots.csv", index=False)
    compliance(snap).to_csv(args.out / "compliance.csv", index=False)
    stats, episodes, cross, params = flow_tables(args.sources, snap)
    stats.to_csv(args.out / "outflows.csv", index=False)
    episodes.to_csv(args.out / "episodes.csv", index=False)
    cross.to_csv(args.out / "crosscheck.csv", index=False)
    stress(snap, stats, episodes).to_csv(args.out / "stress.csv", index=False)
    pd.DataFrame([asdict(r) for r in rules.RULES]).to_csv(args.out / "rules.csv", index=False)
    (args.out / "parameters.json").write_text(json.dumps(params, indent=1, default=str))
    print("outputs written to", args.out)


if __name__ == "__main__":
    main()
