# services/ai_service.py
from openai import OpenAI
from config.config import OPENROUTER_API_KEY, BOT_MIND_FILE
import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

def load_bot_mind() -> str:
    try:
        with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
            return json.dumps(json.load(f), ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error loading bot mind: {e}")
        return ""

async def get_ai_response(messages: List[Dict[str, str]]) -> str:
    try:
        system_prompt = load_bot_mind()
        messages_for_ai = [{"role": "system", "content": system_prompt}] + messages[-20:]
        completion = client.chat.completions.create(
            model="deepseek/deepseek-chat:free",
            messages=messages_for_ai,
            extra_headers={
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "Coffee Master Bot"
            }
        )
        ai_response = completion.choices[0].message.content
        logger.info(f"AI responded: {ai_response}")
        return ai_response
    except Exception as e:
        logger.error(f"API Error: {e}")
        return "⚠️ Произошла ошибка. Попробуйте позже."