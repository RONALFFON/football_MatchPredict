"""应用配置。"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    db_host: str = ''
    db_port: int = 5432
    db_name: str = 'postgres'
    db_user: str = 'postgres'
    db_pass: str = ''
    db_sslmode: str = 'prefer'

    ai_api_key: str = ''
    ai_model: str = 'sensenova-6.7-flash-lite'
    ai_base_url: str = 'https://token.sensenova.cn/v1'

    jwt_secret: str = ''
    jwt_algorithm: str = 'HS256'
    jwt_expire_hours: int = 168

    cors_origins: str = 'http://localhost:3000'

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )


settings = Settings()
