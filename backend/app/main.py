import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from .llm_client import call_model, extract_function_call
from .functions import get_model_functions, call_function_by_name

app = FastAPI(title="Function-calling LLM demo (weather/news/convert)")


class UserMessage(BaseModel):
    user_id: str
    message: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat_endpoint(payload: UserMessage) -> Dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": (
                "You are an assistant that can call tools to fetch data. "
                "Available tools: get_weather_for_date(city, date), "
                "get_news_for_city(city, page_size), convert_currency(amount, base, target). "
                "If the user asks for weather, news or currency conversion, call the correct tool."
            ),
        },
        {"role": "user", "content": payload.message},
    ]

    model_functions = get_model_functions()

    # 1) first model call (may decide to call a tool)
    resp = call_model(messages, functions=model_functions)
    fc = extract_function_call(resp)

    if fc:
        try:
            result = call_function_by_name(fc["name"], fc["arguments"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        # Add tool call + tool output back into messages
        messages.append({"role": "assistant", "content": None, "function_call": fc})
        messages.append({"role": "function", "name": fc["name"], "content": json.dumps(result)})
        messages.append({
            "role": "system",
            "content": (
                "Now write a final user-friendly answer. "
                "Do NOT call any tool. Do NOT return JSON. "
                "Summarize the news in bullet points with title + source."
            )
        })

        # 2) second model call (final response)
        resp2 = call_model(messages)
        final_text = resp2["message"]["content"]

        return {
            "type": "function_call",
            "function": fc["name"],
            "function_args": fc["arguments"],
            "function_result": result,
            "response": final_text,
        }

    # 3) direct response
    text = resp["message"]["content"]
    return {"type": "direct", "response": text}
