"""Reserve figures from the SG-FORGE CoinVertible page and the Quantoz transparency page (HTML snapshots)."""

from __future__ import annotations

import html
import re
from datetime import date, datetime


def page_text(raw: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.DOTALL)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))


def _number(s: str) -> float:
    """'14 176 206,00' (French) or '4,302,714' (English) to a float."""
    s = s.strip().replace("\u202f", " ").replace("\xa0", " ")
    if re.fullmatch(r"[\d ]+,\d{2}", s):
        return float(s.replace(" ", "").replace(",", "."))
    return float(s.replace(",", ""))


def sgforge(raw: str) -> list[dict]:
    """EURCV and USDCV: circulation, date and the share of the reserve held at each named bank."""
    text = page_text(raw)
    out = []
    for token, name in (("USDCV", "USD CoinVertible"), ("EURCV", "EUR CoinVertible")):
        m = re.search(rf"{name} in circulation ([\d  ,]+?) Last update (\d{{2}}/\d{{2}}/\d{{4}}) (.*?)(?=(?:USD|EUR) CoinVertible in circulation|$)", text)
        if not m:
            raise ValueError(f"{token} not found on the SG-FORGE page")
        banks = re.findall(r"([A-Z][A-Za-z ]+?) : ([\d.]+)%", m.group(3))
        shares = {b.strip(): float(p) / 100 for b, p in banks}
        if abs(sum(shares.values()) - 1) > 0.005:
            raise ValueError(f"{token}: bank shares sum to {sum(shares.values())}")
        out.append({"token": token, "report_date": datetime.strptime(m.group(2), "%d/%m/%Y").date(),  # noqa: DTZ007 (a date)
                    "circulation": _number(m.group(1)), "bank_shares": shares,
                    "composition": {"bank_cash": 1.0}, "source": "sgforge_coinvertible.html"})
    return out


def quantoz(raw: str) -> list[dict]:
    """EURQ and USDQ: circulation, reserve ratio and the reported composition (cash, government bonds)."""
    text = page_text(raw)
    m = re.search(r"Published snapshot (\d{1,2} [A-Z][a-z]+ \d{4})", text)
    if not m:
        raise ValueError("snapshot date not found on the Quantoz page")
    when: date = datetime.strptime(m.group(1), "%d %B %Y").date()  # noqa: DTZ007 (a date)
    out = []
    for token in ("EURQ", "USDQ"):
        t = re.search(rf"{token} .*? Tokens in circulation [€$]([\d,]+) Reserve ratio ([\d.]+)% Reported reserve "
                      r"composition Cash (\d+)% Government bonds (\d+)%", text)
        if not t:
            raise ValueError(f"{token} not found on the Quantoz page")
        out.append({"token": token, "report_date": when, "circulation": _number(t.group(1)),
                    "reserve_ratio": float(t.group(2)) / 100,
                    "composition": {"bank_cash": float(t.group(3)) / 100, "government_bonds": float(t.group(4)) / 100},
                    "bank_shares": {}, "source": "quantoz_transparency.html"})
    return out
