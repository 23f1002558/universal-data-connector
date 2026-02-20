# Function-Calling LLM — Weather / News / Currency (end-to-end)

## What this project does
- Exposes a single `/chat` endpoint.
- The LLM (OpenAI model) can ask to call one of three allowed functions:
  - `get_weather_for_date(city, date)` — weather for a date (YYYY-MM-DD).
  - `get_news_for_city(city, page_size)` — recent news mentioning the city.
  - `convert_currency(amount, base, target)` — convert currencies.
- The backend executes the function locally (so secrets stay safe), logs the call to SQLite, then asks the model for a final natural-language reply.
<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/3be5da54-1d18-46b0-9e7e-7fce6849ea1a" />
