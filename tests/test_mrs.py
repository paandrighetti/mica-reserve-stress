from datetime import date

import numpy as np
import pandas as pd
import pytest

from mrs import buckets, circle, flows, pages, rules

USDC_TEXT = """USDC Reserve Report
Report Dates August 11, 2026 August 31, 2026
USDC in Circulation 990 1,980
Fair Value of Assets Held in USDC Reserve $ 1,000 $ 2,000
CIRCLE RESERVE FUND ASSETS AS OF AUGUST 11, 2026
912797UU9 08/12/26 100
912797TX5 08/20/26 200
TOTAL U.S. TREASURY SECURITIES 300
U.S. Treasury Repurchase Agreements3
400
Cash held in Circle Reserve Fund 50
Cash due to/(owed by) Circle Reserve Fund due to timing and settlement differences, net4 (50)
TOTAL CIRCLE RESERVE FUND ASSETS 700
OTHER USDC RESERVE ASSETS AS OF AUGUST 11, 2026
290
Cash held at regulated financial institutions
Cash due to/(owed by) Circle due to timing and settlement differences, net4 10
TOTAL OTHER USDC RESERVE ASSETS 300
TOTAL USDC RESERVE ASSETS AS OF AUGUST 11, 2026 1,000
CIRCLE RESERVE FUND ASSETS AS OF AUGUST 31, 2026
TOTAL U.S. TREASURY SECURITIES 0
U.S. Treasury Repurchase Agreements3 1,500
Cash held in Circle Reserve Fund 0
Cash due to/(owed by) Circle Reserve Fund due to timing and settlement differences, net4 0
TOTAL CIRCLE RESERVE FUND ASSETS 1,500
OTHER USDC RESERVE ASSETS AS OF AUGUST 31, 2026
Cash held at regulated financial institutions 500
Cash due to/(owed by) Circle due to timing and settlement differences, net4 0
TOTAL OTHER USDC RESERVE ASSETS 500
TOTAL USDC RESERVE ASSETS AS OF AUGUST 31, 2026 2,000
"""


def test_circle_parse_and_totals():
    holdings, summary = circle.parse_text(USDC_TEXT, "test")
    assert [s["reserve"] for s in summary] == [1000, 2000] and summary[0]["circulation"] == 990
    first = [h for h in holdings if h.report_date == date(2026, 8, 11)]
    kinds = {(h.pool, h.kind): h.amount for h in first if h.kind != "tbill"}
    assert kinds == {("fund", "repo"): 400, ("fund", "fund_cash"): 50, ("fund", "timing"): -50,
                     ("direct", "bank_cash"): 290, ("direct", "timing"): 10}
    assert sorted(h.maturity for h in first if h.kind == "tbill") == [date(2026, 8, 12), date(2026, 8, 20)]
    with pytest.raises(circle.ParseError):
        circle.parse_text(USDC_TEXT.replace("Cash held in Circle Reserve Fund 50", "Cash held in Circle Reserve Fund 51"), "t")


def test_working_days_and_buckets():
    assert buckets.working_days_between(date(2026, 8, 28), date(2026, 8, 31), "USD") == 1  # Friday to Monday
    assert buckets.working_days_between(date(2026, 9, 4), date(2026, 9, 8), "USD") == 1  # over Labor Day
    assert buckets.working_days_between(date(2026, 9, 4), date(2026, 9, 8), "EUR") == 2
    d = date(2026, 8, 11)
    assert buckets.bucket_of("tbill", date(2026, 8, 12), d, "USD") == 1
    assert buckets.bucket_of("tbill", date(2026, 8, 18), d, "USD") == 5
    assert buckets.bucket_of("tbill", date(2026, 9, 18), d, "USD") == 0
    assert buckets.bucket_of("timing", None, d, "USD") is None
    holdings, _ = circle.parse_text(USDC_TEXT, "test")
    rows = [h.__dict__ for h in holdings if h.report_date == d]
    sh = buckets.shares(rows, 1000, "USD")
    assert sh["daily_share_look_through"] == pytest.approx((100 + 400 + 50 + 290) / 1000)
    assert sh["weekly_share_look_through"] == pytest.approx((100 + 400 + 50 + 290) / 1000)  # 08/20 is 7 working days
    assert sh["daily_share_strict"] == pytest.approx(290 / 1000)
    assert sh["fund_share"] == pytest.approx(0.7) and sh["deposit_share"] == pytest.approx(0.29)


def frame(values):
    idx = pd.date_range("2024-01-01", periods=len(values), freq="D")
    return pd.DataFrame({"circulating": values, "unreleased": np.nan}, index=idx)


def test_flows_data_changes_and_worst():
    base = [1e8] * 200
    spike = base.copy()
    spike[150], spike[151] = 1.5e8, 1e8  # in and out within two days: a data change
    run = base.copy()
    for k in range(160, 165):
        run[k] = run[k - 1] * 0.95  # five days of 5% outflows
    for k in range(165, 200):
        run[k] = run[164]
    assert flows.data_changes(frame(spike)) == {pd.Timestamp("2024-05-30"), pd.Timestamp("2024-05-31")}
    assert flows.data_changes(frame(run)) == set()
    w1, day = flows.worst(frame(run), 1)
    # 9 June follows a day without change, so its move may span several days and is left out
    assert w1 == pytest.approx(0.05) and day == pd.Timestamp("2024-06-10")
    w7, _ = flows.worst(frame(run), 7)
    assert w7 == pytest.approx(1 - 0.95 ** 5)
    assert np.isnan(flows.worst(frame(spike), 1)[0]) or flows.worst(frame(spike), 1)[0] == 0
    assert flows.informative(frame(run).circulating)[0] is False


def test_pages():
    sg = ("<p>USD CoinVertible in circulation 14 176 206,00 Last update 20/10/2026 BNY : 77.59% | Societe Generale : "
          "22.41%</p><p>EUR CoinVertible in circulation 169 091 433,55 Last update 20/10/2026 Societe Generale : 100%</p>")
    usd, eur = pages.sgforge(sg)
    assert usd["bank_shares"] == {"BNY": 0.7759, "Societe Generale": 0.2241} and eur["circulation"] == 169091433.55
    qz = ("Published snapshot 30 August 2026 EURQ Euro e-money token Tokens in circulation €4,302,714 Reserve ratio "
          "100.76% Reported reserve composition Cash 33% Government bonds 66% USDQ US dollar e-money token Tokens in "
          "circulation $5,684,016 Reserve ratio 101.91% Reported reserve composition Cash 33% Government bonds 66%")
    e, u = pages.quantoz(qz)
    assert e["circulation"] == 4302714 and u["reserve_ratio"] == pytest.approx(1.0191)


def test_rules_apply():
    by_name = {r.rule: r for r in rules.RULES}
    art54 = by_name["Deposits at credit institutions"]
    assert rules.applicable(art54, False) and not rules.applicable(art54, True)  # replaced for significant tokens
    sig = by_name["Deposits per currency, significant token"]
    assert rules.applicable(sig, True) and not rules.applicable(sig, False)
    other = by_name["Deposits per currency, other tokens"]
    assert rules.applicable(other, False) and not rules.applicable(other, True)
    assert art54.passes(0.3) and not art54.passes(0.29)
