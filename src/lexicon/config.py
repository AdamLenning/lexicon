from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LEXICON_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://lexicon:lexicon@localhost:5433/lexicon"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    embedding_model: str = "voyage-3"


settings = Settings()
