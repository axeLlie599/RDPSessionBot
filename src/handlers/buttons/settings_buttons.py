import time

from telegram import Update
from telegram.ext import ContextTypes

from src.config import config
from src.db.utils import get_session
from src.engine import get_settings_menu, get_main_menu
from src.logger import logger


async def settings_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки внутри меню настроек"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id != config.ADMIN_TELEGRAM_ID:
        await query.answer("❌ У вас нет прав.", show_alert=True)
        return

    data = query.data

    if data == 'change_timeout':
        # Предлагаем ввести новое значение
        instruction_text = (
            f"⏱️ *Изменение таймаута сессии*\n\n"
            f"Текущее значение: `{config.SESSION_TIMEOUT}` секунд.\n"
            f"Введите новое значение в секундах командой:\n"
            f"`/set_timeout <значение>`"
        )
        # Получаем chat_id и message_id из context.user_data или update
        chat_id = context.user_data.get('main_menu_chat_id') or update.effective_chat.id
        message_id = context.user_data.get('main_menu_message_id') or query.message.message_id

        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=instruction_text,
                parse_mode='Markdown',
                reply_markup=get_settings_menu() # Можно оставить меню, чтобы пользователь мог вернуться
            )
        except Exception as e:
             logger.error(f"Ошибка редактирования сообщения для изменения таймаута: {e}")
             # Если не удалось отредактировать, отправляем новое
             try:
                 sent_message = await context.bot.send_message(
                     chat_id=chat_id,
                     text=instruction_text,
                     reply_markup=get_settings_menu(),
                     parse_mode='Markdown'
                 )
                 context.user_data['main_menu_message_id'] = sent_message.message_id
                 context.user_data['main_menu_chat_id'] = sent_message.chat_id
             except Exception as e2:
                 logger.error(f"Ошибка отправки нового сообщения изменения таймаута: {e2}")

    elif data == 'back_to_main':
        # Возврат в главное меню
        # Нужно определить статус админа и залогиненности
        bot_user_id, timestamp = get_session(user_id)
        is_logged_in = bot_user_id is not None and (time.time() - timestamp) < SESSION_TIMEOUT
        is_admin = (user_id == config.ADMIN_TELEGRAM_ID)
        main_text = "⬅️ *Главное меню*"
        if is_logged_in:
            main_text += "\n\n✅ Вы вошли в систему."
        # Получаем chat_id и message_id из context.user_data или update
        chat_id = context.user_data.get('main_menu_chat_id') or update.effective_chat.id
        message_id = context.user_data.get('main_menu_message_id') or query.message.message_id

        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=main_text,
                parse_mode='Markdown',
                reply_markup=get_main_menu(is_logged_in, is_admin)
            )
        except Exception as e:
             logger.error(f"Ошибка редактирования сообщения для возврата в главное меню: {e}")
             # Если не удалось отредактировать, отправляем новое
             try:
                 sent_message = await context.bot.send_message(
                     chat_id=chat_id,
                     text=main_text,
                     reply_markup=get_main_menu(is_logged_in, is_admin),
                     parse_mode='Markdown'
                 )
                 context.user_data['main_menu_message_id'] = sent_message.message_id
                 context.user_data['main_menu_chat_id'] = sent_message.chat_id
             except Exception as e2:
                 logger.error(f"Ошибка отправки нового сообщения главного меню: {e2}")

    elif data == 'dummy_info':
        # Информационная кнопка, ничего не делает
        await query.answer("Это информационное поле.", show_alert=False)