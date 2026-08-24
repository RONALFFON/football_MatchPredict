"""PostgreSQL 连接管理。业务代码不直接拼接连接参数。"""
from contextlib import contextmanager
from typing import Iterator

import psycopg2

from app.core.config import settings


class Database:
    @property
    def configured(self) -> bool:
        return bool(settings.db_host and settings.db_user and settings.db_pass)

    @property
    def connection_params(self) -> dict:
        if not self.configured:
            raise RuntimeError('数据库未配置')
        return {
            'host': settings.db_host,
            'port': settings.db_port,
            'database': settings.db_name,
            'user': settings.db_user,
            'password': settings.db_pass,
            'sslmode': settings.db_sslmode,
        }

    @contextmanager
    def connection(self) -> Iterator:
        conn = psycopg2.connect(**self.connection_params)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def healthcheck(self) -> bool:
        try:
            with self.connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT 1')
            return True
        except Exception:
            return False


database = Database()
