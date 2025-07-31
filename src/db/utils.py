import hashlib
import secrets
import sqlite3
import time
from contextlib import contextmanager

from src.config import config
from src.db.expressions import DatabaseExpressions
from src.logger import dbAnyLogger, dbUsersLogger, dbActiveSessionsLogger


@contextmanager
def get_db_connection():
    """Контекстный менеджер для подключения к БД."""
    conn = sqlite3.connect(config.DB_NAME)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Создаёт таблицы пользователей и сессий, если их нет."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Таблица пользователей бота
        cursor.execute(DatabaseExpressions.INIT_USERS)
        # Таблица активных сессий бота (временно хранит данные пользователя)
        cursor.execute(DatabaseExpressions.INIT_SESSIONS)
        conn.commit()
        dbAnyLogger.info("База данных инициализирована.")

def register_bot_user(telegram_id: int, username: str, password: str) -> bool:
    """Регистрирует нового пользователя бота. Возвращает True, если успешно."""
    try:
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), (config.PASSWORD_HASH_SECRET + salt).encode('utf-8'), 100000).hex()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                DatabaseExpressions.REGISTER_BOT_USER,
                (telegram_id, username, password_hash, salt)
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError as e: # Например, дубликат telegram_id или username
        dbUsersLogger.warning(f"Ошибка регистрации пользователя {telegram_id}/{username}: {e}")
        return False

def get_user_status(telegram_id: int) -> str | None:
    """Получает статус пользователя по Telegram ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(DatabaseExpressions.GET_USER_STATUS, (telegram_id,))
        row = cursor.fetchone()
        return row[0] if row else None

def approve_user(telegram_id: int):
    """Одобряет пользователя, меняя статус на 'active'."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(DatabaseExpressions.APPROVE_USER, (telegram_id,))
        conn.commit()

def authenticate_user(username: str, password: str) -> tuple[int | None, int | None]:
    """
    Аутентифицирует пользователя по логину и паролю.
    Возвращает (telegram_id, bot_user_id) если успешно, иначе (None, None).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(DatabaseExpressions.AUTH_USER, (username,))
        row = cursor.fetchone()
        if row:
            bot_user_id, telegram_id, stored_hash, salt = row
            password_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                (config.PASSWORD_HASH_SECRET + salt).encode('utf-8'),
                100000
            ).hex()
            if secrets.compare_digest(password_hash, stored_hash): # Безопасное сравнение
                return telegram_id, bot_user_id
    return None, None

def is_user_active(telegram_id: int) -> bool:
    """Проверяет, активен ли пользователь по Telegram ID."""
    status = get_user_status(telegram_id)
    return status == 'active'

# --- Функции работы с БД (Сессии) ---
def create_session(telegram_id: int, bot_user_id: int):
    """Создаёт или обновляет сессию пользователя."""
    timestamp = time.time()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            DatabaseExpressions.CREATE_SESSION,
            (telegram_id, bot_user_id, timestamp)
        )
        conn.commit()

def get_session(telegram_id: int) -> tuple[int | None, float | None]:
    """Получает ID пользователя бота и временную метку сессии. Возвращает (bot_user_id, timestamp) или (None, None)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            DatabaseExpressions.GET_SESSION,
            (telegram_id,)
        )
        row = cursor.fetchone()
        return row if row else (None, None)

def delete_session(telegram_id: int):
    """Удаляет сессию пользователя."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(DatabaseExpressions.DELETE_SESSION, (telegram_id,))
        conn.commit()

def cleanup_expired_sessions():
    """Удаляет истёкшие сессии из БД."""
    now = time.time()
    expired_time = now - config.SESSION_TIMEOUT
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            DatabaseExpressions.CLEANUP_EXP_SESSIONS,
            (expired_time,)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        if deleted_count > 0:
            dbActiveSessionsLogger.info(f"Удалено {deleted_count} истёкших сессий.")

if __name__ == "__main__":
    init_db()