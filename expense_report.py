from datetime import datetime
from collections import defaultdict
import pytz
from sheets_service import get_sheet, SHEET_EXPENSES
from settings import TIMEZONE

SGT = pytz.timezone(TIMEZONE)

# Approximate FX rates to SGD
FX_RATES = {
    "SGD": 1.0,
    "USD": 1.35,
    "EUR": 1.47,
    "GBP": 1.71,
    "JPY": 0.009,
    "AUD": 0.88,
    "HKD": 0.17,
    "MYR": 0.30,
    "THB": 0.038,
    "IDR": 0.000082,
    "CNY": 0.187,
    "GBP": 1.71,
    "CAD": 1.00,
    "NZD": 0.82,
}


def get_all_expenses() -> list:
    try:
        sheet = get_sheet(SHEET_EXPENSES)
        return sheet.get_all_records()
    except:
        return []


def current_year() -> str:
    return datetime.now(SGT).strftime("%Y")


def current_month() -> str:
    return datetime.now(SGT).strftime("%Y-%m")


def month_name(month_str: str) -> str:
    try:
        return datetime.strptime(month_str, "%Y-%m").strftime("%B %Y")
    except:
        return month_str


def format_currency_breakdown(entries: list) -> dict:
    """Group entries by original currency, return subtotals and SGD total."""
    by_currency = defaultdict(float)
    sgd_total = 0.0

    for e in entries:
        curr = str(e.get("currency_original", "SGD")).upper().strip()
        amt_orig = float(e.get("amount_original", 0) or 0)
        amt_sgd = float(e.get("amount_sgd", 0) or 0)

        by_currency[curr] += amt_orig
        sgd_total += amt_sgd

    return {"by_currency": dict(by_currency), "sgd_total": round(sgd_total, 2)}


def format_monthly_report(records: list, month: str) -> str:
    entries = [r for r in records if str(r.get("month", "")) == month]
    if not entries:
        return f"No expenses found for {month_name(month)}."

    lines = []
    lines.append(f"💸 *{month_name(month)} — Expense Report*\n")

    for cat in ["Personal", "Palfinger"]:
        cat_entries = [e for e in entries if e.get("category") == cat]
        if not cat_entries:
            continue

        cat_total = sum(float(e.get("amount_sgd", 0) or 0) for e in cat_entries)
        lines.append(f"*{cat}* — SGD {cat_total:,.2f}")

        # Group by subcategory
        by_sub = defaultdict(list)
        for e in cat_entries:
            sub = e.get("subcategory", "Other") or "Other"
            by_sub[sub].append(e)

        for sub, sub_entries in sorted(by_sub.items()):
            breakdown = format_currency_breakdown(sub_entries)
            sub_sgd = breakdown["sgd_total"]
            by_curr = breakdown["by_currency"]

            # Currency breakdown string
            curr_parts = []
            for curr, amt in sorted(by_curr.items()):
                if curr == "SGD":
                    curr_parts.append(f"SGD {amt:,.2f}")
                else:
                    curr_parts.append(f"{curr} {amt:,.2f} ≈ SGD {amt * FX_RATES.get(curr, 1):,.2f}")

            if len(curr_parts) == 1:
                lines.append(f"  • {sub}: {curr_parts[0]}")
            else:
                lines.append(f"  • {sub}: SGD {sub_sgd:,.2f}")
                for cp in curr_parts:
                    lines.append(f"    ↳ {cp}")

        lines.append("")

    # Overall totals
    total_breakdown = format_currency_breakdown(entries)
    by_curr = total_breakdown["by_currency"]
    sgd_total = total_breakdown["sgd_total"]

    lines.append(f"*TOTAL: SGD {sgd_total:,.2f}*")

    non_sgd = {k: v for k, v in by_curr.items() if k != "SGD"}
    if non_sgd:
        lines.append("_Currency breakdown:_")
        if by_curr.get("SGD"):
            lines.append(f"  SGD {by_curr['SGD']:,.2f}")
        for curr, amt in sorted(non_sgd.items()):
            rate = FX_RATES.get(curr, 1)
            lines.append(f"  {curr} {amt:,.2f} → SGD {amt * rate:,.2f} (est. rate: {rate})")

    return "\n".join(lines)


