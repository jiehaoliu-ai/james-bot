import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pytz
import json
import os

from settings import TIMEZONE, SPREADSHEET_ID, GOOGLE_CREDENTIALS_PATH, GOOGLE_CREDENTIALS_JSON

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SGT = pytz.timezone(TIMEZONE)
SHEET_FITNESS = "Fitness"

WEEKLY_GOAL = 6
MONTHLY_GOAL = 24


def get_credentials():
    if GOOGLE_CREDENTIALS_JSON:
        info = json.loads(GOOGLE_CREDENTIALS_JSON)
        return Credentials.from_service_account_info(info, scopes=SCOPES)
    return Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)


def get_fitness_sheet():
    creds = get_credentials()
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    try:
        return spreadsheet.worksheet(SHEET_FITNESS)
    except:
        ws = spreadsheet.add_worksheet(title=SHEET_FITNESS, rows=2000, cols=10)
        ws.append_row([
            "timestamp", "date", "type", "activity",
            "duration_mins", "distance_km", "muscle_group",
            "intensity", "notes"
        ])
        return ws


def now_sgt():
    return datetime.now(SGT).strftime("%Y-%m-%d %H:%M:%S")


def today_sgt():
    return datetime.now(SGT).strftime("%Y-%m-%d")


def get_all_workouts() -> list:
    try:
        sheet = get_fitness_sheet()
        return sheet.get_all_records()
    except:
        return []


