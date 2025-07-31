from src.config import config
from src.db.expressions import DatabaseExpressions
from src.db.utils import get_db_connection, register_bot_user
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.engine import update_main_message
from src.logger import logger


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_id = update.effective_message.message_id

    # Проверка, не зарегистрирован ли уже пользователь
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(DatabaseExpressions.GET_USER_STATUS, (user_id,))
        existing_user = cursor.fetchone()

    if existing_user:
        status = existing_user[0]
        if status == 'active':
            status_text = "✅ Вы уже зарегистрированы и одобрены."
        elif status == 'pending':
            status_text = "⏳ Ваша заявка на регистрацию ожидает одобрения администратора."
        else: # banned
             status_text = "ℹ️ Ваша регистрация заблокирована."
        # Удаляем исходное сообщение пользователя
        try:
             await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
             logger.debug(f"Сообщение /register от пользователя {user_id} удалено.")
        except Exception as e:
             logger.warning(f"Не удалось удалить сообщение /register {message_id}: {e}")
        await update_main_message(update, context, status_text, is_logged_in=False) # Предполагаем, что при регистрации он не залогинен
        return

    if len(context.args) < 2:
        status_text = (
            "📝 *Регистрация*\n\n"
            "Используйте: `/register <внутренний_логин> <пароль>`\n\n"
            "*Важно:* Этот логин/пароль будет использоваться только для входа в *этот бот* и не связан с вашей учеткой на сервере."
        )
        # Удаляем исходное сообщение пользователя
        try:
             await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
             logger.debug(f"Сообщение /register от пользователя {user_id} удалено.")
        except Exception as e:
             logger.warning(f"Не удалось удалить сообщение /register {message_id}: {e}")
        await update_main_message(update, context, status_text, is_logged_in=False)
        return

    username = context.args[0].strip()
    password = context.args[1]

    if register_bot_user(user_id, username, password):
        status_text = "✅ Регистрация прошла успешно. Ожидайте одобрения администратора."
        # Уведомляем админа (отдельным сообщением, как и было)
        approve_button = InlineKeyboardButton("✅ Одобрить", callback_data=f'approve_{user_id}')
        keyboard = [[approve_button]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await context.bot.send_message(
                chat_id=config.ADMIN_TELEGRAM_ID,
                text=f"🔔 Новая заявка на регистрацию!\nTelegram User ID: `{user_id}`\nИмя: {update.effective_user.full_name or 'N/A'}\nUsername: @{update.effective_user.username or 'N/A'}\nВнутренний логин: `{username}`",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
             logger.error(f"Не удалось уведомить администратора: {e}")
        logger.info(f"Новая заявка на регистрацию от пользователя {user_id} (внутр. логин: {username})")
    else:
        status_text = "❌ Ошибка регистрации. Возможно, логин уже занят."

    # Удаляем исходное сообщение пользователя
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.debug(f"Сообщение /register от пользователя {user_id} удалено.")
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение /register {message_id}: {e}")

    await update_main_message(update, context, status_text, is_logged_in=False)