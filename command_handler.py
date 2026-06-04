from datetime import datetime
from collections import defaultdict
import pytz
from telegram import Update
from telegram.ext import ContextTypes

from settings import ALLOWED_USER_ID, TIMEZONE
from sheets_service import get_open_todos, get_expenses_mtd, get_expenses_today, search_thoughts
from digest_service import format_morning_digest, format_evening_digest
from expense_report import get_all_expenses, format_monthly_report, format_ytd_report, format_category_report, current_month

SGT = pytz.timezone(TIMEZONE)


def auth(update) -> bool:
    return str(update.effective_user.id) == str(ALLOWED_USER_ID)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    await update.message.reply_text(
        "👋 *James Bot is live.*\n\n"
        "Track expenses, todos, thoughts, and reminders — all in natural language.\n\n"
        "*Just talk to me:*\n"
        "• _spent 45 on lunch_ → expense\n"
        "• _need to call John tomorrow_ → todo\n"
        "• _remind me about the board meeting Friday 9am_ → reminder + calendar\n"
        "• _interesting: systems beat tools_ → thought archive\n"
        "• _done with the Palfinger proposal_ → mark complete\n\n"
        "*Commands:*\n"
        "/digest — current summary\n"
        "/todos — open todos\n"
        "/expenses — today + MTD by category\n"
        "/monthly — full monthly report\n"
        "/ytd — year to date report\n"
        "/personal — Personal detail\n"
        "/palfinger — Palfinger detail\n"
        "/thoughts <keyword> — search thoughts\n"
        "/help — this message\n\n"
        "Auto-digests at *8:00 AM* and *10:00 PM* SGT.",
        parse_mode='Markdown'
    )


async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    hour = datetime.now(SGT).hour
    digest = format_morning_digest() if hour < 14 else format_evening_digest()
    await update.message.reply_text(digest, parse_mode='Markdown')


async def todos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    todos = get_open_todos()
    if todos['total'] == 0:
        await update.message.reply_text("No open todos.")
        return
    msg = f"📋 *Open To-Dos* ({todos['total']})\n\n"
    if todos['personal']:
        msg += f"*Personal ({len(todos['personal'])})*\n"
        for t in todos['personal']:
            icon = "🔴" if t.get('priority') == 'high' else "🟡"
            due = f" _(due {t.get('due_date')})_" if t.get('due_date') else ""
            msg += f"  {icon} {t.get('title')}{due}\n"
        msg += "\n"
    if todos['palfinger']:
        msg += f"*Palfinger ({len(todos['palfinger'])})*\n"
        for t in todos['palfinger']:
            icon = "🔴" if t.get('priority') == 'high' else "🟡"
            due = f" _(due {t.get('due_date')})_" if t.get('due_date') else ""
            msg += f"  {icon} {t.get('title')}{due}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')


async def expenses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    today = get_expenses_today()
    records = get_all_expenses()
    month = current_month()
    month_entries = [r for r in records if str(r.get("month", "")) == month]
    now = datetime.now(SGT)

    msg = f"💸 *Expenses — {now.strftime('%B %Y')}*\n\n"

    # Today
    msg += f"*Today*\n"
    msg += f"  Personal: SGD {today['personal']:,.2f}\n"
    msg += f"  Palfinger: SGD {today['palfinger']:,.2f}\n"
    msg += f"  Total: SGD {today['total']:,.2f}\n\n"

    # MTD by category breakdown
    msg += f"*Month to Date*\n"
    for cat in ["Personal", "Palfinger"]:
        cat_entries = [e for e in month_entries if e.get("category") == cat]
        if not cat_entries:
            continue
        cat_total = sum(float(e.get("amount_sgd", 0) or 0) for e in cat_entries)
        msg += f"\n_{cat}_ — SGD {cat_total:,.2f}\n"

        by_sub = defaultdict(float)
        for e in cat_entries:
            sub = e.get("subcategory", "Other") or "Other"
            by_sub[sub] += float(e.get("amount_sgd", 0) or 0)

        for sub, amt in sorted(by_sub.items(), key=lambda x: -x[1]):
            msg += f"  • {sub}: SGD {amt:,.2f}\n"

    grand = sum(float(e.get("amount_sgd", 0) or 0) for e in month_entries)
    msg += f"\n*TOTAL: SGD {grand:,.2f}*"

    await update.message.reply_text(msg, parse_mode='Markdown')


async def monthly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    await update.message.reply_text("_Pulling monthly report..._", parse_mode='Markdown')
    records = get_all_expenses()
    args = context.args
    month = args[0] if args else current_month()
    report = format_monthly_report(records, month)
    if len(report) > 4000:
        for chunk in [report[i:i+4000] for i in range(0, len(report), 4000)]:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text(report, parse_mode='Markdown')


async def ytd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    await update.message.reply_text("_Pulling year-to-date report..._", parse_mode='Markdown')
    records = get_all_expenses()
    report = format_ytd_report(records)
    if len(report) > 4000:
        for chunk in [report[i:i+4000] for i in range(0, len(report), 4000)]:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text(report, parse_mode='Markdown')


async def personal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    await update.message.reply_text("_Pulling Personal detail..._", parse_mode='Markdown')
    records = get_all_expenses()
    report = format_category_report(records, "Personal")
    if len(report) > 4000:
        for chunk in [report[i:i+4000] for i in range(0, len(report), 4000)]:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text(report, parse_mode='Markdown')


async def palfinger_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    await update.message.reply_text("_Pulling Palfinger detail..._", parse_mode='Markdown')
    records = get_all_expenses()
    report = format_category_report(records, "Palfinger")
    if len(report) > 4000:
        for chunk in [report[i:i+4000] for i in range(0, len(report), 4000)]:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text(report, parse_mode='Markdown')


async def thoughts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /thoughts <keyword>\nExample: /thoughts systems")
        return
    query = " ".join(args)
    results = search_thoughts(query)
    if not results:
        await update.message.reply_text(f"No thoughts found for '{query}'.")
        return
    msg = f"💭 *Thoughts: '{query}'* ({len(results)})\n\n"
    for t in results[:5]:
        tags = t.get('tags', '')
        msg += f"• {t.get('content')}\n"
        if tags:
            msg += f"  _{tags}_\n"
        msg += "\n"
    await update.message.reply_text(msg, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)


async def fitness_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    from fitness_service import format_fitness_report
    report = format_fitness_report()
    await update.message.reply_text(report, parse_mode='Markdown')
