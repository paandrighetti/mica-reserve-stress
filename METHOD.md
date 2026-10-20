# Method

## Question

What do public disclosures show about the reserves of the main e-money tokens against the reserve and liquidity
rules of MiCA, the EU's Markets in Crypto-Assets Regulation (Regulation (EU) 2023/1114), both the rules in force
and those still in draft? And how much redemption stress could those reserves absorb within one and five working
days?

Tokens: USDC and EURC (Circle), EURCV and USDCV (Societe Generale-FORGE, the Societe Generale subsidiary that
issues them) and EURQ and USDQ (Quantoz). The European Banking Authority (EBA) classified USDC as the first
significant e-money token on 14 October 2026, with EBA supervision from 12 November 2026. The other tokens are not
significant.

## Rules (`outputs/rules.csv`)

The rules depend on whether a token is significant:

- For a token that is not significant, MiCA article 54 governs the funds safeguarded under article 7(1) of the
  e-money directive.
- For a significant token, article 58(1)(a) replaces that safeguarding with articles 36 to 38 and 45(1) to (4).
  Their figures are set by two draft regulatory technical standards (RTS).

USDC's snapshot is therefore tested against both regimes: not significant until 11 November 2026, significant
from 12 November 2026.

| Rule | Significant token | Other tokens | Status on 20 October 2026 |
| --- | --- | --- | --- |
| Deposits at credit institutions, MiCA article 54(a) | (replaced) | at least 30% | in force |
| Deposits per currency, draft RTS EBA/RTS/2024/10, article 3 | at least 60% | at least 30%, if the supervisor requires it | draft |
| Assets available within one working day, same draft, article 1(1) | at least 40% | at least 20%, if required | draft |
| Assets available within five working days, article 1(2) | at least 60% | at least 30%, if required | draft |
| Deposits at one credit institution, article 5(1) | at most 25% at a systemically important bank, 15% at another large bank, 5% at any other | same, if required | draft |
| Deposits at one credit institution as a share of its total assets, article 5(2) | at most 1.5% | same, if required | draft |
| Units of collective investment undertakings of one management company, draft RTS EBA/RTS/2024/11, article 3(1)(c) | at most 5% | same, if required | draft |
| Securities of one sovereign issuer, same draft, article 3(1)(a) | at most 35% | same, if required | draft |

**Adoption status.** On 20 October 2026, the EBA's pages for both drafts still describe them as final drafts
submitted to the Commission. The response of the European System of Central Banks to the MiCA review (September
2026) says they are not yet in force. The EBA's MiCA overview page labels the article 36(4) draft as published in
the Official Journal, but no such act was found.

**The 2025 amendments.** The Commission's amendments of 28 August 2025 leave unchanged the figures above for
buckets, deposit minimums and per-bank caps. For eligible instruments, they would do two things:

- admit EU money market funds with a 10% limit;
- delete the 5% limit per management company.

The EBA rejected both in its opinion EBA/Op/2025/14 of 9 October 2025. The tests use the EBA's June 2024 drafts.

The concentration caps are tested at 25%, the most lenient. The disclosures do not allow the 1.5% test.

## Data

- **Circle's examination reports** for USDC and EURC, January to August 2026, each covering two report dates
  (16 snapshots per token). `src/mrs/circle.py` parses every line and requires each printed subtotal and total to
  equal the sum of the parsed lines.
- **Two web pages saved on 20 October 2026:**
  - The SG-FORGE CoinVertible page (EURCV and USDCV) gives circulation and the share of the reserve held at each
    named bank.
  - The Quantoz transparency page (EURQ and USDQ) gives circulation, reserve ratio, and the shares of cash and
    government bonds.
- **DefiLlama daily circulating supply** for the six tokens and for the reference episodes (USDT, BUSD, TUSD).
  DefiLlama leaves out tokens that are minted but still held by the issuer.
- **Manifest.** `sources/MANIFEST.json` gives the URL, size, SHA-256 and download time of every file.

## Scope limits

