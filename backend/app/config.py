from pydantic import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENWEATHER_API_KEY: str | None = None
    NEWSAPI_KEY: str | None = None
    FUNCTION_LOG_DB: str = "./function_calls.db"

    class Config:
        env_file = "../../.env"

settings = Settings()
