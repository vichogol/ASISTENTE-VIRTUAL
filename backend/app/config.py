from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    freellmapi_base_url: str = "http://localhost:3001/v1"
    freellmapi_api_key: str = ""
    freellmapi_model: str = "auto"

    chroma_path: str = "../data/processed/chroma"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    turnstile_enabled: bool = False
    turnstile_secret_key: str = ""

    rate_limit: str = "30/minute"
    cors_origins: str = "http://localhost:5173"

    top_k: int = 5
    faq_path: str = ""
    semantic_search: bool = False
    ai_summary_enabled: bool = False
    learning_enabled: bool = True
    learning_path: str = ""


settings = Settings()