- **USDC.** MiCA's reserve rules bind the reserve of the EU issuer. For USDC this is Circle Internet Financial
  Europe SAS, whose reserve requirement equals the value of USDC held in the European Economic Area (EEA)
  (Circle's MiCA white paper, F.1.4). That reserve is not published separately. The USDC figures describe the
  global reserve: they show what the published reserve would look like under the rules, not whether the EU
  reserve complies.
- **Deposits.** The documents read give no notice periods for bank deposits, so deposits are treated as
  available within one working day. SG-FORGE gives no reserve amount; its statement that the tokens are fully
  backed by cash is taken at face value.
- **Bank concentration.** Bank names are published only by SG-FORGE, so bank concentration can be tested only for
  EURCV and USDCV.
- **Quantoz bonds.** Quantoz gives neither the issuers nor the maturities of its government bonds. They count in
  no liquidity bucket, and the single-issuer test is "not disclosed".

## Liquidity buckets

- **One working day:** bank deposits, overnight repurchase agreements, cash held in a fund, and Treasury bills
  maturing within one working day of the report date.
- **Five working days:** the same, plus bills maturing within five working days.
- **Working days** exclude weekends and US federal holidays for dollar assets. For euro assets they exclude the
  closing days of TARGET, the Eurosystem's payment system (`holidays` package).
- **Timing and settlement adjustments** count in the reserve total but in no bucket.
- **Two readings of the Circle Reserve Fund.** USDC holds most of its reserve through this fund, a US government
  money market fund under Rule 2a-7:
  - **Through the fund:** the fund's repurchase agreements, bills and cash are classified by their own maturity.
  - **Without the fund:** under the EBA's draft on eligible instruments, article 1 admits only zero-haircut
    level 1 assets, covered bonds and referenced assets. The EBA leaves fund units to MiCA article 38(2), which
    covers UCITS (undertakings for collective investment in transferable securities, the EU fund framework). On
    our reading, units of a US fund are therefore not eligible and count in no bucket. The draft says nothing
    explicit about non-UCITS funds.
- **The 5% limit on fund units** is applied as if the fund's units were eligible, the reading most favourable to
  the issuer.

## Redemption stress

- **Net outflow** over h calendar days (h = 1, 7, 30) is the fall in DefiLlama circulating supply, as a share of
  the supply h days before. One working day is compared with one calendar day, and five working days with seven.
- **Own history.** Only days on which the supply is at least 10% of the token's latest supply and at least one
  million units count, after the first 90 days of the series. Earlier days describe a much smaller token.
- **Data changes.** A move of at least 2% of supply is treated as a change in the data, not as issuance or
  redemption, if moves in the other direction within two days on either side offset at least 80% of it. Windows
  containing such a day are left out.
- **One-day moves after a quiet day** are left out. The day before them shows no change, so the move may add up
  several days of flows.
- **Series that rarely change.** A series that changes on fewer than half of its days does not measure daily
  flows. Its own-history figures are reported as "not informative" and are not used in the stress table.
- **Reference episodes,** measured on the same series:
  - USDC, 8 to 31 March 2023 (Silicon Valley Bank);
  - BUSD, 10 February to 15 April 2023 (stop of minting);
  - USDT, 7 to 31 May 2022 (Terra);
  - TUSD, 10 to 31 January 2024.

  The stressed outflow for a horizon is the largest of these episodes at that horizon.
- **Gross and net outflows.** The EBA's guidelines on liquidity stress testing (EBA/GL/2024/08, paragraphs 11 to
  13) ask for gross outflows. DefiLlama gives net flows, which understate them. A sensitivity scales the reference
  outflows by the gross-to-net ratio of 13 March 2023, when 2.9 billion USDC were redeemed and 0.7 billion issued
  (Reuters, 14 March 2023).
- **Coverage** is the assets of the bucket divided by the stressed outflow, both measured against circulation.
  For one working day, the report also gives the share of bank deposits that could be frozen before the one-day
  assets fall short of the stressed outflow, as happened in March 2023.

## Cross-check

DefiLlama's supply is compared with the attested circulation at each of Circle's 16 report dates per token.
