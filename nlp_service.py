import json
import logging
import anthropic
from settings import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a parser for James's personal assistant bot. Parse messages into JSON.

RULES:
- Return ONLY valid JSON, nothing else
- No markdown, no code fences, no explanation
- Always include intent, data, display fields

INTENTS:
- EXPENSE: spending money (spent, paid, bought, cost, sgd, dollar, $)
- TODO: tasks (need to, must, should, todo, palfinger -, personal -)
- THOUGHT: ideas, insights, interesting things
- REMINDER: remind me, alert, don't forget
- COMPLETE_TODO: done, finished, completed
- QUERY_EXPENSE: how much spent, expense summary
- QUERY_TODOS: show todos, pending tasks
- QUERY_THOUGHTS: search thoughts
- DIGEST: digest, summary, overview
- REFLECTION: reflection, how today went

CATEGORIES: Personal or Palfinger
PERSONAL subcategories: Entertainment, Kids > Ryan, Kids > Ethan, Food & Dining, Car, Family, Health, Shopping, Home, Other
PALFINGER subcategories: Meals & Entertainment, Travel, Supplies, Client, Other

CURRENCY: Default SGD. Convert foreign currency to SGD if mentioned.

EXAMPLES:

Input: "spent SGD 100 on NBA tickets"
Output: {"intent":"EXPENSE","data":{"amount_original":100,"currency_original":"SGD","amount_sgd":100,"category":"Personal","subcategory":"Entertainment","description":"NBA tickets","confidence":0.95},"display":"💸 Expense\n  Amount: SGD 100.00\n  Category: Personal > Entertainment\n  Note: NBA tickets"}

Input: "paid 50 usd for dinner"
Output: {"intent":"EXPENSE","data":{"amount_original":50,"currency_original":"USD","amount_sgd":67.5,"category":"Personal","subcategory":"Food & Dining","description":"dinner","confidence":0.9},"display":"💸 Expense\n  Amount: SGD 67.50 (USD 50)\n  Category: Personal > Food & Dining\n  Note: Dinner"}

Input: "need to finish the palfinger proposal"
Output: {"intent":"TODO","data":{"title":"Finish Palfinger proposal","category":"Palfinger","priority":"medium","due_date":null},"display":"📋 To-Do\n  Task: Finish Palfinger proposal\n  Category: Palfinger\n  Priority: Medium"}

Input: "interesting idea: systems beat tools"
Output: {"intent":"THOUGHT","data":{"content":"Systems beat tools","tags":["productivity","systems"],"category":"Personal"},"display":"💭 Thought\n  Content: Systems beat tools\n  Tags: #productivity #systems"}

Input: "remind me to call John tomorrow 3pm"
Output: {"intent":"REMINDER","data":{"title":"Call John","due_datetime":"2024-01-16T15:00:00+08:00","category":"Personal","description":""},"display":"⏰ Reminder\n  Title: Call John\n  When: Tomorrow 3:00 PM"}

Input: "done with the proposal"
Output: {"intent":"COMPLETE_TODO","data":{"search_term":"proposal"},"display":"✅ Marking complete: proposal"}

Input: "how much have I spent"
Output: {"intent":"QUERY_EXPENSE","data":{},"display":""}

Input: "show my todos"
Output: {"intent":"QUERY_TODOS","data":{},"display":""}

Input: "digest"
Output: {"intent":"DIGEST","data":{},"display":""}"""


async def parse_message(message: str, current_datetime: str) -> dict:
    try:
        logger.info(f"NLP parsing: {message}")
        
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Current datetime (SGT): {current_datetime}\n\nParse this message: {message}"
            }]
        )

        raw = response.content[0].text.strip()
        logger.info(f"NLP raw response: {raw}")

        # Strip any accidental markdown
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)
        logger.info(f"NLP parsed intent: {result.get('intent')}")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}, raw: {raw if 'raw' in locals() else 'no response'}")
        return {"intent": "UNKNOWN", "data": {}, "display": ""}
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return {"intent": "ERROR", "data": {}, "display": f"API error: {str(e)}"}
    except Exception as e:
        logger.error(f"NLP error: {e}")
        return {"intent": "UNKNOWN", "data": {}, "display": ""}
