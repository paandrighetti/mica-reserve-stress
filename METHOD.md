# Method

## Question

What do public disclosures show about the reserves of the main e-money tokens against the reserve and
liquidity rules of MiCA (Regulation (EU) 2023/1114), those in force and those still in draft, and how much
redemption stress could those reserves absorb within one and five working days?

Tokens: USDC and EURC (Circle), EURCV and USDCV (Societe Generale-FORGE), EURQ and USDQ (Quantoz). USDC was
classified as the first significant e-money token by the EBA on 14 October 2026, with EBA supervision from
12 November 2026; the others are not significant.

## Rules (`outputs/rules.csv`)

| Rule | Threshold | Applies to | Status on 20 October 2026 |
| --- | --- | --- | --- |
| Deposits at credit institutions, MiCA article 54(a) | at least 30% | every e-money token | in force |
| Deposits per currency, draft RTS article 3 (EBA/RTS/2024/10) | at least 60% / 30% | significant / others if the authority requires it | draft, not adopted |
| Assets available within one working day, draft RTS article 1 | at least 40% / 20% | significant / others if required | draft |
| Assets available within five working days, draft RTS article 1 | at least 60% / 30% | significant / others if required | draft |
| Deposits at one global or other systemically important institution, draft RTS article 5(1) | at most 25% | significant / others if required | draft |
| Units of funds of one management company, draft RTS on highly liquid financial instruments, article 3(1) (EBA/RTS/2024/11) | at most 5% | every issuer, through article 54(b), in the EBA's opinion EBA/Op/2025/14 | draft |
| Securities of one sovereign issuer, same RTS, article 3(1) | at most 35% | every issuer | draft |

The Commission has not adopted the two draft RTS. Its amendments of 28 August 2025 and the EBA's opinions of
9 October 2025 leave the e-money token figures above unchanged.

## Data

- Circle's examination reports for USDC and EURC, January to August 2026, two dates each (32 snapshots).
  `src/mrs/circle.py` parses every line and requires each printed subtotal and total to equal the sum of the
  parsed lines.
- The SG-FORGE CoinVertible page (EURCV, USDCV: circulation and share of the reserve per named bank) and the
  Quantoz transparency page (EURQ, USDQ: circulation, reserve ratio, cash and government bond shares), saved on
  20 October 2026.
- DefiLlama daily circulating supply, which leaves out tokens minted but held by the issuer, for the six tokens
  and for the reference episodes (USDT, BUSD, TUSD).
- `sources/MANIFEST.json` gives the URL, size, SHA-256 and download time of every file.

## Scope limits, stated before any result

- MiCA's reserve rules bind the EU issuer's reserve. For USDC this is the reserve of Circle Internet Financial
  Europe SAS, which must equal EEA holdings (Circle's MiCA white paper, F.1.4) and is not published separately.
  USDC figures describe the global reserve. They show what the published reserve would look like under the rules,
  not whether the EU reserve complies.
- Notice periods of bank deposits are not disclosed: deposits are treated as available within one working day.
- Bank names are published only by SG-FORGE, so bank concentration is tested only for EURCV and USDCV.
- Quantoz does not say how its government bonds split by issuer or maturity: they count in no liquidity bucket
  and the single-issuer test is "not disclosed".

## Liquidity buckets

- One working day: bank deposits, overnight repurchase agreements, cash held in a fund, and Treasury bills
  maturing within one working day of the report date. Five working days: the same plus bills maturing within
  five working days. Working days exclude weekends and US federal holidays for dollar assets, TARGET closing
  days for euro assets (`holidays` package). Timing and settlement adjustments count in the reserve total but in
  no bucket.
- Two readings of the assets USDC holds through the Circle Reserve Fund, a US government money market fund
  under Rule 2a-7:
  - look-through: the fund's repurchase agreements, bills and cash are classified by their own maturity;
  - strict: units of such a fund are not highly liquid financial instruments under the EBA's draft RTS (they are
    neither level 1 assets nor units of a UCITS investing only in eligible assets), so they count in no bucket.
- The 5% fund-unit limit is applied as if the fund were eligible, its most lenient reading.

## Redemption stress

- Net outflow over h calendar days (h = 1, 7, 30) = fall in DefiLlama circulating supply as a share of the
  supply h days before. One working day is compared with one calendar day, five working days with seven.
- Own history: days on which the supply is at least 10% of the token's latest supply and at least one million
  units, after the first 90 days of the series. Earlier days measure a token of another size.
- A one-day fall that comes back by at least 80% within two days is treated as a data change, not a
  redemption, and skipped when looking for the worst day.
- A series that changes on fewer than half of its days does not measure daily flows; its own-history figures are
  reported as "not informative" and not used in the stress table.
- Reference episodes, on the same series: USDC 8 to 31 March 2023 (Silicon Valley Bank), BUSD 10 February to
  15 April 2023 (stop of minting), USDT 7 to 31 May 2022 (Terra), TUSD 10 to 31 January 2024. The stress
  outflow for a horizon is the largest of these episodes at that horizon.
- The EBA's guidelines on liquidity stress testing (EBA/GL/2024/08, paragraphs 11 to 13) ask for gross
  outflows. DefiLlama gives net flows, which understate them. A sensitivity scales the reference outflows by the
  gross-to-net ratio of 13 March 2023: 2.9 billion USDC redeemed and 0.7 billion issued (Reuters, 14 March 2023).
- Coverage = assets of the bucket / stressed outflow, both against circulation. For one working day, the report
  also gives the share of bank deposits that could be frozen, as at Silicon Valley Bank in March 2023, before
  the one-day bucket falls short of the stressed outflow.

## Cross-check

DefiLlama's supply is compared with the attested circulation at each of Circle's 32 report dates.
