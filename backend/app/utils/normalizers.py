from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
import re


# -------------------------
# DATE NORMALIZER
# -------------------------
def normalize_date(date_str: str) -> str:
    """
    Converts user-friendly date inputs into ISO YYYY-MM-DD.

    Supports:
    - today
    - tomorrow
    - YYYY-MM-DD
    - DD-MM-YYYY
    - DD/MM/YYYY
    - "19 Feb 2026"
    - "Feb 19 2026"
    """

    if not date_str:
        raise ValueError("Date cannot be empty.")

    s = date_str.strip().lower()

    # today / tomorrow
    if s == "today":
        return datetime.now().date().isoformat()

    if s == "tomorrow":
        return (datetime.now().date() + timedelta(days=1)).isoformat()

    # ISO YYYY-MM-DD
    try:
        return datetime.fromisoformat(date_str).date().isoformat()
    except Exception:
        pass

    # DD-MM-YYYY or DD/MM/YYYY
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", s)
    if m:
        dd, mm, yyyy = m.groups()
        dt = datetime(int(yyyy), int(mm), int(dd))
        return dt.date().isoformat()

    # Try common text formats
    formats = [
        "%d %b %Y",   # 19 Feb 2026
        "%d %B %Y",   # 19 February 2026
        "%b %d %Y",   # Feb 19 2026
        "%B %d %Y",   # February 19 2026
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.date().isoformat()
        except Exception:
            continue

    raise ValueError("Invalid date format. Use YYYY-MM-DD or today/tomorrow.")


# -------------------------
# CITY NORMALIZER
# -------------------------
def normalize_city(city: str) -> str:
    """
    Normalizes city strings.
    """
    if not city:
        raise ValueError("City cannot be empty.")

    s = city.strip()

    # remove "city" word
    s = re.sub(r"\bcity\b", "", s, flags=re.IGNORECASE).strip()

    # Pune -> Pune,IN is optional
    return s.title()


# -------------------------
# CURRENCY NORMALIZER
# -------------------------
def normalize_currency(code: str) -> str:
    """
    Normalizes currency codes like:
    inr -> INR
    usd -> USD
    """
    if not code:
        raise ValueError("Currency cannot be empty.")
    return code.strip().upper()