def format_ytd_report(records: list) -> str:
    year = current_year()
    entries = [r for r in records if str(r.get("month", "")).startswith(year)]
    if not entries:
        return f"No expenses found for {year}."

    lines = []
    lines.append(f"📊 *{year} — Year to Date Report*\n")

    # Monthly summary table
    months_seen = sorted(set(str(r.get("month", "")) for r in entries))
    lines.append("*Monthly Overview*")
    for m in months_seen:
        m_entries = [r for r in entries if str(r.get("month", "")) == m]
        m_total = sum(float(e.get("amount_sgd", 0) or 0) for e in m_entries)
        personal = sum(float(e.get("amount_sgd", 0) or 0) for e in m_entries if e.get("category") == "Personal")
        palfinger = sum(float(e.get("amount_sgd", 0) or 0) for e in m_entries if e.get("category") == "Palfinger")
        lines.append(f"  {month_name(m)}: SGD {m_total:,.2f}  (P: {personal:,.0f} | W: {palfinger:,.0f})")

    lines.append("")

    # YTD by category
    for cat in ["Personal", "Palfinger"]:
        cat_entries = [e for e in entries if e.get("category") == cat]
        if not cat_entries:
            continue

        cat_total = sum(float(e.get("amount_sgd", 0) or 0) for e in cat_entries)
        lines.append(f"*{cat} YTD* — SGD {cat_total:,.2f}")

        by_sub = defaultdict(list)
        for e in cat_entries:
            sub = e.get("subcategory", "Other") or "Other"
            by_sub[sub].append(e)

        for sub, sub_entries in sorted(by_sub.items(), key=lambda x: -sum(float(e.get("amount_sgd", 0) or 0) for e in x[1])):
            sub_total = sum(float(e.get("amount_sgd", 0) or 0) for e in sub_entries)
            pct = (sub_total / cat_total * 100) if cat_total > 0 else 0
            lines.append(f"  • {sub}: SGD {sub_total:,.2f} ({pct:.0f}%)")

        lines.append("")

    # Currency breakdown YTD
    breakdown = format_currency_breakdown(entries)
    by_curr = breakdown["by_currency"]
    sgd_total = breakdown["sgd_total"]

    lines.append(f"*YTD TOTAL: SGD {sgd_total:,.2f}*")
    non_sgd = {k: v for k, v in by_curr.items() if k != "SGD"}
    if non_sgd:
        lines.append("_Multi-currency breakdown:_")
        if by_curr.get("SGD"):
            lines.append(f"  SGD {by_curr['SGD']:,.2f}")
        for curr, amt in sorted(non_sgd.items()):
            rate = FX_RATES.get(curr, 1)
            lines.append(f"  {curr} {amt:,.2f} → SGD {amt * rate:,.2f}")

    return "\n".join(lines)


def format_category_report(records: list, category: str) -> str:
    """Detailed breakdown for one category across all time."""
    year = current_year()
    entries = [r for r in records if str(r.get("month", "")).startswith(year) and r.get("category") == category]
    if not entries:
        return f"No {category} expenses found for {year}."

    lines = []
    lines.append(f"📊 *{category} — {year} Detail*\n")

    by_sub = defaultdict(list)
    for e in entries:
        sub = e.get("subcategory", "Other") or "Other"
        by_sub[sub].append(e)

    total = sum(float(e.get("amount_sgd", 0) or 0) for e in entries)

    for sub, sub_entries in sorted(by_sub.items(), key=lambda x: -sum(float(e.get("amount_sgd", 0) or 0) for e in x[1])):
        sub_total = sum(float(e.get("amount_sgd", 0) or 0) for e in sub_entries)
        pct = (sub_total / total * 100) if total > 0 else 0
        lines.append(f"*{sub}* — SGD {sub_total:,.2f} ({pct:.0f}%)")

        # Show individual entries (latest 5)
        sorted_entries = sorted(sub_entries, key=lambda x: x.get("timestamp", ""), reverse=True)
        for e in sorted_entries[:5]:
            date = str(e.get("timestamp", ""))[:10]
            desc = e.get("description", "")
            curr = str(e.get("currency_original", "SGD")).upper()
            amt_orig = float(e.get("amount_original", 0) or 0)
            amt_sgd = float(e.get("amount_sgd", 0) or 0)

            if curr != "SGD":
                lines.append(f"  {date} — {desc} ({curr} {amt_orig:,.2f} = SGD {amt_sgd:,.2f})")
            else:
                lines.append(f"  {date} — {desc} (SGD {amt_sgd:,.2f})")

        if len(sub_entries) > 5:
            lines.append(f"  _+{len(sub_entries)-5} more entries_")
        lines.append("")

    lines.append(f"*TOTAL: SGD {total:,.2f}*")
    return "\n".join(lines)
