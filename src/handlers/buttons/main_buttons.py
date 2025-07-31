import time
from telegram import Update
from telegram.ext import ContextTypes
from src.config import config
from src.db.utils import create_session, delete_session, get_session, cleanup_expired_sessions
from src.engine import get_settings_menu, update_main_message
from src.logger import logger


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на основные кнопки"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    is_admin = (user_id == config.ADMIN_TELEGRAM_ID)
    # Очистка истёкших сессий
    cleanup_expired_sessions()

    # Проверяем сессию пользователя
    bot_user_id, timestamp = get_session(user_id)
    is_logged_in = bot_user_id is not None and (time.time() - timestamp) < config.SESSION_TIMEOUT

    if data == 'register':
        status_text = (
            "📝 *Регистрация*\n\n"
            "Пожалуйста, введите данные для регистрации в формате:\n"
            "`/register <внутренний_логин> <пароль>`\n\n"
            "*Важно:* Этот логин/пароль будет использоваться только для входа в *этот бот* и не связан с вашей учеткой на сервере."
        )
        await update_main_message(update, context, status_text, is_logged_in=False) # После нажатия "Регистрация" пользователь точно не залогинен

    elif data == 'login':
        # Проверка, если пользователь уже залогинен (по сессии)
        if is_logged_in:
             # Обновляем таймаут
             create_session(user_id, bot_user_id)
             status_text = "✅ Вы уже вошли в систему."
             await update_main_message(update, context, status_text, is_logged_in=True)
        else:
            status_text = (
                "🔑 *Вход*\n\n"
                "Пожалуйста, введите логин и пароль в формате:\n"
                "`/login <внутренний_логин> <пароль>`"
            )
            await update_main_message(update, context, status_text, is_logged_in=False)

    elif data == 'restart':
        if not is_logged_in:
            status_text = "❌ Сначала авторизуйтесь."
            await update_main_message(update, context, status_text, is_logged_in=False)
            return
        # Обновляем таймаут
        create_session(user_id, bot_user_id)
        status_text = (
            "🔄 *Перезапуск сессии*\n\n"
            "Введите имя пользователя на сервере для перезапуска сессии:\n"
            "`/restart <имя_пользователя_на_сервере>`"
        )
        await update_main_message(update, context, status_text, is_logged_in=True)

    elif data == 'logout':
        delete_session(user_id)
        status_text = "✅ Вы вышли из системы."
        await update_main_message(update, context, status_text, is_logged_in=False) # Не залогинен

    elif data == 'settings':
        if not is_admin:
            await query.answer("❌ У вас нет прав для доступа к настройкам.", show_alert=True)
            # Обновляем основное сообщение, чтобы убрать потенциальное сообщение об ошибке
            # await update_main_message(update, context, "❌ Доступ запрещён.", is_logged_in=is_logged_in)
            return
        # Переход в меню настроек
        settings_text = f"⚙️ *Настройки бота*\n\nТекущие параметры:"
        # Получаем chat_id и message_id из context.user_data или update
        chat_id = context.user_data.get('main_menu_chat_id') or update.effective_chat.id
        message_id = context.user_data.get('main_menu_message_id') or query.message.message_id

        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=settings_text,
                parse_mode='Markdown',
                reply_markup=get_settings_menu()
            )
        except Exception as e:
             logger.error(f"Ошибка редактирования сообщения для перехода в настройки: {e}")
             # Если не удалось отредактировать, отправляем новое
             try:
                 sent_message = await context.bot.send_message(
                     chat_id=chat_id,
                     text=settings_text,
                     reply_markup=get_settings_menu(),
                     parse_mode='Markdown'
                 )
                 context.user_data['main_menu_message_id'] = sent_message.message_id
                 context.user_data['main_menu_chat_id'] = sent_message.chat_id
             except Exception as e2:
                 logger.error(f"Ошибка отправки нового сообщения настроек: {e2}")