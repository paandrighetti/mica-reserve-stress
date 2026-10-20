# mica-reserve-stress

What do public disclosures say about the reserves of e-money tokens under MiCA, and how much redemption stress
could those reserves absorb within one and five working days?

The study reads the published reserves of six e-money tokens (USDC and EURC from Circle, EURCV and USDCV from
Societe Generale-FORGE, EURQ and USDQ from Quantoz), checks them against MiCA's reserve rules, those in force and
the EBA's draft technical standards, and replays the worst redemption episodes of stablecoins against their
liquid assets. USDC, classified as the first significant e-money token by the EBA on 14 October 2026, is the
main case.

Results: [REPORT.md](REPORT.md). Method, data and limits: [METHOD.md](METHOD.md).

## What it does

- Parses Circle's monthly examination reports line by line (Treasury bills with CUSIP and maturity, repurchase
  agreements, fund cash, bank deposits) and requires every printed subtotal and total to equal the sum of the
  parsed lines.
- Sorts each reserve into the one-day and five-day buckets of the draft RTS, on US or TARGET working days, under
  two readings of the Circle Reserve Fund: through the fund, or without it, since the EBA's draft on eligible
  instruments does not admit its units.
- Measures net redemptions from DefiLlama's daily supply, leaving out data changes, over each token's own history
  and over four reference runs (USDC 2023, BUSD 2023, USDT 2022, TUSD 2024).
- Computes coverage ratios and the share of bank deposits that could be frozen before the one-day assets fall
  short, the failure mode of March 2023.

## Run it

```
pip install -e ".[dev]"
python scripts/fetch_sources.py   # downloads the reports and pages listed in sources/MANIFEST.json
python scripts/build.py           # outputs/*.csv
python scripts/report.py          # REPORT.md
pytest -q
```

The examination reports and web pages are not stored here; `sources/MANIFEST.json` gives their URL and SHA-256.
The DefiLlama series used are stored in `sources/`.

## Layout

- `src/mrs/`: report parser (`circle.py`), web pages (`pages.py`), rules (`rules.py`), buckets (`buckets.py`),
  flows (`flows.py`).
- `scripts/`: `fetch_sources.py`, `build.py`, `report.py`.
- `outputs/`: holdings, snapshots, rule results, outflows, episodes, stress, checks.

## License

Code under the MIT license (`LICENSE`). Report text and tables under CC BY 4.0. Not legal advice: the draft
technical standards were not adopted on 20 October 2026, and the EU reserve of USDC is not published separately.
