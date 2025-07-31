from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
)

from src.commands.admin_commands.approve import approve_user_command
from src.commands.admin_commands.set_timeout import set_timeout
from src.commands.login import login
from src.commands.logout import logout
from src.commands.register import register
from src.commands.restart import restart
from src.commands.start import start
from src.config import config
from src.db.utils import init_db
from src.handlers.buttons.approve_button import button_approve_handler
from src.handlers.buttons.main_buttons import button_handler
from src.handlers.buttons.settings_buttons import settings_button_handler
from src.logger import logger

# --- Основная функция ---
if __name__ == '__main__':
    init_db() # Инициализируем БД при запуске
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("approve", approve_user_command)) # Для админа
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CommandHandler("logout", logout))
    # Новые обработчики для настроек
    app.add_handler(CommandHandler("set_timeout", set_timeout)) # Для админа

    # Обработчики для кнопок
    # Основные кнопки (включая "Настройки")
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(login|restart|logout|register|settings)$'))
    # Кнопки внутри меню настроек
    app.add_handler(CallbackQueryHandler(settings_button_handler, pattern='^(change_timeout|back_to_main|dummy_info)$'))
    # Кнопка одобрения
    app.add_handler(CallbackQueryHandler(button_approve_handler, pattern='^approve_'))

    logger.info("Бот запущен...")
    app.run_polling()
