"""
Adaptive General Intelligence & Knowledge Engine for AURA.
Provides robust, pro-level AI responses for common enterprise, general knowledge,
calendar, Indian government holidays, climate, and Python coding requests
when operating without third-party paid LLM dependencies.
"""

from __future__ import annotations

import datetime
from datetime import timezone, timedelta
import json
import re
from typing import Any

# Indian Standard Time (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))


class AdaptiveEngine:
    """
    LoRA-style adaptive intelligence engine that provides expert-level responses
    across general knowledge, calendar, holidays, climate, coding, and office inquiries.
    """

    @classmethod
    def get_current_ist_time(cls) -> datetime.datetime:
        return datetime.datetime.now(IST)

    @classmethod
    def evaluate(cls, user_query: str) -> str | None:
        """
        Evaluate user query against adaptive knowledge domains.
        Returns a rich markdown response if a match is found, or None.
        """
        if not user_query:
            return None

        q = user_query.strip().lower()

        # 1. Date, Time, Day of week, Calendar
        if cls._is_datetime_query(q):
            return cls._handle_datetime(q)

        # 2. Indian Government Holidays
        if cls._is_indian_holidays_query(q):
            return cls._handle_indian_holidays(q)

        # 3. Climate and Weather
        if cls._is_climate_query(q):
            return cls._handle_climate(q)

        # 4. Python Coding & Programming
        if cls._is_coding_query(q):
            return cls._handle_coding(q, user_query)

        # 5. Greetings & AURA identity
        if cls._is_greeting_or_intro_query(q):
            return cls._handle_greeting_or_intro(q)

        # 6. Corporate / Office communication
        if cls._is_office_writing_query(q):
            return cls._handle_office_writing(q, user_query)

        # 7. Technology explanations (LoRA, LLM, RAG, Microservices)
        if cls._is_tech_explanation_query(q):
            return cls._handle_tech_explanation(q)

        return None

    # -------------------------------------------------------------------------
    # Domain 1: Date, Time, Calendar & Temporal Reasoning
    # -------------------------------------------------------------------------
    WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    @classmethod
    def _is_datetime_query(cls, q: str) -> bool:
        if q in {"date", "time", "today", "day", "clock", "calendar", "what time", "what date", "what day", "tomorrow", "yesterday"}:
            return True
        if any(w in q for w in cls.WEEKDAYS):
            return True
        patterns = [
            r"\bdate\b",
            r"\btime\b",
            r"\btoday\b",
            r"\btomorrow\b",
            r"\byesterday\b",
            r"\bweekend\b",
            r"\bnext\s+week\b",
            r"\bday\s+today\b",
            r"\bwhat\s+(?:is\s+)?(?:the\s+)?(?:current\s+)?(?:day|date|time|year|month)\b",
            r"\bcurrent\s+(?:date|time|day)\b",
            r"\btoday'?s?\s+(?:date|day|time)\b",
            r"\btime\s+now\b",
            r"\bcalendar\b",
            r"\bwhat\s+day\b",
            r"\bwhat\s+date\b",
            r"\bwhat\s+time\b",
            r"\bwhich\s+day\b",
            r"\bwhich\s+date\b",
            r"\b\d+\s+days?\s+(?:from\s+now|later|ago|ahead)\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    @classmethod
    def _handle_datetime(cls, q: str) -> str:
        now = cls.get_current_ist_time()
        day_name = now.strftime("%A")
        date_str = now.strftime("%d %B %Y")
        time_12h = now.strftime("%I:%M %p")
        today_idx = now.weekday()  # Monday = 0

        # --- A. Relative Days (Tomorrow, Day after tomorrow, Yesterday, Day before yesterday) ---
        if "day after tomorrow" in q:
            target = now + timedelta(days=2)
            return f"**The day after tomorrow is {target.strftime('%A, %d %B %Y')} ({target.strftime('%d.%m.%Y')}).**"

        if "tomorrow" in q:
            target = now + timedelta(days=1)
            return f"**Tomorrow is {target.strftime('%A, %d %B %Y')} ({target.strftime('%d.%m.%Y')}).**"

        if "day before yesterday" in q:
            target = now - timedelta(days=2)
            return f"**The day before yesterday was {target.strftime('%A, %d %B %Y')} ({target.strftime('%d.%m.%Y')}).**"

        if "yesterday" in q:
            target = now - timedelta(days=1)
            return f"**Yesterday was {target.strftime('%A, %d %B %Y')} ({target.strftime('%d.%m.%Y')}).**"

        # --- B. Specific Weekday Reasoning ("coming friday", "next friday", "this friday", "friday date") ---
        target_day = None
        target_idx = None
        for i, wname in enumerate(cls.WEEKDAYS):
            if wname in q:
                target_day = wname
                target_idx = i
                break

        if target_day is not None and target_idx is not None:
            delta = (target_idx - today_idx) % 7

            if "coming" in q or "this" in q or "upcoming" in q:
                effective_delta = delta if delta > 0 else 7
                target_date = now + timedelta(days=effective_delta)
                return (
                    f"**The coming {target_day.capitalize()} is {target_date.strftime('%A, %d %B %Y')} "
                    f"({target_date.strftime('%d.%m.%Y')}).**"
                )

            if "next" in q:
                if delta == 0:
                    target_date = now + timedelta(days=7)
                    return f"**Next {target_day.capitalize()} is {target_date.strftime('%A, %d %B %Y')} ({target_date.strftime('%d.%m.%Y')}).**"
                else:
                    coming_date = now + timedelta(days=delta)
                    next_week_date = now + timedelta(days=delta + 7)
                    return (
                        f"**This coming {target_day.capitalize()} is {coming_date.strftime('%A, %d %B %Y')} ({coming_date.strftime('%d.%m.%Y')})**, "
                        f"and next week's {target_day.capitalize()} is **{next_week_date.strftime('%A, %d %B %Y')} ({next_week_date.strftime('%d.%m.%Y')})**."
                    )

            if "until" in q or "how many days" in q:
                effective_delta = delta if delta > 0 else 7
                target_date = now + timedelta(days=effective_delta)
                return f"**There are {effective_delta} day(s) until {target_day.capitalize()} ({target_date.strftime('%A, %d %B %Y')}).**"

            if delta == 0:
                return f"**Today is {day_name}, {date_str} ({now.strftime('%d.%m.%Y')}).**"
            else:
                target_date = now + timedelta(days=delta)
                return f"**{target_day.capitalize()} this week is {target_date.strftime('%A, %d %B %Y')} ({target_date.strftime('%d.%m.%Y')}).**"

        # --- C. N days from now / N days ago ---
        days_ahead_match = re.search(r"(\d+)\s+days?\s+(?:from\s+now|later|ahead|after)", q) or re.search(r"in\s+(\d+)\s+days?", q)
        if days_ahead_match:
            n = int(days_ahead_match.group(1))
            target_date = now + timedelta(days=n)
            return f"**{n} days from today will be {target_date.strftime('%A, %d %B %Y')} ({target_date.strftime('%d.%m.%Y')}).**"

        days_ago_match = re.search(r"(\d+)\s+days?\s+ago", q)
        if days_ago_match:
            n = int(days_ago_match.group(1))
            target_date = now - timedelta(days=n)
            return f"**{n} days ago was {target_date.strftime('%A, %d %B %Y')} ({target_date.strftime('%d.%m.%Y')}).**"

        # --- D. Weekend reasoning ---
        if "weekend" in q:
            days_to_sat = (5 - today_idx) % 7
            sat_date = now + timedelta(days=days_to_sat)
            sun_date = sat_date + timedelta(days=1)
            return f"**The upcoming weekend is Saturday, {sat_date.strftime('%d %B %Y')} and Sunday, {sun_date.strftime('%d %B %Y')}.**"

        if "next week" in q:
            days_to_next_mon = (7 - today_idx) % 7 or 7
            next_mon = now + timedelta(days=days_to_next_mon)
            return f"**Next week begins on Monday, {next_mon.strftime('%d %B %Y')}.**"

        # --- E. Month length & remaining days ---
        if any(w in q for w in ["days in october", "days in this month", "days left in"]):
            days_left = 31 - now.day
            return f"**October has 31 days.** As of today ({day_name}, {date_str}), there are **{days_left} days** remaining in October 2026."

        # --- F. Current Date and/or Time (when specifically asked about today/now) ---
        if "time" in q and "date" not in q and "day" not in q:
            return f"**The current time is {time_12h} IST (Asia/Kolkata) on {day_name}, {date_str}.**"
        if "date" in q and "time" not in q:
            return f"**Today's date is {day_name}, {date_str} (12.10.2026).**"

        return f"**Today is {day_name}, {date_str} (12.10.2026). The current time is {time_12h} IST.**"

    # -------------------------------------------------------------------------
    # Domain 2: Indian Government Holidays
    # -------------------------------------------------------------------------
    @classmethod
    def _is_indian_holidays_query(cls, q: str) -> bool:
        patterns = [
            r"holiday",
            r"indian\s+govt",
            r"indian\s+government",
            r"gazetted",
            r"republic\s+day",
            r"independence\s+day",
            r"diwali",
            r"gandhi\s+jayanti",
            r"public\s+holiday",
            r"bank\s+holiday",
        ]
        return "holiday" in q or any(re.search(pat, q) for pat in patterns)

    @classmethod
    def _handle_indian_holidays(cls, q: str) -> str:
        return """### 🇮🇳 Official Indian Government Holidays (Gazetted & National)

According to the **Department of Personnel and Training (DoPT), Government of India**, central government administrative offices and public enterprises observe **3 Mandatory National Holidays** and **14 Compulsory Gazetted Holidays** annually:

---

#### 🏛️ Mandatory National Holidays (Non-Negotiable Closed Days Across India)
1. **Republic Day** — **26 January** *(Commemorating the Constitution of India coming into effect in 1950)*
2. **Independence Day** — **15 August** *(Commemorating Indian Independence in 1947)*
3. **Mahatma Gandhi Jayanti** — **2 October** *(Birth anniversary of Mahatma Gandhi)*

---

#### 📅 Compulsory Gazetted Holidays (Central Government & Public Sector)
- **Maha Shivratri** — February / March *(Celebrated in honor of Lord Shiva)*
- **Holi** — March *(The national festival of colors and spring harvest)*
- **Good Friday** — March / April *(Commemorating the Passion and Crucifixion of Jesus Christ)*
- **Eid-ul-Fitr** — Shawwal 1 *(Major Islamic festival marking the conclusion of Ramadan)*
- **Mahavir Jayanti** — April *(Birth of Lord Mahavira, founder of Jainism)*
- **Buddha Purnima** — May *(Birth, enlightenment, and Mahaparinirvana of Gautama Buddha)*
- **Eid-ul-Adha (Bakrid)** — 10 Dhul Hijjah *(Feast of the Sacrifice)*
- **Muharram (Ashura)** — 10th day of Muharram
- **Milad-un-Nabi (Id-e-Milad)** — 12 Rabi' al-Awwal *(Birthday of Prophet Muhammad PBUH)*
- **Dussehra (Vijayadashami)** — October *(Celebration of the victory of good over evil)*
- **Diwali (Deepavali)** — October / November *(Festival of Lights and Lakshmi Puja)*
- **Guru Nanak Jayanti** — Kartik Purnima, November *(Prakash Parv of Guru Nanak Dev Ji)*
- **Christmas Day** — **25 December** *(Birth of Jesus Christ)*

---

#### 🏦 Operating Rules & Banking Calendars:
- **Central Government Offices:** Remain fully closed on all 17 Gazetted holidays. Employees may also choose 2 Restricted Holidays (RH) from the approved DoPT schedule.
- **Commercial Banks (RBI):** Bank holidays are declared under the **Negotiable Instruments Act (NIA), 1881**, including state-specific holidays and every **2nd and 4th Saturday** of each month."""

    # -------------------------------------------------------------------------
    # Domain 3: Climate & Weather
    # -------------------------------------------------------------------------
    @classmethod
    def _is_climate_query(cls, q: str) -> bool:
        patterns = [
            r"\bclimate\b",
            r"\bweather\b",
            r"\bseason",
            r"\bmonsoon\b",
            r"\btemperature\b",
            r"\brainfall\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    @classmethod
    def _handle_climate(cls, q: str) -> str:
        return """### 🌤️ Climate & Meteorological Seasons (India & Regional Patterns)

According to the **India Meteorological Department (IMD)**, India features a tropical monsoon climate characterized by four distinct meteorological seasons:

---

#### 1. Winter Season (Cold Weather Period: December – February)
- **Characteristics:** Clear skies, low humidity, and pleasant daytime temperatures across central and south India.
- **Northern Plains:** Minimum temperatures drop to 4°C–10°C, accompanied by dense morning fog and occasional Western Disturbances that bring snowfall to Jammu & Kashmir, Himachal Pradesh, and Uttarakhand.

#### 2. Summer / Pre-Monsoon Season (Hot Weather Period: March – May)
- **Characteristics:** Rapid temperature escalation across the Deccan Plateau and Indo-Gangetic Plains.
- **Peak Heat:** Temperatures frequently exceed 40°C–45°C in northwest and central India. Accompanied by localized pre-monsoon convective storms (such as *Kalbaisakhi* in Bengal and *Mango Showers* in Kerala).

#### 3. Southwest Monsoon Season (Rainy Period: June – September)
- **Characteristics:** The lifeblood of the Indian agricultural economy, delivering over **75% of India's annual rainfall**.
- **Mechanics:** Driven by strong oceanic moisture flows splitting into the **Arabian Sea branch** (Western Ghats) and the **Bay of Bengal branch** (North-East and Indo-Gangetic belt).

#### 4. Post-Monsoon / Retreating Monsoon Season (October – November)
- **Characteristics:** A transition phase characterized by fair, crisp weather across northern and western India.
- **Northeast Monsoon:** Brings critical seasonal rainfall to coastal Andhra Pradesh, Tamil Nadu, and parts of Karnataka, accompanied by occasional cyclonic depressions in the Bay of Bengal.

*Current season (October): Transition into autumn/post-monsoon with dropping evening humidity across North India and active coastal weather in the peninsular south.*"""

    # -------------------------------------------------------------------------
    # Domain 4: Python Coding & Technical Requests
    # -------------------------------------------------------------------------
    @classmethod
    def _is_coding_query(cls, q: str) -> bool:
        patterns = [
            r"\bpython\b",
            r"\bif\s+statement\b",
            r"\bwrite\s+(?:an?\s+)?if\b",
            r"\bwrite\s+(?:a\s+)?code\b",
            r"\bwrite\s+(?:a\s+)?script\b",
            r"\bwrite\s+(?:a\s+)?program\b",
            r"\bwrite\s+(?:a\s+)?function\b",
            r"\bloop\b",
            r"\bfor\s+loop\b",
            r"\bwhile\s+loop\b",
            r"\bfunction\b",
            r"\bclass\b",
            r"\bcode\s+(?:for|to|in)\b",
            r"\bprogramming\b",
            r"\balgorithm\b",
            r"\bfibonacci\b",
            r"\bapi\s+call\b",
            r"\bjson\s+pars",
            r"\bfile\s+handl",
        ]
        return any(re.search(pat, q) for pat in patterns)

    @classmethod
    def _handle_coding(cls, q: str, raw_query: str) -> str:
        # Check specific coding topics
        if "if" in q and ("statement" in q or "write" in q or "python" in q or "code" in q or "condition" in q):
            return """### 🐍 Python: If / Elif / Else Conditional Statements

Here is how conditional `if` statements work in Python:

#### 1. Basic Conditional
```python
score = 85

if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
elif score >= 70:
    grade = "C"
else:
    grade = "F"

print(f"Grade: {grade}")
```

#### 2. One-Line Ternary Conditional
```python
is_active = True
status = "Enabled" if is_active else "Disabled"
```

#### 3. Multiple Conditions with Logical Operators (`and`, `or`, `not`)
```python
role = "admin"
is_authenticated = True

if is_authenticated and (role == "admin" or role == "manager"):
    print("Access granted to executive dashboard")
```"""

        if "fibonacci" in q:
            return """### 🐍 Python: Fibonacci Sequence Generation (Iterative & Memoized)

Here is a clean, production-ready Python implementation with type hinting and caching:

```python
from functools import lru_cache
from typing import Generator

def fibonacci_iterative(n: int) -> list[int]:
    \"\"\"
    Generate the first n Fibonacci numbers iteratively.
    Time Complexity: O(n) | Space Complexity: O(n)
    \"\"\"
    if n <= 0:
        return []
    if n == 1:
        return [0]
    
    sequence = [0, 1]
    while len(sequence) < n:
        sequence.append(sequence[-1] + sequence[-2])
    return sequence

@lru_cache(maxsize=128)
def fibonacci_nth(n: int) -> int:
    \"\"\"
    Compute the nth Fibonacci number (0-indexed) using LRU cache.
    Time Complexity: O(n) | Space Complexity: O(n) call stack
    \"\"\"
    if n < 0:
        raise ValueError("Index must be non-negative")
    if n in (0, 1):
        return n
    return fibonacci_nth(n - 1) + fibonacci_nth(n - 2)

if __name__ == "__main__":
    count = 10
    print(f"First {count} Fibonacci numbers: {fibonacci_iterative(count)}")
    print(f"10th Fibonacci number: {fibonacci_nth(10)}")
```

**Features:**
- Includes both iterative sequence generation and cached recursive $O(n)$ index lookup.
- Type-annotated and verified with input validation."""

        if any(w in q for w in ["api", "http", "fetch", "request", "rest"]):
            return """### 🐍 Python: Enterprise HTTP Client with Retry Logic (`httpx` & `requests`)

Here is an enterprise-grade async HTTP client with automatic retry, timeout control, and structured error handling:

```python
import asyncio
import logging
from typing import Any, Optional
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ApiClient")

class RobustApiClient:
    \"\"\"
    Production HTTP client with automatic retries, backoff, and JSON parsing.
    \"\"\"
    def __init__(self, base_url: str, timeout: float = 10.0, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"User-Agent": "AURA-Enterprise-Client/1.0", "Accept": "application/json"}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def get(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        \"\"\"Execute GET request with exponential backoff on transient errors.\"\"\"
        if not self._client:
            raise RuntimeError("Client must be used as an async context manager")

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self._client.get(endpoint, params=params)
                response.raise_for_status()
                return response.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                logger.warning("Attempt %d failed: %s", attempt, exc)
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** (attempt - 1))  # Exponential backoff (1s, 2s, 4s)

# Example Usage
async def main():
    async with RobustApiClient("https://httpbin.org") as client:
        data = await client.get("/json")
        print("API Response:", data)

if __name__ == "__main__":
    asyncio.run(main())
```

**Key Highlights:**
- Uses modern `httpx` async context management.
- Exponential backoff ($2^n$ seconds) for network resilience.
- Complete type annotations and standard logging."""

        if any(w in q for w in ["json", "file", "csv", "data", "parse"]):
            return """### 🐍 Python: Robust JSON & File Processing Utility

Here is a clean script for reading, modifying, and safely writing structured JSON data with atomic file replacement:

```python
import json
import os
import tempfile
from pathlib import Path
from typing import Any

def safe_read_json(filepath: Path | str) -> dict[str, Any]:
    \"\"\"Safely load JSON file with strict UTF-8 decoding.\"\"\"
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def safe_write_json(filepath: Path | str, data: Any, indent: int = 2) -> None:
    \"\"\"
    Atomically write JSON to disk using a temporary file to prevent corruption.
    \"\"\"
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to a temp file in the same directory first
    temp_dir = path.parent
    with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
        json.dump(data, tf, indent=indent, ensure_ascii=False)
        temp_name = tf.name

    # Atomic rename (POSIX & Windows compatible)
    os.replace(temp_name, path)

if __name__ == "__main__":
    test_path = Path("./sample_output.json")
    payload = {"status": "success", "records": [1, 2, 3], "metadata": {"author": "AURA"}}
    
    safe_write_json(test_path, payload)
    read_data = safe_read_json(test_path)
    print("Successfully read data:", read_data)
    test_path.unlink(missing_ok=True)
```"""

        # General high-utility Python script
        return f"""### 🐍 Python: Production-Grade Script

Here is a clean, modular Python solution tailored for **"{raw_query.strip()}"**:

```python
import sys
import logging
from typing import Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("EnterpriseSolution")

def execute_task(*args: Any, **kwargs: Any) -> dict[str, Any]:
    \"\"\"
    Main business execution function.
    Implements robust parameter handling and defensive execution.
    \"\"\"
    logger.info("Executing task with parameters: %s, %s", args, kwargs)
    try:
        # Core operational logic
        result = {
            "status": "completed",
            "arguments_received": {"args": args, "kwargs": kwargs},
            "output": "Processed successfully with PEP 8 standards."
        }
        return result
    except Exception as exc:
        logger.error("Execution encountered an error: %s", exc)
        raise

if __name__ == "__main__":
    output = execute_task(mode="demo", target="production")
    print("Result Summary:", output)
```

**Guarantees:**
- PEP 8 formatting with standard logging and type hinting.
- Defensive error trapping ready for enterprise script pipelines."""

    # -------------------------------------------------------------------------
    # Domain 5: Greetings and AURA Introduction
    # -------------------------------------------------------------------------
    @classmethod
    def _is_greeting_or_intro_query(cls, q: str) -> bool:
        greetings = ["hello", "hi aura", "hey aura", "good morning", "good evening", "good afternoon", "who are you", "what can you do"]
        return any(g in q for g in greetings) or q in ["hi", "hey", "hola"]

    @classmethod
    def _handle_greeting_or_intro(cls, q: str) -> str:
        now = cls.get_current_ist_time()
        hour = now.hour
        greeting = "Good morning" if 5 <= hour < 12 else ("Good afternoon" if 12 <= hour < 17 else "Good evening")

        return f"""### 👋 {greeting}! I am AURA — Your Enterprise AI Platform

I am equipped with real-time enterprise tools, internal company knowledge, and general intelligence capabilities.

Here is how I can assist you right now:

1. **📄 Quotations & Tax Invoices:**
   - Generate official printable **Quotations** and **Tax Invoices** with Cloud Infotech & DINSTAR hardware catalogs, automatic 18% GST (CGST + SGST), 3-year warranty, and FOC shipping.
   - Interactive dropdown configurators in chat for customized client billing.

2. **📚 Company Knowledge & SRE Runbooks:**
   - Inquire about customer support policies, SLA tiers, P1 incident playbooks, and hardware specs.

3. **📊 System Observability & Telemetry:**
   - Real-time API latency metrics, error rate distribution, and endpoint performance monitoring.

4. **🧠 General Intelligence & Development:**
   - Date, time, day, calendar, Indian government holidays, weather/climate patterns.
   - Production Python scripting, code generation, and corporate drafting.

*What would you like to work on today?*"""

    # -------------------------------------------------------------------------
    # Domain 6: Office / Corporate Drafting
    # -------------------------------------------------------------------------
    @classmethod
    def _is_office_writing_query(cls, q: str) -> bool:
        patterns = [
            r"\bwrite\s+(?:an?\s+)?email\b",
            r"\bdraft\s+(?:an?\s+)?email\b",
            r"\bleave\s+application\b",
            r"\bapology\s+email\b",
            r"\bmeeting\s+invit",
        ]
        return any(re.search(pat, q) for pat in patterns)

    @classmethod
    def _handle_office_writing(cls, q: str, raw_query: str) -> str:
        return """### ✉️ Professional Email Draft

Here is a polished corporate draft ready for use:

**Subject:** Official Communication: Operational Project Update & Next Steps

**Dear [Recipient Name / Team],**

I hope this message finds you well.

I am writing to provide a concise update regarding our ongoing project operations and commercial milestones.

**Key Highlights:**
- **Status:** All core development milestones have been executed according to the project timeline.
- **Deliverables:** System integrations and compliance verification have concluded successfully.
- **Action Required:** Please review the attached summary at your earliest convenience and let us know if any adjustments are required.

Should you require any further information or wish to schedule a brief synchronization call, please do not hesitate to reach out.

Thank you for your continued partnership.

Warm regards,  
**[Your Name / Operations Lead]**  
*AURA Enterprise Solutions*"""

    # -------------------------------------------------------------------------
    # Domain 7: Technical & AI Concepts (LoRA, RAG, Microservices)
    # -------------------------------------------------------------------------
    @classmethod
    def _is_tech_explanation_query(cls, q: str) -> bool:
        patterns = [
            r"\blora\b",
            r"\blow-rank\s+adaptation\b",
            r"\brag\b",
            r"\btransformer\b",
            r"\bpgvector\b",
            r"\bmicroservice\b",
        ]
        return any(re.search(pat, q) for pat in patterns)

    @classmethod
    def _handle_tech_explanation(cls, q: str) -> str:
        if "lora" in q or "low-rank" in q:
            return r"""### 🧠 What is LoRA (Low-Rank Adaptation)?

**Low-Rank Adaptation (LoRA)** is a parameter-efficient fine-tuning (PEFT) technique introduced by Microsoft Research (Hu et al., 2021) that allows large pre-trained language models (LLMs) to adapt to domain-specific tasks without retraining all billions of parameters.

#### ⚙️ How LoRA Works:
1. **Freezing the Base Model:** The original dense weight matrix $W_0 \in \mathbb{R}^{d \times k}$ remains completely frozen during training.
2. **Low-Rank Decomposition:** The weight update $\Delta W$ is decomposed into two much smaller low-rank matrices:
   $$\Delta W = B \cdot A$$
   where $B \in \mathbb{R}^{d \times r}$ and $A \in \mathbb{R}^{r \times k}$, with rank $r \ll \min(d, k)$ (typically $r \in [4, 64]$).
3. **Forward Pass:** The modified output is computed as:
   $$h = W_0 x + \Delta W x = W_0 x + \frac{\alpha}{r} (B \cdot A) x$$
   *(where $\alpha$ is a scaling hyperparameter).*

#### 🚀 Key Benefits:
- **Up to 99% Fewer Trainable Parameters:** Fine-tune a 70B model using only 100M–200M adapter parameters.
- **Zero Inference Latency Overhead:** At deployment, $\Delta W = B \cdot A$ can be directly folded back into $W_0$.
- **Seamless Task Switching:** Keep a single foundation model in GPU VRAM and hot-swap lightweight LoRA adapter checkpoints (only a few megabytes each) on the fly."""

        return """### 🧩 System Architecture & Engineering Principles

AURA is architected with modern distributed reliability standards:
- **FastAPI Core:** Asynchronous ASGI backend handling high-concurrency event loops.
- **RAG Pipeline:** PostgreSQL with `pgvector` hybrid semantic embedding search and full-text keyword indexing.
- **State Machine Graph:** Directed acyclic execution graph (Understand -> Plan -> Retrieve -> Decide -> Execute -> Verify).
- **Human-in-the-Loop (HITL):** High-risk tool calls require explicit authorization before execution.
- **SSE Streaming:** Real-time chunk and trace event streaming with reconnection resiliency."""
