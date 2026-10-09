from pathlib import Path
from pydantic import Field, SecretStr, field_validator
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    aira_data_dir: Path = ROOT / 'data'
    aira_cache_dir: Path = ROOT / '.cache'
    gemini_api_key: str = ''
    gemini_live_model: str = 'gemini-3.8-live'
    gemini_standard_model: str = 'gemini-3.8-flash'
    aira_coding_model: str = ''
    aira_invoice_repair_mode: Literal['deterministic', 'agent'] = 'deterministic'
    aira_telegram_enabled: bool = False
    aira_telegram_bot_token: SecretStr = SecretStr('')
    aira_telegram_chat_id: str = ''
    gemini_image_model: str = 'gemini-2.5-flash-image'
    aira_youtube_summary_model: str = 'gemini-3.5-flash-lite'
    aira_youtube_image_model: str = 'gemini-3-pro-image'
    gemini_embedding_model: str = 'gemini-embedding-001'
    host: str = '127.0.0.1'
    port: int = 8000
    debug: bool = False
    aira_live_idle_seconds: float = Field(default=120, ge=0, le=3600)
    aira_live_max_seconds: float = Field(default=600, ge=0, le=7200)
    aira_live_max_estimated_usd: float = Field(default=0, ge=0, le=100)
    aira_live_usage_mode: Literal['per_turn', 'session_cumulative'] = 'per_turn'
    cors_origins: list[str] = ['http://127.0.0.1:5173', 'http://localhost:5173']

    @field_validator('aira_data_dir', 'aira_cache_dir')
    @classmethod
    def local_path(cls, value: Path) -> Path:
        value = value.resolve()
        if not value.is_relative_to(ROOT):
            raise ValueError('AIRA paths must remain within the E-drive workspace')
        return value

    @field_validator('host')
    @classmethod
    def loopback(cls, value: str) -> str:
        if value not in ('127.0.0.1', 'localhost', '::1'):
            raise ValueError('AIRA must bind to loopback')
        return value

settings = Settings()
