import dataclasses
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from src.logger import Loggers
from src.main import SESSION_TIMEOUT, logger

DB_NAME = os.environ.get("BOT_DBNAME", Path("../bot.db"))

@dataclasses.dataclass(frozen=True)
class DBExpressions:
    create_users_database = ('''
            CREATE TABLE IF NOT EXISTS bot_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL, -- Внутренний логин в боте
                password_hash TEXT NOT NULL, -- Хеш пароля
                salt TEXT NOT NULL, -- Соль для хеширования
                status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'active', 'banned'
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    create_sessions_database = ('''
            CREATE TABLE IF NOT EXISTS active_sessions (
                telegram_id INTEGER PRIMARY KEY,
                bot_user_id INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                FOREIGN KEY (bot_user_id) REFERENCES bot_users (id)
            )
        ''')
    register_user =\
        "INSERT INTO bot_users (telegram_id, username, password_hash, salt, status) VALUES (?, ?, ?, ?, 'pending')"
    get_user_status = "SELECT status FROM bot_users WHERE telegram_id = ?"
    approve_user = "UPDATE bot_users SET status = 'active' WHERE telegram_id = ?"
    auth_user = "SELECT id, telegram_id, password_hash, salt FROM bot_users WHERE username = ? AND status = 'active'"
    create_session = "INSERT OR REPLACE INTO active_sessions (telegram_id, bot_user_id, timestamp) VALUES (?, ?, ?)"
    get_session = "SELECT bot_user_id, timestamp FROM active_sessions WHERE telegram_id = ?"
    delete_session = "DELETE FROM active_sessions WHERE telegram_id = ?"
    cleanup_expired_sessions = "DELETE FROM active_sessions WHERE timestamp < ?"


@contextmanager
def get_db_connection():
    """Контекстный менеджер для подключения к БД."""
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn
    finally:
        conn.close()


def create_session(telegram_id: int, bot_user_id: int):
    """Создаёт или обновляет сессию пользователя."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            DBExpressions.create_session,
            (telegram_id, bot_user_id, time.time())
        )
        conn.commit()

def get_session(telegram_id: int) -> tuple[int | None, float | None]:
    """Получает ID пользователя бота и временную метку сессии. Возвращает (bot_user_id, timestamp) или (None, None)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(DBExpressions.get_session, (telegram_id,))
        row = cursor.fetchone()
        return row if row else (None, None)

def delete_session(telegram_id: int):
    """Удаляет сессию пользователя."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(DBExpressions.delete_session, (telegram_id,))
        conn.commit()

def cleanup_expired_sessions():
    """Удаляет истёкшие сессии из БД."""
    now = time.time()
    expired_time = now - SESSION_TIMEOUT
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(DBExpressions.cleanup_expired_sessions, (expired_time,))
        deleted_count = cursor.rowcount
        conn.commit()
        if deleted_count > 0:
            logger.info(f"Удалено {deleted_count} истёкших сессий.")

def init_db():
    """Создаёт таблицы пользователей и сессий, если их нет."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Таблица пользователей бота
        Loggers.DBUsers.info("Создание секции bot_users...")
        cursor.execute(DBExpressions.create_users_database)
        # Таблица активных сессий бота (временно хранит данные пользователя)
        Loggers.DBSessions.info("Создание секции active_sessions")
        cursor.execute(DBExpressions.create_sessions_database)
        conn.commit()
        Loggers.DBAny.info("База данных инициализирована.")


if __name__ == "__main__":
    init_db()