import asyncio
import time

from telegram import Update
from telegram.ext import ContextTypes

from src.config import config
from src.db.utils import get_session
from src.engine import update_main_message, get_settings_menu
from src.logger import logger


async def set_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /set_timeout <значение> для админа"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_id = update.effective_message.message_id

    if user_id != config.ADMIN_TELEGRAM_ID:
        response_text = "❌ У вас нет прав для изменения настроек."
        # Отправляем ответ админу в основном сообщении
        bot_user_id, timestamp = get_session(user_id)
        is_logged_in = bot_user_id is not None and (time.time() - timestamp) < config.SESSION_TIMEOUT
        is_admin_user = (user_id == config.ADMIN_TELEGRAM_ID)
        await update_main_message(update, context, response_text, is_logged_in)
        try:
             await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
             logger.debug(f"Сообщение /set_timeout от пользователя {user_id} удалено.")
        except Exception as e:
             logger.warning(f"Не удалось удалить сообщение /set_timeout {message_id}: {e}")
        return

    if not context.args or not context.args[0].isdigit():
        response_text = "Используйте: `/set_timeout <значение_в_секундах>`"
        # Отправляем ответ админу в основном сообщении
        bot_user_id, timestamp = get_session(user_id)
        is_logged_in = bot_user_id is not None and (time.time() - timestamp) < config.SESSION_TIMEOUT
        is_admin_user = (user_id == config.ADMIN_TELEGRAM_ID)
        await update_main_message(update, context, response_text, is_logged_in)
        try:
             await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
             logger.debug(f"Сообщение /set_timeout от пользователя {user_id} удалено.")
        except Exception as e:
             logger.warning(f"Не удалось удалить сообщение /set_timeout {message_id}: {e}")
        return


    new_timeout = int(context.args[0])
    if new_timeout <= 0:
        response_text = "❌ Значение таймаута должно быть положительным числом."
        # Отправляем ответ админу в основном сообщении
        bot_user_id, timestamp = get_session(user_id)
        is_logged_in = bot_user_id is not None and (time.time() - timestamp) < config.SESSION_TIMEOUT
        is_admin_user = (user_id == config.ADMIN_TELEGRAM_ID)
        await update_main_message(update, context, response_text, is_logged_in)
        try:
             await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
             logger.debug(f"Сообщение /set_timeout от пользователя {user_id} удалено.")
        except Exception as e:
             logger.warning(f"Не удалось удалить сообщение /set_timeout {message_id}: {e}")
        return

    old_timeout = config.SESSION_TIMEOUT
    SESSION_TIMEOUT = new_timeout

    response_text = f"✅ Таймаут сессии изменён с {old_timeout} сек на {new_timeout} сек."

    # Удаляем сообщение с командой
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Сообщение /set_timeout от админа {user_id} удалено.")
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение /set_timeout {message_id}: {e}")

    # Отправляем подтверждение в основном сообщении и возвращаем в меню настроек
    # Получаем chat_id и message_id из context.user_data или update
    main_chat_id = context.user_data.get('main_menu_chat_id') or chat_id
    main_message_id = context.user_data.get('main_menu_message_id')

    if main_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=main_chat_id,
                message_id=main_message_id,
                text=response_text + "\n\nВозвращаюсь в настройки...",
                parse_mode='Markdown'
            )
            # Небольшая задержка перед возвратом в меню настроек
            await asyncio.sleep(1.5)
            await context.bot.edit_message_text(
                chat_id=main_chat_id,
                message_id=main_message_id,
                text="⚙️ *Настройки бота*\n\nТекущие параметры:",
                parse_mode='Markdown',
                reply_markup=get_settings_menu()
            )
        except Exception as e:
             logger.error(f"Ошибка обновления основного сообщения после set_timeout: {e}")
             # Если не удалось отредактировать, отправляем новое
             try:
                 sent_message = await context.bot.send_message(
                     chat_id=main_chat_id,
                     text="⚙️ *Настройки бота*\n\nТекущие параметры:",
                     reply_markup=get_settings_menu(),
                     parse_mode='Markdown'
                 )
                 context.user_data['main_menu_message_id'] = sent_message.message_id
                 context.user_data['main_menu_chat_id'] = sent_message.chat_id
             except Exception as e2:
                 logger.error(f"Ошибка отправки нового сообщения настроек после set_timeout: {e2}")
    else:
        # Если основное сообщение не найдено, отправляем новое
        try:
             sent_message = await context.bot.send_message(
                 chat_id=main_chat_id,
                 text="⚙️ *Настройки бота*\n\nТекущие параметры:",
                 reply_markup=get_settings_menu(),
                 parse_mode='Markdown'
             )
             context.user_data['main_menu_message_id'] = sent_message.message_id
             context.user_data['main_menu_chat_id'] = sent_message.chat_id
        except Exception as e:
             logger.error(f"Ошибка отправки нового сообщения настроек после set_timeout (нет основного): {e}")