def add_workout(data: dict) -> bool:
    try:
        sheet = get_fitness_sheet()
        row = [
            now_sgt(),
            today_sgt(),
            data.get("type", ""),
            data.get("activity", ""),
            data.get("duration_mins", ""),
            data.get("distance_km", ""),
            data.get("muscle_group", ""),
            data.get("intensity", "moderate"),
            data.get("notes", "")
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        print(f"Error adding workout: {e}")
        return False


def get_streak(workouts: list) -> dict:
    """Calculate current streak and best streak."""
    if not workouts:
        return {"current": 0, "best": 0, "last_workout": None}

    dates = sorted(set(w.get("date", "") for w in workouts if w.get("date")), reverse=True)
    if not dates:
        return {"current": 0, "best": 0, "last_workout": None}

    today = today_sgt()
    yesterday = (datetime.now(SGT) - timedelta(days=1)).strftime("%Y-%m-%d")

    # Current streak — must include today or yesterday to be active
    current = 0
    if dates[0] in [today, yesterday]:
        check_date = datetime.strptime(dates[0], "%Y-%m-%d")
        for d in dates:
            d_dt = datetime.strptime(d, "%Y-%m-%d")
            if (check_date - d_dt).days <= current:
                current += 1
                check_date = d_dt
            else:
                break

    # Best streak ever
    best = 1
    temp = 1
    for i in range(1, len(dates)):
        d1 = datetime.strptime(dates[i-1], "%Y-%m-%d")
        d2 = datetime.strptime(dates[i], "%Y-%m-%d")
        if (d1 - d2).days == 1:
            temp += 1
            best = max(best, temp)
        else:
            temp = 1

    return {
        "current": current,
        "best": max(best, current),
        "last_workout": dates[0] if dates else None
    }


def get_weekly_stats(workouts: list) -> dict:
    """Stats for current week (Mon-Sun)."""
    now = datetime.now(SGT)
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    week_entries = [w for w in workouts if w.get("date", "") >= week_start]

    sessions = len(week_entries)
    total_mins = sum(int(w.get("duration_mins", 0) or 0) for w in week_entries)
    cardio = [w for w in week_entries if w.get("type") == "cardio"]
    strength = [w for w in week_entries if w.get("type") == "strength"]
    total_km = sum(float(w.get("distance_km", 0) or 0) for w in cardio)

    return {
        "sessions": sessions,
        "goal": WEEKLY_GOAL,
        "total_mins": total_mins,
        "total_km": round(total_km, 2),
        "cardio_sessions": len(cardio),
        "strength_sessions": len(strength),
        "entries": week_entries
    }


def get_monthly_stats(workouts: list) -> dict:
    """Stats for current month."""
    month = datetime.now(SGT).strftime("%Y-%m")
    month_entries = [w for w in workouts if str(w.get("date", "")).startswith(month)]

    sessions = len(month_entries)
    total_mins = sum(int(w.get("duration_mins", 0) or 0) for w in month_entries)
    cardio = [w for w in month_entries if w.get("type") == "cardio"]
    strength = [w for w in month_entries if w.get("type") == "strength"]
    total_km = sum(float(w.get("distance_km", 0) or 0) for w in cardio)

    return {
        "sessions": sessions,
        "goal": MONTHLY_GOAL,
        "total_mins": total_mins,
        "total_km": round(total_km, 2),
        "cardio_sessions": len(cardio),
        "strength_sessions": len(strength),
        "pct": round(sessions / MONTHLY_GOAL * 100),
        "entries": month_entries
    }


def get_last_workout(workouts: list) -> dict:
    if not workouts:
        return {}
    sorted_w = sorted(workouts, key=lambda x: x.get("timestamp", ""), reverse=True)
    return sorted_w[0]


def format_fitness_report() -> str:
    workouts = get_all_workouts()
    streak = get_streak(workouts)
    weekly = get_weekly_stats(workouts)
    monthly = get_monthly_stats(workouts)
    last = get_last_workout(workouts)

    now = datetime.now(SGT)
    lines = []
    lines.append(f"💪 *Fitness — {now.strftime('%B %Y')}*\n")

    # Streak
    fire = "🔥" if streak['current'] >= 3 else "✨" if streak['current'] > 0 else "💤"
    lines.append(f"*Streak*")
    lines.append(f"  {fire} Current: {streak['current']} days")
    lines.append(f"  🏆 Best: {streak['best']} days")
    lines.append("")

    # Weekly
    week_pct = streak['current']
    week_bar = _progress_bar(weekly['sessions'], weekly['goal'])
    status = "✅" if weekly['sessions'] >= weekly['goal'] else "🎯"
    lines.append(f"*This Week* {status}")
    lines.append(f"  {week_bar} {weekly['sessions']}/{weekly['goal']} sessions")
    if weekly['total_mins'] > 0:
        lines.append(f"  ⏱ {weekly['total_mins']} mins total")
    if weekly['total_km'] > 0:
        lines.append(f"  🏃 {weekly['total_km']} km on treadmill")
    if weekly['cardio_sessions']:
        lines.append(f"  Cardio: {weekly['cardio_sessions']} | Strength: {weekly['strength_sessions']}")
    lines.append("")

    # Monthly
    month_bar = _progress_bar(monthly['sessions'], monthly['goal'])
    m_status = "✅" if monthly['sessions'] >= monthly['goal'] else "🎯"
    lines.append(f"*{now.strftime('%B')} {m_status}*")
    lines.append(f"  {month_bar} {monthly['sessions']}/{monthly['goal']} sessions ({monthly['pct']}%)")
    lines.append(f"  ⏱ {monthly['total_mins']} mins | 🏃 {monthly['total_km']} km")
    lines.append(f"  Cardio: {monthly['cardio_sessions']} | Strength: {monthly['strength_sessions']}")
    lines.append("")

    # Last workout
    if last:
        last_date = last.get("date", "")
        last_type = last.get("activity", last.get("type", ""))
        last_dur = last.get("duration_mins", "")
        last_km = last.get("distance_km", "")
        last_str = f"{last_type}"
        if last_dur:
            last_str += f" / {last_dur} min"
        if last_km:
            last_str += f" / {last_km} km"
        lines.append(f"*Last Workout*")
        lines.append(f"  {last_date} — {last_str}")
        lines.append("")

    # Nudge
    nudge = _get_nudge(workouts, weekly, streak)
    if nudge:
        lines.append(f"_{nudge}_")

    return "\n".join(lines)


def format_fitness_digest_line() -> str:
    """Two-liner for morning digest."""
    workouts = get_all_workouts()
    streak = get_streak(workouts)
    weekly = get_weekly_stats(workouts)
    monthly = get_monthly_stats(workouts)

    fire = "🔥" if streak['current'] >= 3 else "✨" if streak['current'] > 0 else "💤"
    line1 = f"💪 {fire} Streak: {streak['current']}d | Week: {weekly['sessions']}/{weekly['goal']} | Month: {monthly['sessions']}/{monthly['goal']}"

    last = get_last_workout(workouts)
    if last and last.get("date") == today_sgt():
        line2 = f"   ✅ Already worked out today"
    elif last:
        last_str = last.get("activity", "workout")
        line2 = f"   Last: {last.get('date', '')} — {last_str}"
    else:
        line2 = f"   No workouts logged yet"

    return f"{line1}\n{line2}"


def _progress_bar(current: int, goal: int, length: int = 8) -> str:
    filled = min(int(current / goal * length), length)
    return "█" * filled + "░" * (length - filled)


def _get_nudge(workouts: list, weekly: dict, streak: dict) -> str:
    now = datetime.now(SGT)
    today = today_sgt()

    worked_today = any(w.get("date") == today for w in workouts)
    if worked_today:
        return "Great work today. Rest well tonight. 💪"

    if streak['current'] == 0:
        return "No active streak. Today's a good day to start one."

    # Check last strength session
    strength_dates = sorted(
        [w.get("date") for w in workouts if w.get("type") == "strength" and w.get("date")],
        reverse=True
    )
    if not strength_dates or (datetime.strptime(strength_dates[0], "%Y-%m-%d") < datetime.now(SGT) - timedelta(days=3)):
        return "Haven't done strength in 3+ days. Consider dumbbells today."

    days_left = 7 - now.weekday()
    sessions_needed = weekly['goal'] - weekly['sessions']
    if sessions_needed > 0 and days_left <= sessions_needed:
        return f"Need {sessions_needed} more sessions in {days_left} days to hit weekly goal."

    return ""
