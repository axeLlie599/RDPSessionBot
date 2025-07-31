import asyncio
import time

from src.config import config
from src.db.utils import cleanup_expired_sessions, get_session, create_session
from src.engine import update_main_message
from src.logger import logger
from src.ssh import restart_user_session_on_server
from telegram import Update
from telegram.ext import ContextTypes


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_id = update.effective_message.message_id
    # Очистка истёкших сессий
    cleanup_expired_sessions()

    # Проверка наличия активной сессии
    bot_user_id, timestamp = get_session(user_id)
    is_logged_in = bot_user_id is not None and (time.time() - timestamp) < config.SESSION_TIMEOUT
    if not is_logged_in:
        status_text = "❌ Сначала авторизуйтесь."
        # Удаляем исходное сообщение пользователя
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            logger.debug(f"Сообщение /restart от пользователя {user_id} удалено.")
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение /restart {message_id}: {e}")
        await update_main_message(update, context, status_text, is_logged_in=False)
        return

    # Обновляем таймаут сессии
    create_session(user_id, bot_user_id)

    if not context.args:
        status_text = (
            "🔄 *Перезапуск сессии*\n\n"
            "Пожалуйста, укажите имя пользователя на сервере:\n"
            "`/restart <имя_пользователя_на_сервере>`"
        )
        # Удаляем исходное сообщение пользователя
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            logger.debug(f"Сообщение /restart от пользователя {user_id} удалено.")
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение /restart {message_id}: {e}")
        await update_main_message(update, context, status_text, is_logged_in=True)
        return

    target_username = context.args[0].strip()

    # Отправляем промежуточный статус "обрабатывается" как временное сообщение
    # Это отдельное сообщение, не основное.
    try:
        status_message = await update.message.reply_text(f"🔄 Перезапускаю сессию для '{target_username}' на сервере...")
    except Exception as e:
        logger.error(f"Ошибка отправки временного сообщения статуса: {e}")
        status_message = None

    # Выполняем SSH в отдельном потоке
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda username: asyncio.run(restart_user_session_on_server(username)),
        target_username
    )

    # Редактируем временное сообщение с результатом
    if status_message:
        try:
            # Редактируем временное сообщение
            await status_message.edit_text(result)
            # Удаляем временное сообщение после небольшой задержки (опционально)
            # await asyncio.sleep(5)
            # await context.bot.delete_message(chat_id=status_message.chat_id, message_id=status_message.message_id)
        except Exception as e:
            logger.error(f"Ошибка редактирования временного сообщения статуса: {e}")

    # Обновляем основное сообщение с результатом или информацией о следующем шаге
    # Предполагаем, что пользователь захочет сделать еще что-то, показываем меню.
    await update_main_message(update, context, result + "\n\nВыберите следующее действие:", is_logged_in=True)

    # Удаляем исходное сообщение пользователя с командой
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Сообщение /restart от пользователя {user_id} удалено.")
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение /restart {message_id}: {e}")