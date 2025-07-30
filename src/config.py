# --- Конфигурация ---
import dataclasses
import os
from src.utils import check_dotenv

check_dotenv("../.env")


@dataclasses.dataclass
class Config:
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    SSH_HOST = os.getenv('SSH_HOST')
    SSH_PORT = int(os.getenv('SSH_PORT', 22))
    # SSH учётка бота
    BOT_SSH_USER = os.getenv('BOT_SSH_USER')
    BOT_SSH_PASS = os.getenv('BOT_SSH_PASS')
    ADMIN_TELEGRAM_ID = int(os.getenv('ADMIN_TELEGRAM_ID'))
    PASSWORD_HASH_SECRET = os.getenv('PASSWORD_HASH_SECRET')
    # Инициализируем SESSION_TIMEOUT из .env или значением по умолчанию
    DEFAULT_SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 300)) # По умолчанию 5 минут