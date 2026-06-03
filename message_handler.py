from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from settings import ALLOWED_USER_ID, TIMEZONE
from nlp_service import parse_message
from sheets_service import (
    add_expense, add_todo, add_thought, add_reminder,
    get_open_todos, get_expenses_mtd, get_expenses_today,
    search_thoughts, complete_todo
)
from digest_service import format_morning_digest, format_evening_digest

SGT = pytz.timezone(TIMEZONE)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text("Unauthorized.")
        return

    text = update.message.text.strip()
    now_sgt = datetime.now(SGT).isoformat()

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    parsed = await parse_message(text, now_sgt)
    intent = parsed.get("intent", "UNKNOWN")
    data = parsed.get("data", {})
    display = parsed.get("display", "")

    # ─── WRITE INTENTS — confirm before saving ───────────────
    if intent in ["EXPENSE", "TODO", "THOUGHT", "REMINDER"]:
        context.user_data["pending"] = {
            "intent": intent,
            "data": data,
            "display": display,
            "original_text": text
        }

        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
            InlineKeyboardButton("✏️ Edit", callback_data="edit"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
        ]]

        await update.message.reply_text(
            f"Got this — confirm?\n\n{display}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ─── COMPLETE TODO ───────────────────────────────────────
    elif intent == "COMPLETE_TODO":
        search_term = data.get("search_term", "")
        result = complete_todo(search_term)
        if result.get("success"):
            await update.message.reply_text(f"✅ Done: *{result['title']}*", parse_mode='Markdown')
        elif result.get("ambiguous"):
            matches = "\n".join([f"  • {m}" for m in result.get("matches", [])])
            await update.message.reply_text(f"Found multiple matches — be more specific:\n{matches}")
        else:
            await update.message.reply_text("Couldn't find a matching open todo.")

    # ─── EXPENSE QUERY ───────────────────────────────────────
    elif intent == "QUERY_EXPENSE":
        expenses = get_expenses_mtd()
        today = get_expenses_today()
        msg = (
            f"💸 *Expense Summary*\n\n"
            f"*Today*\n"
            f"  Personal: SGD {today['personal']:,.2f}\n"
            f"  Palfinger: SGD {today['palfinger']:,.2f}\n\n"
            f"*Month to Date*\n"
            f"  Personal: SGD {expenses['personal']:,.2f}\n"
            f"  Palfinger: SGD {expenses['palfinger']:,.2f}\n"
            f"  *Total: SGD {expenses['total']:,.2f}*"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')

    # ─── TODO QUERY ──────────────────────────────────────────
    elif intent == "QUERY_TODOS":
        todos = get_open_todos()
        if todos['total'] == 0:
            await update.message.reply_text("No open todos. Clean slate.")
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

    # ─── THOUGHTS QUERY ──────────────────────────────────────
    elif intent == "QUERY_THOUGHTS":
        query = data.get("search_term", text)
        results = search_thoughts(query)
        if not results:
            await update.message.reply_text(f"No thoughts found matching that.")
            return
        msg = f"💭 *Thoughts* ({len(results)})\n\n"
        for t in results[:5]:
            tags = t.get('tags', '')
            msg += f"• {t.get('content')}\n"
            if tags:
                msg += f"  _{tags}_\n"
            msg += "\n"
        await update.message.reply_text(msg, parse_mode='Markdown')

    # ─── DIGEST ──────────────────────────────────────────────
    elif intent == "DIGEST":
        hour = datetime.now(SGT).hour
        digest = format_morning_digest() if hour < 14 else format_evening_digest()
        await update.message.reply_text(digest, parse_mode='Markdown')

    # ─── REFLECTION ──────────────────────────────────────────
    elif intent == "REFLECTION":
        from sheets_service import add_reflection
        hour = datetime.now(SGT).hour
        r_type = "morning" if hour < 14 else "evening"
        add_reflection(r_type, data.get("content", text))
        await update.message.reply_text("📝 Reflection logged. ✓")

    # ─── UNKNOWN ─────────────────────────────────────────────
    else:
        await update.message.reply_text(
            "Not sure what to do with that. Try:\n\n"
            "• _spent 45 on lunch_ → expense\n"
            "• _need to finish the proposal_ → todo\n"
            "• _remind me to call John tomorrow 3pm_ → reminder\n"
            "• _interesting: systems beat tools_ → thought\n"
            "• _done with the proposal_ → complete todo\n"
            "• /digest → your summary",
            parse_mode='Markdown'
        )
