from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
        "/expenses — today + MTD\n"
        "/monthly — this month by category\n"
        "/ytd — year to date report\n"
        "/personal — Personal category detail\n"
        "/palfinger — Palfinger category detail\n"
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
            msg += f"  {icon} {t.get('title')}\n"
        msg += "\n"
    if todos['palfinger']:
        msg += f"*Palfinger ({len(todos['palfinger'])})*\n"
        for t in todos['palfinger']:
            icon = "🔴" if t.get('priority') == 'high' else "🟡"
            msg += f"  {icon} {t.get('title')}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')


async def expenses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    today = get_expenses_today()
    mtd = get_expenses_mtd()
    msg = (
        f"💸 *Expenses*\n\n"
        f"*Today*\n"
        f"  Personal: SGD {today['personal']:,.2f}\n"
        f"  Palfinger: SGD {today['palfinger']:,.2f}\n\n"
        f"*Month to Date*\n"
        f"  Personal: SGD {mtd['personal']:,.2f}\n"
        f"  Palfinger: SGD {mtd['palfinger']:,.2f}\n"
        f"  *Total: SGD {mtd['total']:,.2f}*"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')


async def monthly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    await update.message.reply_text("_Pulling monthly report..._", parse_mode='Markdown')
    records = get_all_expenses()

    # Allow /monthly 2026-05 for a specific month
    args = context.args
    month = args[0] if args else current_month()

    report = format_monthly_report(records, month)
    # Split if too long for Telegram (4096 char limit)
    if len(report) > 4000:
        chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text(report, parse_mode='Markdown')


async def ytd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    await update.message.reply_text("_Pulling year-to-date report..._", parse_mode='Markdown')
    records = get_all_expenses()
    report = format_ytd_report(records)
    if len(report) > 4000:
        chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text(report, parse_mode='Markdown')


async def personal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    await update.message.reply_text("_Pulling Personal detail..._", parse_mode='Markdown')
    records = get_all_expenses()
    report = format_category_report(records, "Personal")
    if len(report) > 4000:
        chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text(report, parse_mode='Markdown')


async def palfinger_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auth(update): return
    await update.message.reply_text("_Pulling Palfinger detail..._", parse_mode='Markdown')
    records = get_all_expenses()
    report = format_category_report(records, "Palfinger")
    if len(report) > 4000:
        chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
        for chunk in chunks:
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
