from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    helm_token: str = Field(default="change-me-generate-a-long-random-string")
    helm_data_dir: Path = Field(default=Path("data"))
    helm_host: str = "0.0.0.0"
    helm_port: int = 8080
    helm_public_url: str = "http://127.0.0.1:8080"
    helm_admin_emails: str = ""
    helm_master_key: str = ""
    helm_auth_dev: bool = False
    helm_rate_limit: bool = True
    helm_catalog_warm: bool = True
    helm_cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    redis_url: str = "redis://127.0.0.1:6379/0"

    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_environment: str = "demo"
    binance_product: str = "usd_m"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    helm_llm_provider: str = "off"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5"

    google_client_id: str = ""
    google_client_secret: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    @property
    def params_path(self) -> Path:
        return self.helm_data_dir / "params.json"

    @property
    def reports_dir(self) -> Path:
        return self.helm_data_dir / "reports"

    @property
    def research_dir(self) -> Path:
        return self.helm_data_dir / "research"

    @property
    def db_path(self) -> Path:
        return self.helm_data_dir / "helm.db"

    @property
    def admin_emails(self) -> set[str]:
        return {item.strip().lower() for item in self.helm_admin_emails.split(",") if item.strip()}

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.helm_cors_origins.split(",") if item.strip()]


def get_settings() -> Settings:
    return Settings()
