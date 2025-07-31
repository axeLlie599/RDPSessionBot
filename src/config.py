import os
from pathlib import Path

from src.logger import envLogger
from src.utils import check_env_file


class ConfigurationError(Exception):
    pass


class AppConfig:
    loaded = check_env_file()

    def __init__(self):
        if not self.loaded:
            envLogger.error("Configuration didn't load: ")
            raise ConfigurationError("Configuration file not found")

        # Обязательные переменные
        self.BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

        if not self.BOT_TOKEN:
            envLogger.error("TELEGRAM_BOT_TOKEN is required")
            raise ConfigurationError("TELEGRAM_BOT_TOKEN is required")

        try:
            self.ADMIN_TELEGRAM_ID = int(os.getenv('ADMIN_TELEGRAM_ID', 0))
            if self.ADMIN_TELEGRAM_ID == 0:
                envLogger.error("ADMIN_TELEGRAM_ID is required")
                raise ConfigurationError("ADMIN_TELEGRAM_ID is required")
        except ValueError:
            envLogger.error("ADMIN_TELEGRAM_ID must be a valid integer")
            raise ConfigurationError("ADMIN_TELEGRAM_ID must be a valid integer")

        self.PASSWORD_HASH_SECRET = os.getenv('PASSWORD_HASH_SECRET')
        if not self.PASSWORD_HASH_SECRET:
            envLogger.error("PASSWORD_HASH_SECRET is required")
            raise ConfigurationError("PASSWORD_HASH_SECRET is required")

        # Инициализация остальных атрибутов
        self.DB_NAME = Path(os.environ.get("DB_NAME", "../database.db"))
        self.SSH_HOST = os.getenv('SSH_HOST')
        self.SSH_PORT = int(os.getenv('SSH_PORT', 22))
        self.BOT_SSH_USER = os.getenv('BOT_SSH_USER')
        self.BOT_SSH_PASS = os.getenv('BOT_SSH_PASS')
        self.SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 300))

        envLogger.info("Configuration loaded")


config = AppConfig()