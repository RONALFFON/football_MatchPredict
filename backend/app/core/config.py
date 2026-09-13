"""应用配置。"""
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import field_validator

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    db_host: str = ''
    db_port: int = 5432
    db_name: str = 'postgres'
    db_user: str = 'postgres'
    db_pass: str = ''
    db_sslmode: str = 'prefer'

    ai_mode: str = ''
    ai_api_key: str = ''
    ai_model: str = ''
    ai_base_url: str = ''

    jwt_secret: str = ''
    jwt_algorithm: str = 'HS256'
    jwt_expire_hours: int = 168

    business_timezone: str = 'Asia/Shanghai'
    system_admin_email: str = 'admin@matchpredict.example'
    admin_user_ids: str = ''

    @field_validator('business_timezone')
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @field_validator('system_admin_email')
    @classmethod
    def normalize_system_admin_email(cls, value: str) -> str:
        return value.strip().casefold()

    cors_origins: str = 'http://localhost:3000'

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    @property
    def ai_is_local(self) -> bool:
        return self.ai_mode.strip().lower() in {'local', 'local_url'}

    @property
    def ai_ready(self) -> bool:
        return (
            self.ai_mode.strip().lower() in {'api_key', 'local', 'local_url'}
            and bool(self.ai_client_base_url)
            and bool(self.ai_model.strip())
            and (self.ai_is_local or bool(self.ai_api_key.strip()))
        )

    @property
    def ai_client_base_url(self) -> str:
        """返回环境变量中配置的 AI 接口地址，不提供厂商默认值。"""
        return self.ai_base_url.strip()


settings = Settings()
