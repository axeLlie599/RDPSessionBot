from src.db.utils import delete_session
from telegram import Update
from telegram.ext import ContextTypes
from src.engine import update_main_message
from src.logger import commandLogger


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_id = update.effective_message.message_id
    delete_session(user_id) # Удаляем сессию
    status_text = "✅ Вы вышли из системы."
    # Удаляем исходное сообщение пользователя
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        commandLogger.debug(f"Сообщение /logout от пользователя {user_id} удалено.")
    except Exception as e:
        commandLogger.warning(f"Не удалось удалить сообщение /logout {message_id}: {e}")
    await update_main_message(update, context, status_text, is_logged_in=False)