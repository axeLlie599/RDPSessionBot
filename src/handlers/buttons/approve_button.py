import time

from src.config import config
from src.db.utils import get_db_connection, get_session, approve_user
from src.engine import get_main_menu
from src.logger import logger
from telegram import Update
from telegram.ext import ContextTypes


async def button_approve_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие кнопки 'Одобрить' админом."""
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id

    if admin_id != config.ADMIN_TELEGRAM_ID:
        await query.answer("❌ У вас нет прав для одобрения.", show_alert=True)
        return

    data = query.data
    if data.startswith('approve_'):
        target_telegram_id = int(data.split('_')[1])
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM bot_users WHERE telegram_id = ?", (target_telegram_id,))
            row = cursor.fetchone()

        if not row:
             status_text = f"❌ Пользователь {target_telegram_id} не найден."
             # Редактируем сообщение админа
             is_admin_logged_in = get_session(admin_id)[0] is not None and (time.time() - get_session(admin_id)[1]) < config.SESSION_TIMEOUT
             menu_markup = get_main_menu(is_logged_in=is_admin_logged_in, is_admin=True)
             await query.edit_message_text(text=status_text, reply_markup=menu_markup)
             return

        current_status = row[0]
        if current_status == 'active':
            status_text = f"ℹ️ Пользователь {target_telegram_id} уже одобрен."
        elif current_status in ['pending', 'banned']:
            approve_user(target_telegram_id)
            status_text = f"✅ Пользователь {target_telegram_id} одобрен через кнопку."
            try:
                # Уведомляем пользователя об одобрении (отдельным сообщением)
                await context.bot.send_message(
                    chat_id=target_telegram_id,
                    text="🎉 Ваша заявка одобрена! Теперь вы можете войти в бота.",
                    reply_markup=get_main_menu(is_logged_in=False) # Пользователь еще не залогинен
                )
            except Exception as e:
                 logger.warning(f"Не удалось уведомить пользователя {target_telegram_id} об одобрении через кнопку: {e}")
        else:
             status_text = f"❌ Невозможно одобрить пользователя со статусом {current_status}."

        # Редактируем сообщение админа
        is_admin_logged_in = get_session(admin_id)[0] is not None and (time.time() - get_session(admin_id)[1]) < config.SESSION_TIMEOUT
        menu_markup = get_main_menu(is_logged_in=is_admin_logged_in, is_admin=True)
        await query.edit_message_text(text=status_text, reply_markup=menu_markup)