"""MiCA reserve rules for e-money tokens, as numbers, with their legal status on 20 October 2026."""

from __future__ import annotations

from dataclasses import dataclass

IN_FORCE = "in force"
DRAFT = "draft, not adopted"

MICA = "Regulation (EU) 2023/1114 (MiCA)"
RTS_LIQ = "EBA/RTS/2024/10, final draft of 13 June 2024 (article 36(4) of MiCA)"
RTS_HLFI = "EBA/RTS/2024/11, final draft of 13 June 2024 (article 38(5) of MiCA)"


@dataclass(frozen=True)
class Rule:
    rule: str
    metric: str
    op: str  # ">=" or "<="
    threshold: float
    applies_to: str  # "all", "significant", "non-significant if required"
    status: str
    source: str

    def passes(self, value: float) -> bool:
        return value >= self.threshold if self.op == ">=" else value <= self.threshold


RULES = (
    Rule("Deposits at credit institutions, all e-money tokens", "deposit_share", ">=", 0.30, "all", IN_FORCE,
         f"{MICA}, article 54(a)"),
    Rule("Deposits per currency, significant token", "deposit_share", ">=", 0.60, "significant", DRAFT,
         f"{RTS_LIQ}, article 3; floor set by MiCA article 45(7)(b)"),
    Rule("Assets available within one working day, significant token", "daily_share", ">=", 0.40, "significant",
         DRAFT, f"{RTS_LIQ}, article 1"),
    Rule("Assets available within five working days, significant token", "weekly_share", ">=", 0.60, "significant",
         DRAFT, f"{RTS_LIQ}, article 1"),
    Rule("Deposits per currency, other tokens", "deposit_share", ">=", 0.30, "non-significant if required", DRAFT,
         f"{RTS_LIQ}, article 3; floor set by MiCA article 36(4)(d)"),
    Rule("Assets available within one working day, other tokens", "daily_share", ">=", 0.20,
         "non-significant if required", DRAFT, f"{RTS_LIQ}, article 1"),
    Rule("Assets available within five working days, other tokens", "weekly_share", ">=", 0.30,
         "non-significant if required", DRAFT, f"{RTS_LIQ}, article 1"),
    Rule("Deposits at one global or other systemically important institution", "largest_bank_share", "<=", 0.25,
         "significant", DRAFT, f"{RTS_LIQ}, article 5(1)"),
    Rule("Deposits at one global or other systemically important institution, other tokens", "largest_bank_share",
         "<=", 0.25, "non-significant if required", DRAFT, f"{RTS_LIQ}, article 5(1)"),
    Rule("Units of funds of one management company", "fund_share", "<=", 0.05, "all", DRAFT,
         f"{RTS_HLFI}, article 3(1); binds all issuers through MiCA article 54(b) in the EBA opinion EBA/Op/2025/14"),
    Rule("Securities of one sovereign issuer", "sovereign_share", "<=", 0.35, "all", DRAFT,
         f"{RTS_HLFI}, article 3(1)"),
)


def applicable(rule: Rule, significant: bool) -> bool:
    if rule.applies_to == "all":
        return True
    return significant if rule.applies_to == "significant" else not significant
