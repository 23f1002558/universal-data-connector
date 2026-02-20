"""
Real implementations for:
1) get_weather_for_date(city, date)  -- Uses OpenWeatherMap (current or 5-day forecast)
2) get_news_for_city(city, page_size) -- Uses NewsAPI.org
3) convert_currency(amount, base, target) -- Uses exchangerate.host (free)

Notes:
- OpenWeatherMap free tier supports current weather and 5-day / 3-hour forecast.
- For forecasts, we map the requested date to the nearest day in the 5-day forecast.
- For historical weather beyond the forecast window a paid provider or historical endpoints are needed.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
from .utils.normalizers import normalize_date, normalize_city
from .utils.normalizers import normalize_city
from .utils.normalizers import normalize_currency

import os
import requests
import json
from datetime import datetime, timezone, date as date_class, timedelta
import sqlite3

DB_PATH = os.getenv("FUNCTION_LOG_DB", "./function_calls.db")

# ---------------------------
# logging helper (sqlite)
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS function_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            function_name TEXT NOT NULL,
            arguments_json TEXT NOT NULL,
            result_json TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def log_call(function_name: str, arguments: Dict[str, Any], result: Dict[str, Any]):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO function_calls (ts_utc, function_name, arguments_json, result_json) VALUES (?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), function_name, json.dumps(arguments, ensure_ascii=False), json.dumps(result, ensure_ascii=False))
    )
    conn.commit()
    conn.close()

# ---------------------------
# Utilities
# ---------------------------
def _safe_get(d, *keys, default=None):
    for k in keys:
        if d is None:
            return default
        d = d.get(k)
    return d if d is not None else default

# ---------------------------
# 1) Weather for a particular date
# ---------------------------
def _geocode_city(city: str) -> Optional[Dict[str, Any]]:
    
    """Return {'lat':..., 'lon':..., 'name':..., 'country':...} or None"""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return None
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {"q": city, "limit": 1, "appid": api_key}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        return None
    arr = r.json()
    if not arr:
        return None
    return {"lat": arr[0]["lat"], "lon": arr[0]["lon"], "name": arr[0].get("name"), "country": arr[0].get("country")}

def get_weather_for_date(city: str, date: str) -> Dict[str, Any]:
    """
    city: city name (e.g., "Pune" or "Pune,IN")
    date: YYYY-MM-DD (ISO) — can be today or within next ~5 days (forecast). If out of range, returns an informative message.
    """
    city = normalize_city(city)
    date = normalize_date(date)

    init_db()
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        result = {"error": "Missing OPENWEATHER_API_KEY in environment"}
        log_call("get_weather_for_date", {"city": city, "date": date}, result)
        return result

    try:
        target = datetime.fromisoformat(date).date()
    except Exception as e:
        result = {"error": f"Invalid date format. Use YYYY-MM-DD. ({e})"}
        log_call("get_weather_for_date", {"city": city, "date": date}, result)
        return result

    geo = _geocode_city(city)
    if not geo:
        result = {"error": f"Could not geocode city '{city}' (check spelling) or missing API key."}
        log_call("get_weather_for_date", {"city": city, "date": date}, result)
        return result

    today = datetime.now().date()
    lat, lon = geo["lat"], geo["lon"]

    # If asking for today's weather -> use current weather endpoint
    if target == today:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            result = {"error": r.json()}
            log_call("get_weather_for_date", {"city": city, "date": date}, result)
            return result
        d = r.json()
        result = {
            "date": date,
            "city": geo.get("name"),
            "country": geo.get("country"),
            "type": "current",
            "temperature_c": _safe_get(d, "main", "temp"),
            "feels_like_c": _safe_get(d, "main", "feels_like"),
            "humidity": _safe_get(d, "main", "humidity"),
            "condition": _safe_get((_safe_get(d, "weather") or [{}])[0], "description"),
            "wind_mps": _safe_get(d, "wind", "speed"),
        }
        log_call("get_weather_for_date", {"city": city, "date": date}, result)
        return result

    # For future dates: use 5-day / 3-hour forecast. Note: this covers ~5 days only.
    # We'll request the forecast and bucket entries by date and summarize.
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
    r = requests.get(url, params=params, timeout=12)
    if r.status_code != 200:
        result = {"error": r.json()}
        log_call("get_weather_for_date", {"city": city, "date": date}, result)
        return result

    data = r.json()
    entries = data.get("list", [])
    # Group entries by date (YYYY-MM-DD)
    grouped = {}
    for e in entries:
        ts = e.get("dt")
        if ts is None:
            continue
        dts = datetime.fromtimestamp(ts, tz=timezone.utc).date()
        grouped.setdefault(dts.isoformat(), []).append(e)

    target_iso = target.isoformat()
    if target_iso not in grouped:
        result = {"error": "Requested date is outside the available forecast window (OpenWeatherMap 5-day forecast)."}
        log_call("get_weather_for_date", {"city": city, "date": date}, result)
        return result

    day_entries = grouped[target_iso]
    temps = [ _safe_get(e, "main", "temp") for e in day_entries if _safe_get(e, "main", "temp") is not None ]
    feels = [ _safe_get(e, "main", "feels_like") for e in day_entries if _safe_get(e, "main", "feels_like") is not None ]
    humid = [ _safe_get(e, "main", "humidity") for e in day_entries if _safe_get(e, "main", "humidity") is not None ]
    # choose most common description
    descs = [ (_safe_get((e.get("weather") or [{}])[0], "description") or "").lower() for e in day_entries ]
    from collections import Counter
    most_common_desc = Counter([d for d in descs if d]).most_common(1)
    cond = most_common_desc[0][0] if most_common_desc else None

    result = {
        "date": date,
        "city": geo.get("name"),
        "country": geo.get("country"),
        "type": "forecast",
        "temp_min_c": min(temps) if temps else None,
        "temp_max_c": max(temps) if temps else None,
        "temp_avg_c": sum(temps)/len(temps) if temps else None,
        "feels_like_avg_c": sum(feels)/len(feels) if feels else None,
        "humidity_avg": sum(humid)/len(humid) if humid else None,
        "condition": cond,
        "note": "Forecast derived from OpenWeatherMap 5-day/3-hour forecasts. For exact historical data use a paid historical API."
    }
    log_call("get_weather_for_date", {"city": city, "date": date}, result)
    return result

# ---------------------------
# 2) News for a particular city
# ---------------------------
def get_news_for_city(city: str, page_size: int = 5) -> Dict[str, Any]:
    city = normalize_city(city)

    init_db()
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        result = {"error": "Missing NEWSAPI_KEY in environment"}
        log_call("get_news_for_city", {"city": city, "page_size": page_size}, result)
        return result

    # Use NewsAPI 'everything' endpoint and search for the city name.
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": city,
        "pageSize": max(1, min(int(page_size), 20)),
        "sortBy": "publishedAt",
        "language": "en",
        "apiKey": api_key
    }
    r = requests.get(url, params=params, timeout=12)
    if r.status_code != 200:
        result = {"error": r.json()}
        log_call("get_news_for_city", {"city": city, "page_size": page_size}, result)
        return result

    data = r.json()
    articles = []
    for a in data.get("articles", [])[: params["pageSize"]]:
        articles.append({
            "title": a.get("title"),
            "source": (a.get("source") or {}).get("name"),
            "publishedAt": a.get("publishedAt"),
            "url": a.get("url"),
            "description": a.get("description")
        })
    result = {"city": city, "count": len(articles), "articles": articles}
    log_call("get_news_for_city", {"city": city, "page_size": page_size}, result)
    return result

# ---------------------------
# 3) Currency conversion
# ---------------------------
def convert_currency(amount: float, base: str, target: str) -> Dict[str, Any]:
    base = normalize_currency(base)
    target = normalize_currency(target)

    url = "https://api.frankfurter.app/latest"
    params = {"amount": amount, "from": base.upper(), "to": target.upper()}

    try:
        r = requests.get(url, params=params, timeout=12)
        data = r.json()
    except Exception as e:
        return {"error": f"Currency request failed: {str(e)}"}

    if r.status_code != 200:
        return {"error": data}

    converted = data["rates"][target.upper()]
    rate = converted / amount if amount else None

    return {
        "amount": amount,
        "base": base.upper(),
        "target": target.upper(),
        "converted": converted,
        "rate": rate
    }


# ---------------------------
# Registry for model
# ---------------------------
FUNCTION_REGISTRY = {
    "get_weather_for_date": {
        "callable": get_weather_for_date,
        "description": "Get weather for a city on a particular date (YYYY-MM-DD). Uses OpenWeatherMap current/forecast endpoints.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["city", "date"]
        }
    },
    "get_news_for_city": {
        "callable": get_news_for_city,
        "description": "Get recent news articles mentioning a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 20}
            },
            "required": ["city"]
        }
    },
    "convert_currency": {
        "callable": convert_currency,
        "description": "Convert amount from base currency to target currency using exchangerate.host",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "base": {"type": "string"},
                "target": {"type": "string"},
            },
            "required": ["amount", "base", "target"]
        }
    }
}

def get_model_functions():
    out = []
    for name, meta in FUNCTION_REGISTRY.items():
        out.append({
            "name": name,
            "description": meta["description"],
            "parameters": meta["parameters"]
        })
    return out

def call_function_by_name(name: str, arguments: dict):
    if name not in FUNCTION_REGISTRY:
        raise ValueError(f"Unknown function: {name}")
    fn = FUNCTION_REGISTRY[name]["callable"]
    # Basic args sanitization: ensure only expected keys passed
    params_schema = FUNCTION_REGISTRY[name]["parameters"]["properties"]
    cleaned_args = {}
    for k in params_schema.keys():
        if k in arguments:
            cleaned_args[k] = arguments[k]
    # type conversions where needed
    try:
        return fn(**cleaned_args)
    except TypeError as e:
        # likely missing or bad args
        raise
