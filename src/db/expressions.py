from dataclasses import dataclass


@dataclass
class DatabaseExpressions:
    INIT_USERS = ('''
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

    INIT_SESSIONS = ('''
            CREATE TABLE IF NOT EXISTS active_sessions (
                telegram_id INTEGER PRIMARY KEY,
                bot_user_id INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                FOREIGN KEY (bot_user_id) REFERENCES bot_users (id)
            )
        ''')

    REGISTER_BOT_USER =\
        "INSERT INTO bot_users (telegram_id, username, password_hash, salt, status) VALUES (?, ?, ?, ?, 'pending')"
    GET_USER_STATUS =\
        "SELECT status FROM bot_users WHERE telegram_id = ?"
    APPROVE_USER = "UPDATE bot_users SET status = 'active' WHERE telegram_id = ?"
    AUTH_USER =\
        "SELECT id, telegram_id, password_hash, salt FROM bot_users WHERE username = ? AND status = 'active'"
    CREATE_SESSION = "INSERT OR REPLACE INTO active_sessions (telegram_id, bot_user_id, timestamp) VALUES (?, ?, ?)"
    GET_SESSION = "SELECT bot_user_id, timestamp FROM active_sessions WHERE telegram_id = ?"
    DELETE_SESSION = "DELETE FROM active_sessions WHERE telegram_id = ?"
    CLEANUP_EXP_SESSIONS = "DELETE FROM active_sessions WHERE timestamp < ?"
