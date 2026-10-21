"""Holdings from Circle's monthly USDC and EURC examination reports (PDF), checked against the reports' own totals.

Each report covers two dates. For each date the parser returns one row per holding: Treasury bills with their
CUSIP and maturity, repurchase agreements, cash in the Circle Reserve Fund, cash at regulated financial
institutions, and the net timing adjustment. Every subtotal and total printed in the report must equal the sum
of the parsed lines, otherwise parsing fails.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pdfplumber

AMOUNT = r"[€$]?\s?\(?[€$]?\s?[\d,]+\)?"
DATE_WORDS = r"[A-Z][a-z]+ \d{1,2}, \d{4}"
TBILL = re.compile(r"^([0-9A-Z]{9}) (\d{2}/\d{2}/\d{2}) ([\d,]+)$")
LABELS = {
    "repo": re.compile(r"^U\.S\.? Treasury Repurchase Agreements\d?"),
    "fund_cash": re.compile(r"^Cash held in Circle Reserve Fund"),
    "bank_cash": re.compile(r"^Cash held at regulated financial institutions"),
    "timing": re.compile(r"^Cash due to/\(owed by\) .* net\d?"),
    "tbill_total": re.compile(r"^TOTAL U\.S\. TREASURY SECURITIES"),
    "section_total": re.compile(r"^TOTAL (CIRCLE RESERVE FUND|OTHER USDC RESERVE) ASSETS"),
}


class ParseError(Exception):
    pass


@dataclass(frozen=True)
class Holding:
    token: str
    report_date: date
    pool: str  # "fund" (Circle Reserve Fund) or "direct"
    kind: str  # tbill, repo, fund_cash, bank_cash, timing
    amount: int
    cusip: str = ""
    maturity: date | None = None


def amount(text: str) -> int:
    t = text.strip()
    value = int(re.sub(r"[^\d]", "", t))
    return -value if "(" in t else value


def _value_after(lines: list[str], i: int, label: re.Pattern, used: set[int]) -> int:
    """The amount after the label on line i; or a lone amount on the next line, else on the previous one.

    Text extraction puts some amounts on their own line, before or after their label. A lone amount is used once;
    a wrong assignment cannot pass the section totals.
    """
    rest = label.sub("", lines[i]).strip()
    if re.fullmatch(AMOUNT, rest):
        return amount(rest)
    for j in (i + 1, i - 1):
        if 0 <= j < len(lines) and j not in used and re.fullmatch(AMOUNT, lines[j].strip()):
            used.add(j)
            return amount(lines[j])
    raise ParseError(f"no amount for: {lines[i]!r}")


def report_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages[1:])  # page 1 is the accountants' letter


def parse(path: Path) -> tuple[list[Holding], list[dict]]:
    """Holdings and one summary row per report date (circulation, reserve)."""
    return parse_text(report_text(path), path.name)


def parse_text(text: str, name: str) -> tuple[list[Holding], list[dict]]:
    token = "USDC" if "USDC Reserve Report" in text else "EURC" if "EURC Reserve Report" in text else None
    if token is None:
        raise ParseError(f"{name}: not a USDC or EURC reserve report")
    m = re.search(rf"Report Dates ({DATE_WORDS}) ({DATE_WORDS})", text)
    if not m:
        raise ParseError(f"{name}: report dates not found")
    dates = [datetime.strptime(d, "%B %d, %Y").date() for d in m.groups()]
    circ = re.search(rf"{token} in Circulation ([\d,]+) ([\d,]+)", text)
    fair = re.search(rf"Fair Value of Assets Held in {token} Reserve [$€] ([\d,]+) [$€] ([\d,]+)", text)
    if not circ or not fair:
        raise ParseError(f"{name}: circulation or reserve not found")
    lines = [ln.strip() for ln in text.splitlines()]
    holdings, summary = [], []
    for k, d in enumerate(dates):
        stamp = d.strftime("%B %-d, %Y").upper()
        rows = _usdc_date(lines, token, d, stamp) if token == "USDC" else _eurc_date(lines, token, d, stamp)
        total = sum(h.amount for h in rows)
        if total != amount(fair.group(k + 1)):
            raise ParseError(f"{name} {d}: holdings sum to {total}, the report says {fair.group(k + 1)}")
        holdings += rows
        summary.append({"token": token, "report_date": d, "circulation": amount(circ.group(k + 1)),
                        "reserve": total, "source": name})
    return holdings, summary


def _section(lines: list[str], header: str, end: re.Pattern) -> list[str]:
    try:
        start = lines.index(header)
    except ValueError as e:
        raise ParseError(f"section not found: {header}") from e
    out = []
    for ln in lines[start + 1:]:
        out.append(ln)
        if end.match(ln):
            return out
    raise ParseError(f"section not closed: {header}")


def _usdc_date(lines: list[str], token: str, d: date, stamp: str) -> list[Holding]:
    rows: list[Holding] = []
    for pool, header in (("fund", f"CIRCLE RESERVE FUND ASSETS AS OF {stamp}"),
                         ("direct", f"OTHER USDC RESERVE ASSETS AS OF {stamp}")):
        sec = _section(lines, header, LABELS["section_total"])
        bills, values, used = [], {}, set()
        for i, ln in enumerate(sec):
            if mt := TBILL.match(ln):
                bills.append(Holding(token, d, pool, "tbill", amount(mt.group(3)), mt.group(1),
                                     datetime.strptime(mt.group(2), "%m/%d/%y").date()))
                continue
            for key, label in LABELS.items():
                if label.match(ln):
                    values[key] = _value_after(sec, i, label, used)
        if bills and values.get("tbill_total") != sum(b.amount for b in bills):
            raise ParseError(f"{d} {pool}: Treasury bills do not add up to their printed total")
        parts = bills + [Holding(token, d, pool, k, v) for k, v in values.items()
                         if k in ("repo", "fund_cash", "bank_cash", "timing")]
        if sum(p.amount for p in parts) != values.get("section_total"):
            raise ParseError(f"{d} {pool}: lines do not add up to the section total")
        rows += parts
    return rows


def _eurc_date(lines: list[str], token: str, d: date, stamp: str) -> list[Holding]:
    sec = _section(lines, f"EURC RESERVE ASSETS AS OF {stamp}", re.compile(rf"^TOTAL EURC RESERVE ASSETS AS OF {stamp}"))
    values, used = {}, set()
    for i, ln in enumerate(sec):
        for key in ("bank_cash", "timing"):
            if LABELS[key].match(ln):
                values[key] = _value_after(sec, i, LABELS[key], used)
    total = amount(re.sub(rf"^TOTAL EURC RESERVE ASSETS AS OF {stamp}", "", sec[-1]))
    rows = [Holding(token, d, "direct", k, v) for k, v in values.items()]
    if sum(r.amount for r in rows) != total:
        raise ParseError(f"{d}: EURC lines do not add up to the printed total")
    return rows
