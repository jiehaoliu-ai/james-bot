import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz

from settings import GOOGLE_CREDENTIALS_PATH, GOOGLE_CREDENTIALS_JSON, GOOGLE_CALENDAR_ID, TIMEZONE

SCOPES = ['https://www.googleapis.com/auth/calendar']
SGT = pytz.timezone(TIMEZONE)


def get_credentials():
    if GOOGLE_CREDENTIALS_JSON:
        info = json.loads(GOOGLE_CREDENTIALS_JSON)
        return Credentials.from_service_account_info(info, scopes=SCOPES)
    return Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)


def get_calendar_service():
    creds = get_credentials()
    return build('calendar', 'v3', credentials=creds)


def create_calendar_event(data: dict) -> str:
    try:
        service = get_calendar_service()
        due_str = data.get("due_datetime")
        if not due_str:
            return ""
        try:
            start_dt = datetime.fromisoformat(due_str)
            if start_dt.tzinfo is None:
                start_dt = SGT.localize(start_dt)
        except:
            return ""

        end_dt = start_dt + timedelta(hours=1)

        event = {
            'summary': data.get("title", "Reminder"),
            'description': data.get("description", ""),
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': TIMEZONE},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': TIMEZONE},
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 15},
                    {'method': 'popup', 'minutes': 0},
                ],
            },
        }

        result = service.events().insert(calendarId=GOOGLE_CALENDAR_ID, body=event).execute()
        return result.get('id', '')

    except Exception as e:
        print(f"Calendar error: {e}")
        return ""


def get_todays_events() -> list:
    try:
        service = get_calendar_service()
        now = datetime.now(SGT)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)

        events_result = service.events().list(
            calendarId=GOOGLE_CALENDAR_ID,
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])
    except Exception as e:
        print(f"Calendar fetch error: {e}")
        return []
