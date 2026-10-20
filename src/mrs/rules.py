"""MiCA reserve rules for e-money tokens, as numbers, with their legal status on 20 October 2026.

A token is "significant" once the EBA has classified it (USDC: decision of 14 October 2026, EBA supervision
from 12 November 2026). Article 54 governs the funds of non-significant tokens, safeguarded under article 7(1)
of the e-money directive; for a significant token, article 58(1)(a) replaces that safeguarding with articles 36
to 38 and 45(1) to (4), whose figures sit in two draft regulatory technical standards (RTS) that the Commission
has not adopted.
"""

from __future__ import annotations

from dataclasses import dataclass

IN_FORCE = "in force"
DRAFT = "draft, not adopted"

MICA = "Regulation (EU) 2023/1114 (MiCA)"
RTS_LIQ = "EBA/RTS/2024/10, final draft of 13 June 2024 (MiCA article 36(4))"
RTS_HLFI = "EBA/RTS/2024/11, final draft of 13 June 2024 (MiCA article 38(5))"

NON_SIGNIFICANT = "non-significant"
SIGNIFICANT = "significant"
IF_REQUIRED = "non-significant, if the supervisor requires it"


@dataclass(frozen=True)
class Rule:
    rule: str
    metric: str | None  # None: the disclosures do not allow the test
    op: str  # ">=" or "<="
    threshold: float
    applies_to: str
    status: str
    source: str

    def passes(self, value: float) -> bool:
        return value >= self.threshold if self.op == ">=" else value <= self.threshold


def _pair(name: str, metric: str | None, op: str, significant: float, other: float, source: str) -> tuple[Rule, Rule]:
    return (Rule(f"{name}, significant token", metric, op, significant, SIGNIFICANT, DRAFT, source),
            Rule(f"{name}, other tokens", metric, op, other, IF_REQUIRED, DRAFT, source))


RULES = (
    Rule("Deposits at credit institutions", "deposit_share", ">=", 0.30, NON_SIGNIFICANT, IN_FORCE,
         f"{MICA}, article 54(a)"),
    *_pair("Deposits per currency", "deposit_share", ">=", 0.60, 0.30,
           f"{RTS_LIQ}, article 3; floors set by MiCA articles 45(7)(b) and 36(4)(d)"),
    *_pair("Assets available within one working day", "daily_share", ">=", 0.40, 0.20, f"{RTS_LIQ}, article 1(1)"),
    *_pair("Assets available within five working days", "weekly_share", ">=", 0.60, 0.30, f"{RTS_LIQ}, article 1(2)"),
    # Article 5(1): 25% at a global or other systemically important institution (article 131 of Directive
    # 2013/36/EU), 15% at another large institution, 5% at any other. Tested at 25%, the most lenient cap.
    *_pair("Deposits at one credit institution", "largest_bank_share", "<=", 0.25, 0.25, f"{RTS_LIQ}, article 5(1)"),
    *_pair("Deposits at one credit institution, share of its total assets", None, "<=", 0.015, 0.015,
           f"{RTS_LIQ}, article 5(2)"),
    *_pair("Units of collective investment undertakings of one management company", "fund_share", "<=", 0.05, 0.05,
           f"{RTS_HLFI}, article 3(1)(c)"),
    *_pair("Securities of one sovereign issuer", "sovereign_share", "<=", 0.35, 0.35, f"{RTS_HLFI}, article 3(1)(a)"),
)


def applicable(rule: Rule, significant: bool) -> bool:
    return rule.applies_to == SIGNIFICANT if significant else rule.applies_to in (NON_SIGNIFICANT, IF_REQUIRED)
