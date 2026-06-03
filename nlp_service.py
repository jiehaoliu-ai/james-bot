import json
import anthropic
from settings import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an intelligent personal assistant bot for James, operating via Telegram.
James is based in Singapore. He tracks things across two categories: Personal and Palfinger (his work).
Under Personal > Kids, he has two children: Ryan and Ethan.

Parse James's natural language messages and return structured JSON only — no other text.

INTENT TYPES:
- EXPENSE: spending, paying, buying, cost
- TODO: tasks, need to, must, should, to do
- THOUGHT: ideas, observations, quotes, insights, interesting things
- REMINDER: remind me, don't forget, alert, schedule
- COMPLETE_TODO: done, finished, completed, crossed off
- QUERY_EXPENSE: how much spent, expense summary
- QUERY_TODOS: show todos, what's pending, open tasks
- QUERY_THOUGHTS: search thoughts, find thought
- DIGEST: daily summary, digest, update
- REFLECTION: evening reflection, how today went
- UNKNOWN: cannot determine

CATEGORIES: Personal, Palfinger
PERSONAL subcategories: Kids > Ryan, Kids > Ethan, Food & Dining, Transport, Health, Entertainment, Shopping, Home, Other
PALFINGER subcategories: Meals & Entertainment, Travel, Supplies, Client, Other

CURRENCY: Default SGD. If another currency mentioned, convert to SGD using realistic rates. Always include both.

Return valid JSON only. Examples:

EXPENSE:
{"intent":"EXPENSE","data":{"amount_original":45.00,"currency_original":"SGD","amount_sgd":45.00,"category":"Personal","subcategory":"Food & Dining","description":"lunch","confidence":0.95},"display":"💸 Expense\n  Amount: SGD 45.00\n  Category: Personal > Food & Dining\n  Note: Lunch"}

TODO:
{"intent":"TODO","data":{"title":"Finish Palfinger proposal","category":"Palfinger","priority":"high","due_date":null},"display":"📋 To-Do\n  Task: Finish Palfinger proposal\n  Category: Palfinger\n  Priority: High"}

THOUGHT:
{"intent":"THOUGHT","data":{"content":"People overestimate tools and underestimate systems","tags":["productivity","systems","mindset"],"category":"Personal"},"display":"💭 Thought\n  Content: People overestimate tools and underestimate systems\n  Tags: #productivity #systems #mindset"}

REMINDER:
{"intent":"REMINDER","data":{"title":"Call John","due_datetime":"2024-01-15T15:00:00+08:00","category":"Palfinger","description":"Follow up on contract"},"display":"⏰ Reminder\n  Title: Call John\n  When: Monday 3:00 PM\n  Category: Palfinger"}

COMPLETE_TODO:
{"intent":"COMPLETE_TODO","data":{"search_term":"Palfinger proposal"},"display":"✅ Marking complete: Palfinger proposal"}

For QUERY types, DIGEST, REFLECTION, UNKNOWN:
{"intent":"QUERY_EXPENSE","data":{},"display":""}"""


async def parse_message(message: str, current_datetime: str) -> dict:
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Current datetime (SGT): {current_datetime}\n\nMessage: {message}"
            }]
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        return json.loads(raw)

    except json.JSONDecodeError:
        return {"intent": "UNKNOWN", "data": {}, "display": "I couldn't understand that. Try rephrasing?"}
    except Exception as e:
        return {"intent": "ERROR", "data": {}, "display": f"Error: {str(e)}"}


async def generate_query_response(query_type: str, data: dict, user_query: str) -> str:
    prompt = f"""James asked: "{user_query}"
Query type: {query_type}
Data: {json.dumps(data, indent=2)}
Respond directly and concisely. Show data clearly. Use SGD for all amounts. No preamble."""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()
