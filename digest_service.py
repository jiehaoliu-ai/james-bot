from datetime import datetime
import pytz
from telegram import Bot

from settings import ALLOWED_USER_ID, TIMEZONE
from fitness_service import format_fitness_digest_line
from sheets_service import (
    get_open_todos, get_expenses_mtd, get_expenses_today,
    get_reminders_today, get_completed_today
)
from calendar_service import get_todays_events

SGT = pytz.timezone(TIMEZONE)

REFLECTION_PROMPTS_MORNING = [
    "What's the one thing that would make today a win?",
    "What's your biggest priority today — and what might get in the way?",
    "Who do you need to show up for today?",
    "What would you regret NOT doing today?",
    "What assumption are you carrying into today that might be wrong?",
    "Where do you need to push harder, and where do you need to let go?",
    "What's one thing you've been avoiding that needs attention today?",
]

REFLECTION_PROMPTS_EVENING = [
    "What actually happened vs what you planned?",
    "What's one thing that went better than expected?",
    "What's the one thing you'd do differently?",
    "What's sitting unresolved that needs attention tomorrow?",
    "Any insight worth archiving from today?",
    "What drained you today — and what gave you energy?",
    "Did you move the needle on what actually matters?",
]


def get_morning_prompt() -> str:
    day = datetime.now(SGT).weekday()
    return REFLECTION_PROMPTS_MORNING[day % len(REFLECTION_PROMPTS_MORNING)]


def get_evening_prompt() -> str:
    day = datetime.now(SGT).weekday()
    return REFLECTION_PROMPTS_EVENING[day % len(REFLECTION_PROMPTS_EVENING)]


def format_morning_digest() -> str:
    todos = get_open_todos()
    expenses = get_expenses_mtd()
    calendar = get_todays_events()
    now = datetime.now(SGT)

    lines = []
    lines.append(f"☀️ *Good morning, James.*")
    lines.append(f"_{now.strftime('%A, %d %B %Y')}_\n")

    # Todos
    lines.append(f"📋 *OPEN TO-DOS* ({todos['total']})")
    if todos['personal']:
        lines.append(f"  *Personal* ({len(todos['personal'])})")
        for t in todos['personal'][:3]:
            icon = "🔴" if t.get('priority') == 'high' else "🟡"
            lines.append(f"    {icon} {t.get('title', '')}")
        if len(todos['personal']) > 3:
            lines.append(f"    _+{len(todos['personal']) - 3} more_")
    if todos['palfinger']:
        lines.append(f"  *Palfinger* ({len(todos['palfinger'])})")
        for t in todos['palfinger'][:3]:
            icon = "🔴" if t.get('priority') == 'high' else "🟡"
            lines.append(f"    {icon} {t.get('title', '')}")
        if len(todos['palfinger']) > 3:
            lines.append(f"    _+{len(todos['palfinger']) - 3} more_")
    if todos['total'] == 0:
        lines.append("  No open todos. Clean slate.")
    lines.append("")

    # Expenses MTD
    lines.append(f"💸 *EXPENSES — {now.strftime('%B')} MTD*")
    lines.append(f"  Personal:  SGD {expenses['personal']:,.2f}")
    lines.append(f"  Palfinger: SGD {expenses['palfinger']:,.2f}")
    lines.append(f"  Total:     SGD {expenses['total']:,.2f}")
    lines.append("")

    # Calendar
    if calendar:
        lines.append(f"⏰ *TODAY'S SCHEDULE* ({len(calendar)})")
        for event in calendar:
            start = event.get('start', {}).get('dateTime', '')
            if start:
                try:
                    dt = datetime.fromisoformat(start)
                    lines.append(f"  • {dt.strftime('%I:%M %p')} — {event.get('summary', '')}")
                except:
                    pass
        lines.append("")

    # Reflection prompt
    lines.append(f"💭 *MORNING THOUGHT*")
    lines.append(f"  _{get_morning_prompt()}_")
    lines.append("")
    try:
        fitness_line = format_fitness_digest_line()
        lines.append(fitness_line)
    except:
        pass
    lines.append("")
    lines.append("_Reply naturally to log expenses, todos, thoughts, or reminders._")

    return "\n".join(lines)


def format_evening_digest() -> str:
    completed = get_completed_today()
    todos = get_open_todos()
    expenses_today = get_expenses_today()
    now = datetime.now(SGT)

    lines = []
    lines.append(f"🌙 *Evening wrap, James.*")
    lines.append(f"_{now.strftime('%A, %d %B')}_\n")

    # Completed today
    lines.append(f"✅ *COMPLETED TODAY* ({len(completed)})")
    if completed:
        for t in completed:
            lines.append(f"  • {t.get('title', '')}")
    else:
        lines.append("  None logged today.")
    lines.append("")

    # Still open
    lines.append(f"📋 *STILL OPEN* ({todos['total']})")
    if todos['personal']:
        titles = ", ".join([t.get('title', '') for t in todos['personal'][:2]])
        extra = f" +{len(todos['personal'])-2} more" if len(todos['personal']) > 2 else ""
        lines.append(f"  Personal: {titles}{extra}")
    if todos['palfinger']:
        titles = ", ".join([t.get('title', '') for t in todos['palfinger'][:2]])
        extra = f" +{len(todos['palfinger'])-2} more" if len(todos['palfinger']) > 2 else ""
        lines.append(f"  Palfinger: {titles}{extra}")
    if todos['total'] == 0:
        lines.append("  All clear.")
    lines.append("")

    # Spending today
    lines.append(f"💸 *SPENT TODAY* — SGD {expenses_today['total']:,.2f}")
    for entry in expenses_today['entries'][:5]:
        lines.append(f"  • SGD {float(entry.get('amount_sgd', 0)):,.2f} — {entry.get('description', '')} [{entry.get('category', '')}]")
    if not expenses_today['entries']:
        lines.append("  Nothing logged today.")
    lines.append("")

    # Evening reflection
    lines.append(f"📝 *EVENING REFLECTION*")
    lines.append(f"  _{get_evening_prompt()}_")
    lines.append("")
    lines.append("_Reply to log your reflection, or archive any thoughts from today._")

    return "\n".join(lines)


async def send_morning_digest(bot: Bot):
    try:
        message = format_morning_digest()
        await bot.send_message(chat_id=ALLOWED_USER_ID, text=message, parse_mode='Markdown')
    except Exception as e:
        print(f"Morning digest error: {e}")


async def send_evening_digest(bot: Bot):
    try:
        message = format_evening_digest()
        await bot.send_message(chat_id=ALLOWED_USER_ID, text=message, parse_mode='Markdown')
    except Exception as e:
        print(f"Evening digest error: {e}")
