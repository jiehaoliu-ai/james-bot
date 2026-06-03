from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from sheets_service import add_expense, add_todo, add_thought, add_reminder
from calendar_service import create_calendar_event


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data
    pending = context.user_data.get("pending")

    if not pending:
        await query.edit_message_text("Session expired. Please resend your message.")
        return

    intent = pending.get("intent")
    data = pending.get("data", {})

    # ─── CONFIRM ─────────────────────────────────────────────
    if action == "confirm":
        success = False
        response_msg = ""

        if intent == "EXPENSE":
            success = add_expense(data)
            amount_sgd = data.get("amount_sgd", 0)
            orig = data.get("amount_original")
            curr = data.get("currency_original", "SGD")
            orig_str = f" ({curr} {orig})" if curr != "SGD" else ""
            response_msg = (
                f"✅ Expense logged\n"
                f"  SGD {float(amount_sgd):,.2f}{orig_str}\n"
                f"  {data.get('category')} › {data.get('subcategory')}\n"
                f"  {data.get('description')}"
            )

        elif intent == "TODO":
            success = add_todo(data)
            response_msg = (
                f"✅ Todo added\n"
                f"  {data.get('title')}\n"
                f"  {data.get('category')} · {data.get('priority', 'medium')} priority"
            )

        elif intent == "THOUGHT":
            success = add_thought(data)
            tags = " ".join([f"#{t}" for t in data.get("tags", [])])
            response_msg = f"✅ Thought archived\n  {tags}"

        elif intent == "REMINDER":
            calendar_id = create_calendar_event(data)
            success = add_reminder(data, calendar_id)
            cal_str = " + 📅 Calendar event created" if calendar_id else ""
            response_msg = (
                f"✅ Reminder set{cal_str}\n"
                f"  {data.get('title')}\n"
                f"  {data.get('due_datetime', 'Time TBD')}"
            )

        if not success:
            response_msg = "❌ Failed to save. Check Railway logs."

        context.user_data.pop("pending", None)
        await query.edit_message_text(response_msg)

    # ─── CANCEL ──────────────────────────────────────────────
    elif action == "cancel":
        context.user_data.pop("pending", None)
        await query.edit_message_text("❌ Cancelled.")

    # ─── EDIT ────────────────────────────────────────────────
    elif action == "edit":
        if intent == "EXPENSE":
            keyboard = [
                [InlineKeyboardButton("Personal", callback_data="set_cat_Personal"),
                 InlineKeyboardButton("Palfinger", callback_data="set_cat_Palfinger")],
                [InlineKeyboardButton("↩️ Back", callback_data="back")]
            ]
        elif intent == "TODO":
            keyboard = [
                [InlineKeyboardButton("🔴 High", callback_data="set_priority_high"),
                 InlineKeyboardButton("🟡 Medium", callback_data="set_priority_medium"),
                 InlineKeyboardButton("🟢 Low", callback_data="set_priority_low")],
                [InlineKeyboardButton("Personal", callback_data="set_cat_Personal"),
                 InlineKeyboardButton("Palfinger", callback_data="set_cat_Palfinger")],
                [InlineKeyboardButton("↩️ Back", callback_data="back")]
            ]
        else:
            keyboard = [[InlineKeyboardButton("↩️ Back", callback_data="back")]]

        await query.edit_message_text(
            f"What needs changing?\n\n{pending.get('display', '')}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif action.startswith("set_cat_"):
        cat = action.replace("set_cat_", "")
        pending["data"]["category"] = cat
        context.user_data["pending"] = pending
        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ]]
        await query.edit_message_text(
            f"Category updated to *{cat}*. Confirm?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif action.startswith("set_priority_"):
        priority = action.replace("set_priority_", "")
        pending["data"]["priority"] = priority
        context.user_data["pending"] = pending
        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ]]
        await query.edit_message_text(
            f"Priority updated to *{priority}*. Confirm?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif action == "back":
        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
            InlineKeyboardButton("✏️ Edit", callback_data="edit"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
        ]]
        await query.edit_message_text(
            f"Got this — confirm?\n\n{pending.get('display', '')}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
