import time

from src.config import config
from src.db.utils import get_session
from telegram import Update
from telegram.ext import ContextTypes

from src.engine import update_main_message
from src.logger import logger


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = (user_id == config.ADMIN_TELEGRAM_ID)
    # Проверяем, есть ли активная сессия
    bot_user_id, timestamp = get_session(user_id)
    is_logged_in = bot_user_id is not None and (time.time() - timestamp) < config.SESSION_TIMEOUT
    if is_logged_in:
        welcome_text = "👋 *Привет!* Вы уже вошли в систему."
    else:
        welcome_text = "👋 *Привет!* Я бот для перезапуска сессий пользователей.\n\nИспользуйте кнопки ниже для навигации."

    # Удаляем сообщение /start
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)
        logger.debug(f"Сообщение /start от пользователя {user_id} удалено.")
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение /start {update.effective_message.message_id}: {e}")

    # Отправляем основное сообщение
    await update_main_message(update, context, welcome_text, is_logged_in)