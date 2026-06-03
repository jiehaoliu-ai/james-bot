import gspread
import json
import os
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz
from settings import (
    GOOGLE_CREDENTIALS_PATH, GOOGLE_CREDENTIALS_JSON, SPREADSHEET_ID, TIMEZONE,
    SHEET_EXPENSES, SHEET_TODOS, SHEET_THOUGHTS,
    SHEET_REFLECTIONS, SHEET_REMINDERS
)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SGT = pytz.timezone(TIMEZONE)


def get_credentials():
    if GOOGLE_CREDENTIALS_JSON:
        info = json.loads(GOOGLE_CREDENTIALS_JSON)
        return Credentials.from_service_account_info(info, scopes=SCOPES)
    return Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)


def get_client():
    creds = get_credentials()
    return gspread.authorize(creds)


def get_sheet(sheet_name: str):
    client = get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet.worksheet(sheet_name)


def now_sgt():
    return datetime.now(SGT).strftime("%Y-%m-%d %H:%M:%S")


def today_sgt():
    return datetime.now(SGT).strftime("%Y-%m-%d")


def current_month():
    return datetime.now(SGT).strftime("%Y-%m")


# ─── EXPENSES ────────────────────────────────────────────────

def add_expense(data: dict) -> bool:
    try:
        sheet = get_sheet(SHEET_EXPENSES)
        row = [
            now_sgt(),
            data.get("amount_original"),
            data.get("currency_original", "SGD"),
            data.get("amount_sgd"),
            data.get("category"),
            data.get("subcategory"),
            data.get("description"),
            current_month()
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        print(f"Error adding expense: {e}")
        return False


def get_expenses_mtd() -> dict:
    try:
        sheet = get_sheet(SHEET_EXPENSES)
        records = sheet.get_all_records()
        month = current_month()
        mtd = [r for r in records if str(r.get("month", "")) == month]
        personal = sum(float(r.get("amount_sgd", 0)) for r in mtd if r.get("category") == "Personal")
        palfinger = sum(float(r.get("amount_sgd", 0)) for r in mtd if r.get("category") == "Palfinger")
        return {
            "personal": round(personal, 2),
            "palfinger": round(palfinger, 2),
            "total": round(personal + palfinger, 2),
            "entries": mtd
        }
    except Exception as e:
        print(f"Error getting expenses MTD: {e}")
        return {"personal": 0, "palfinger": 0, "total": 0, "entries": []}


def get_expenses_today() -> dict:
    try:
        sheet = get_sheet(SHEET_EXPENSES)
        records = sheet.get_all_records()
        today = today_sgt()
        today_entries = [r for r in records if str(r.get("timestamp", "")).startswith(today)]
        personal = sum(float(r.get("amount_sgd", 0)) for r in today_entries if r.get("category") == "Personal")
        palfinger = sum(float(r.get("amount_sgd", 0)) for r in today_entries if r.get("category") == "Palfinger")
        return {
            "personal": round(personal, 2),
            "palfinger": round(palfinger, 2),
            "total": round(personal + palfinger, 2),
            "entries": today_entries
        }
    except Exception as e:
        print(f"Error getting expenses today: {e}")
        return {"personal": 0, "palfinger": 0, "total": 0, "entries": []}


# ─── TODOS ───────────────────────────────────────────────────

def add_todo(data: dict) -> bool:
    try:
        sheet = get_sheet(SHEET_TODOS)
        row = [
            now_sgt(),
            data.get("title"),
            data.get("category"),
            data.get("priority", "medium"),
            data.get("due_date", ""),
            "open",
            ""
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        print(f"Error adding todo: {e}")
        return False


def get_open_todos() -> dict:
    try:
        sheet = get_sheet(SHEET_TODOS)
        records = sheet.get_all_records()
        open_todos = [r for r in records if r.get("status") == "open"]
        personal = [t for t in open_todos if t.get("category") == "Personal"]
        palfinger = [t for t in open_todos if t.get("category") == "Palfinger"]
        return {
            "personal": personal,
            "palfinger": palfinger,
            "total": len(open_todos)
        }
    except Exception as e:
        print(f"Error getting todos: {e}")
        return {"personal": [], "palfinger": [], "total": 0}


def complete_todo(search_term: str) -> dict:
    try:
        sheet = get_sheet(SHEET_TODOS)
        records = sheet.get_all_records()
        search_lower = search_term.lower()
        matches = [
            (i + 2, r) for i, r in enumerate(records)
            if search_lower in r.get("title", "").lower() and r.get("status") == "open"
        ]
        if not matches:
            return {"success": False, "message": "No matching open todo found"}
        if len(matches) > 1:
            return {"success": False, "ambiguous": True, "matches": [m[1].get("title") for m in matches]}
        row_num, todo = matches[0]
        sheet.update_cell(row_num, 6, "completed")
        sheet.update_cell(row_num, 7, now_sgt())
        return {"success": True, "title": todo.get("title")}
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_completed_today() -> list:
    try:
        sheet = get_sheet(SHEET_TODOS)
        records = sheet.get_all_records()
        today = today_sgt()
        return [r for r in records if str(r.get("completed_at", "")).startswith(today)]
    except:
        return []


# ─── THOUGHTS ────────────────────────────────────────────────

def add_thought(data: dict) -> bool:
    try:
        sheet = get_sheet(SHEET_THOUGHTS)
        tags = ", ".join(data.get("tags", []))
        row = [now_sgt(), data.get("content"), tags, data.get("category", "Personal")]
        sheet.append_row(row)
        return True
    except Exception as e:
        print(f"Error adding thought: {e}")
        return False


def search_thoughts(query: str) -> list:
    try:
        sheet = get_sheet(SHEET_THOUGHTS)
        records = sheet.get_all_records()
        query_lower = query.lower()
        return [
            r for r in records
            if query_lower in r.get("content", "").lower()
            or query_lower in r.get("tags", "").lower()
        ]
    except:
        return []


# ─── REFLECTIONS ─────────────────────────────────────────────

def add_reflection(reflection_type: str, content: str) -> bool:
    try:
        sheet = get_sheet(SHEET_REFLECTIONS)
        records = sheet.get_all_records()
        today = today_sgt()
        today_rows = [(i + 2, r) for i, r in enumerate(records) if r.get("date") == today]
        if today_rows:
            row_num, _ = today_rows[0]
            col = 2 if reflection_type == "morning" else 3
            sheet.update_cell(row_num, col, content)
        else:
            row = [today, "", "", ""]
            if reflection_type == "morning":
                row[1] = content
            else:
                row[2] = content
            sheet.append_row(row)
        return True
    except Exception as e:
        print(f"Error adding reflection: {e}")
        return False


# ─── REMINDERS ───────────────────────────────────────────────

def add_reminder(data: dict, calendar_event_id: str = "") -> bool:
    try:
        sheet = get_sheet(SHEET_REMINDERS)
        row = [
            now_sgt(),
            data.get("title"),
            data.get("due_datetime"),
            data.get("category", "Personal"),
            calendar_event_id,
            "active"
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        print(f"Error adding reminder: {e}")
        return False


def get_reminders_today() -> list:
    try:
        sheet = get_sheet(SHEET_REMINDERS)
        records = sheet.get_all_records()
        today = today_sgt()
        return [
            r for r in records
            if str(r.get("due_datetime", "")).startswith(today)
            and r.get("status") == "active"
        ]
    except:
        return []


# ─── SETUP ───────────────────────────────────────────────────

def setup_sheets():
    client = get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    existing = [ws.title for ws in spreadsheet.worksheets()]

    sheets_config = {
        SHEET_EXPENSES: ["timestamp", "amount_original", "currency_original", "amount_sgd",
                         "category", "subcategory", "description", "month"],
        SHEET_TODOS: ["timestamp", "title", "category", "priority", "due_date", "status", "completed_at"],
        SHEET_THOUGHTS: ["timestamp", "content", "tags", "category"],
        SHEET_REFLECTIONS: ["date", "morning_note", "evening_note", "mood"],
        SHEET_REMINDERS: ["timestamp", "title", "due_datetime", "category", "calendar_event_id", "status"]
    }

    for sheet_name, headers in sheets_config.items():
        if sheet_name not in existing:
            ws = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(headers))
            ws.append_row(headers)
            print(f"✓ Created sheet: {sheet_name}")
        else:
            print(f"  Sheet already exists: {sheet_name}")
