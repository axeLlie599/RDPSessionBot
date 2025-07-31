import time

from telegram import Update
from telegram.ext import ContextTypes

from src.config import config
from src.db.utils import get_session, get_db_connection, approve_user
from src.engine import update_main_message, get_main_menu
from src.logger import logger


async def approve_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /approve <user_id> от админа."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_id = update.effective_message.message_id

    if user_id != config.ADMIN_TELEGRAM_ID:
        status_text = "❌ У вас нет прав для одобрения пользователей."
        # Отправляем ответ админу в основном сообщении
        bot_user_id, timestamp = get_session(user_id)
        is_logged_in = bot_user_id is not None and (time.time() - timestamp) < config.SESSION_TIMEOUT
        is_admin_user = (user_id == config.ADMIN_TELEGRAM_ID)
        await update_main_message(update, context, status_text, is_logged_in)
        try:
             await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
             logger.debug(f"Сообщение /approve от пользователя {user_id} удалено.")
        except Exception as e:
             logger.warning(f"Не удалось удалить сообщение /approve {message_id}: {e}")
        return

    if not context.args or not context.args[0].isdigit():
        status_text = "Используйте: `/approve <telegram_user_id>`"
        # Отправляем ответ админу в основном сообщении
        bot_user_id, timestamp = get_session(user_id)
        is_logged_in = bot_user_id is not None and (time.time() - timestamp) < config.SESSION_TIMEOUT
        is_admin_user = (user_id == config.ADMIN_TELEGRAM_ID)
        await update_main_message(update, context, status_text, is_logged_in)
        try:
             await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
             logger.debug(f"Сообщение /approve от пользователя {user_id} удалено.")
        except Exception as e:
             logger.warning(f"Не удалось удалить сообщение /approve {message_id}: {e}")
        return

    target_telegram_id = int(context.args[0])
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM bot_users WHERE telegram_id = ?", (target_telegram_id,))
        row = cursor.fetchone()

    if not row:
        status_text = f"❌ Пользователь с Telegram ID {target_telegram_id} не найден в заявках."
        # Отправляем ответ админу в основном сообщении
        bot_user_id, timestamp = get_session(user_id)
        is_logged_in = bot_user_id is not None and (time.time() - timestamp) < config.SESSION_TIMEOUT
        is_admin_user = (user_id == config.ADMIN_TELEGRAM_ID)
        await update_main_message(update, context, status_text, is_logged_in)
        try:
             await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
             logger.debug(f"Сообщение /approve от пользователя {user_id} удалено.")
        except Exception as e:
             logger.warning(f"Не удалось удалить сообщение /approve {message_id}: {e}")
        return

    current_status = row[0]
    if current_status == 'active':
        status_text = f"ℹ️ Пользователь {target_telegram_id} уже одобрен."
    elif current_status in ['pending', 'banned']:
        approve_user(target_telegram_id)
        status_text = f"✅ Пользователь {target_telegram_id} одобрен."
        try:
            # Уведомляем пользователя об одобрении (отдельным сообщением)
            await context.bot.send_message(
                chat_id=target_telegram_id,
                text="🎉 Ваша заявка одобрена! Теперь вы можете войти в бота.",
                reply_markup=get_main_menu(is_logged_in=False) # Пользователь еще не залогинен
            )
        except Exception as e:
            logger.warning(f"Не удалось уведомить пользователя {target_telegram_id} об одобрении: {e}")
    else:
        status_text = f"❌ Невозможно одобрить пользователя со статусом {current_status}."

    # Удаляем исходное сообщение пользователя
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.debug(f"Сообщение /approve от админа {user_id} удалено.")
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение /approve {message_id}: {e}")

    # Отправляем ответ админу в основном сообщении
    bot_user_id, timestamp = get_session(user_id)
    is_logged_in_admin = bot_user_id is not None and (time.time() - timestamp) < config.SESSION_TIMEOUT
    is_admin_user = (user_id == config.ADMIN_TELEGRAM_ID)
    await update_main_message(update, context, status_text, is_logged_in_admin)