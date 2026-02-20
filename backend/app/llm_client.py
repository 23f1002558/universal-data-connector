import json
import requests
from typing import Optional, Dict, Any

OLLAMA_URL = "http://host.docker.internal:11434/api/chat"
MODEL_NAME = "llama3.1:8b"


def call_model(messages: list, functions: Optional[list] = None) -> Dict[str, Any]:
    """
    Calls Ollama chat API.
    If functions are provided, we include them in system prompt (manual tool calling).
    """

    if functions:
        tool_text = json.dumps(functions, indent=2)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a STRICT tool-calling assistant.\n\n"
                    "RULES (VERY IMPORTANT):\n"
                    "1) If the user asks for weather, you MUST call get_weather_for_date.\n"
                    "2) If the user asks for news, you MUST call get_news_for_city.\n"
                    "3) If the user asks for currency conversion, you MUST call convert_currency.\n"
                    "4) NEVER say 'you can use tool X'.\n"
                    "5) You must output ONLY valid JSON. No extra text.\n\n"
                    "OUTPUT FORMAT:\n"
                    "To call a tool:\n"
                    "{\"tool\":\"TOOL_NAME\",\"arguments\":{...}}\n\n"
                    "If no tool is needed:\n"
                    "{\"tool\":null,\"final\":\"...\"}\n\n"
                    "IMPORTANT DATE RULE:\n"
                    "- If user says 'today', set date to \"today\".\n"
                    "- If user says 'tomorrow', set date to \"tomorrow\".\n"
                    "- Otherwise if user gives a date, keep it as YYYY-MM-DD.\n\n"
                    "Available tools:\n"
                    f"{tool_text}\n"
                ),
            }
        ] + messages[1:]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0
        }
    }

    r = requests.post(OLLAMA_URL, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()


def extract_function_call(response: Dict[str, Any]):
    """
    Extract tool call from Ollama JSON output.
    """
    content = response["message"]["content"]

    try:
        parsed = json.loads(content)
    except Exception:
        return None

    tool = parsed.get("tool")

    if tool:
        return {"name": tool, "arguments": parsed.get("arguments", {})}

    return None
