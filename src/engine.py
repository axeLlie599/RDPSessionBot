from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.config import config
from src.logger import logger


async def update_main_message(update: Update, context: ContextTypes.DEFAULT_TYPE, status_text: str, is_logged_in: bool = False):
    """Обновляет основное сообщение бота с новым статусом и меню."""
    user_id = update.effective_user.id
    is_admin = (user_id == config.ADMIN_TELEGRAM_ID)
    menu_markup = get_main_menu(is_logged_in, is_admin)

    # Получаем chat_id и message_id из context.user_data или update
    chat_id = context.user_data.get('main_menu_chat_id') or update.effective_chat.id
    message_id = context.user_data.get('main_menu_message_id')

    # Если message_id известен, пытаемся отредактировать сообщение
    if message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=status_text,
                reply_markup=menu_markup,
                parse_mode='Markdown'
            )
            logger.debug(f"Сообщение {message_id} в чате {chat_id} отредактировано.")
            return # Успешно отредактировали, выходим
        except Exception as e:
            error_message = str(e).lower()
            if "message to edit not found" in error_message or "message_id_invalid" in error_message or "message not found" in error_message:
                logger.warning(f"Основное сообщение {message_id} не найдено. Отправляем новое.")
                # Удаляем устаревшие данные
                context.user_data.pop('main_menu_message_id', None)
                context.user_data.pop('main_menu_chat_id', None)
                message_id = None # Сбросим message_id, чтобы отправить новое сообщение
            else:
                logger.error(f"Ошибка редактирования основного сообщения {message_id}: {e}")
                # Даже при ошибке редактирования, не отправляем новое сообщение, если message_id был
                return

    # Если message_id неизвестен или сообщение не найдено, отправляем новое
    # Это происходит при первом запуске или после очистки истории
    try:
        sent_message = await context.bot.send_message(
            chat_id=chat_id,
            text=status_text,
            reply_markup=menu_markup,
            parse_mode='Markdown'
        )
        # Сохраняем ID нового сообщения
        context.user_data['main_menu_message_id'] = sent_message.message_id
        context.user_data['main_menu_chat_id'] = sent_message.chat_id
        logger.info(f"Новое основное сообщение {sent_message.message_id} отправлено в чат {sent_message.chat_id}.")
    except Exception as e:
        logger.error(f"Ошибка отправки нового основного сообщения: {e}")

# ------

def get_main_menu(is_logged_in: bool = False, is_admin: bool = False):
    keyboard = []
    if not is_logged_in:
        keyboard.append([InlineKeyboardButton("🔑 Войти", callback_data='login')])
        keyboard.append([InlineKeyboardButton("📝 Зарегистрироваться", callback_data='register')])
    else:
        keyboard.append([InlineKeyboardButton("🔄 Перезапустить сессию", callback_data='restart')])
        keyboard.append([InlineKeyboardButton("🚪 Выйти", callback_data='logout')])

    # Добавляем кнопку настроек только для администратора
    if is_admin:
        keyboard.append([InlineKeyboardButton("⚙️ Настройки", callback_data='settings')])

    return InlineKeyboardMarkup(keyboard)

#-----
def get_settings_menu():
    keyboard = [
        [InlineKeyboardButton(f"⏱️ Таймаут сессии: {config.SESSION_TIMEOUT} сек", callback_data='dummy_info')], # Информационная кнопка
        [InlineKeyboardButton("✏️ Изменить таймаут", callback_data='change_timeout')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_main')],
    ]
    return InlineKeyboardMarkup(keyboard)