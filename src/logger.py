import logging
import inspect


class DetailedFormatter(logging.Formatter):
    def format(self, record):
        # Получаем информацию о вызывающем коде
        frame = inspect.currentframe()
        try:
            # Поднимаемся по стеку до места вызова логгера
            for _ in range(8):  # Примерное количество уровней до вызова логгера
                frame = frame.f_back
                if frame and 'logging' not in frame.f_code.co_filename:
                    break

            if frame:
                # Пытаемся определить класс и метод
                local_vars = frame.f_locals
                if 'self' in local_vars:
                    class_name = local_vars['self'].__class__.__name__
                    record.classPrefix = f'{class_name}.'
                else:
                    record.classPrefix = ''
            else:
                record.classPrefix = ''
        except:
            record.classPrefix = ''
        finally:
            del frame

        return super().format(record)


# Настройка логгера
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = DetailedFormatter(
    '%(asctime)s - %(levelname)s::%(name)s - %(filename)s:%(lineno)d - %(classPrefix)s%(funcName)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

dbActiveSessionsLogger = logging.getLogger("DB_ACTIVE_SESSIONS")
dbUsersLogger = logging.getLogger("DB_USERS")
dbAnyLogger = logging.getLogger("DB")
envLogger = logging.getLogger("ENV")
commandLogger = logging.getLogger("COMMAND_ACTIONS")

