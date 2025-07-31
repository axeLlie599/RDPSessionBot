import time

from src.config import config
from src.db.utils import cleanup_expired_sessions, get_session, create_session, authenticate_user
from src.engine import update_main_message
from telegram import Update
from telegram.ext import ContextTypes

from src.logger import logger


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_id = update.effective_message.message_id
    # Очистка истёкших сессий
    cleanup_expired_sessions()

    # Проверка, если пользователь уже залогинен (по сессии)
    bot_user_id, timestamp = get_session(user_id)
    is_logged_in = bot_user_id is not None and (time.time() - timestamp) < config.SESSION_TIMEOUT
    if is_logged_in:
        # Обновляем таймаут
        create_session(user_id, bot_user_id)
        status_text = "✅ Вы уже вошли в систему."
        # Удаляем исходное сообщение пользователя
        try:
             await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
             logger.debug(f"Сообщение /login от пользователя {user_id} удалено.")
        except Exception as e:
             logger.warning(f"Не удалось удалить сообщение /login {message_id}: {e}")
        await update_main_message(update, context, status_text, is_logged_in=True)
        return

    if len(context.args) < 2:
        status_text = (
            "🔑 *Вход*\n\n"
            "Используйте: `/login <внутренний_логин> <пароль>`"
        )
        # Удаляем исходное сообщение пользователя
        try:
             await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
             logger.debug(f"Сообщение /login от пользователя {user_id} удалено.")
        except Exception as e:
             logger.warning(f"Не удалось удалить сообщение /login {message_id}: {e}")
        await update_main_message(update, context, status_text, is_logged_in=False)
        return

    username = context.args[0].strip()
    password = context.args[1]
    # Проверка учётных данных
    authenticated_telegram_id, authenticated_bot_user_id = authenticate_user(username, password)
    if authenticated_telegram_id is not None and authenticated_telegram_id == user_id:
        # Успешная аутентификация и проверка Telegram ID
        create_session(user_id, authenticated_bot_user_id) # Создаем или обновляем сессию
        status_text = f"✅ Вы вошли как `{username}`."
        is_logged_in = True
        logger.info(f"Пользователь {user_id} успешно вошёл как {username}")
    elif authenticated_telegram_id is not None and authenticated_telegram_id != user_id:
        # Правильный логин/пароль, но другой Telegram ID
        status_text = "❌ Эта учетная запись привязана к другому аккаунту Telegram."
        is_logged_in = False
        logger.warning(f"Попытка входа под чужой учеткой: Telegram ID {user_id} пытался войти как {username} (владелец: {authenticated_telegram_id})")
    else:
        # Неверный логин или пароль
        status_text = "❌ Неверный логин или пароль."
        is_logged_in = False
        logger.warning(f"Ошибка входа для пользователя {user_id} с логином {username}")

    # Удаляем исходное сообщение пользователя
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.debug(f"Сообщение /login от пользователя {user_id} удалено.")
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение /login {message_id}: {e}")

    await update_main_message(update, context, status_text, is_logged_in)