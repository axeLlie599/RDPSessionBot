import paramiko

from src.config import config
from src.logger import logger


async def restart_user_session_on_server(target_username: str) -> str:
    """
    Подключается по SSH с учёткой бота и завершает сессию пользователя на сервере.
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Подключение
        ssh.connect(
            hostname=config.SSH_HOST,
            port=config.SSH_PORT,
            username=config.BOT_SSH_USER,
            password=config.BOT_SSH_PASS
        )
        # Выполняем команду поиска сессии
        _, stdout, stderr = ssh.exec_command(f'query session {target_username}')
        # Читаем вывод с правильной кодировкой для Windows (cp866 для русского)
        output = stdout.read().decode('cp866', errors='ignore').strip()
        # print(output) # Для отладки
        error = stderr.read().decode('cp866', errors='ignore').strip()
        # Логируем для отладки (можно убрать)
        logger.info(f"Вывод query session для {target_username}:\n{output}")
        if error:
            logger.warning(f"STDERR для {target_username}:\n{error}")
        # Проверка на ошибки
        if error and not output:
            ssh.close()
            return f"❌ Ошибка при поиске сессии: {error}"
        # Проверка, существует ли пользователь
        if ("Не существуют сеансы для" in output or
                "Нет пользователя" in output or
                "The session name is invalid" in output or
                "not found" in output.lower()):
            ssh.close()
            return f"ℹ️ Пользователь '{target_username}' не найден или не активен."
        # Разбор строк
        lines = output.split('\n')
        if len(lines) < 2:
            ssh.close()
            return "❌ Не удалось получить данные о сессии (неполный вывод)."
        # Берём первую строку с данными о сессии (обычно после заголовка)
        session_line = ""
        for line in lines[1:]:
            line = line.strip()
            if line and not line.startswith('-'):
                session_line = line
                break
        if not session_line:
            ssh.close()
            return "❌ Не удалось найти строку с данными о сессии."
        # Разделяем по пробелам
        parts = session_line.split()
        if len(parts) < 3:
            ssh.close()
            return f"❌ Ошибка разбора строки сессии: '{session_line}'"
        # ID сессии — третий элемент
        print(parts)
        session_id = parts[2] #0->1,1->2,2-...
        # print(parts) # Для отладки
        # Завершаем сессию
        _, stdout, stderr = ssh.exec_command(f'logoff {session_id}')
        logoff_error = stderr.read().decode('cp866', errors='ignore').strip()
        ssh.close()
        if logoff_error:
            return f"❌ Ошибка при завершении сессии: {logoff_error}"
        else:
            return f"✅ Сессия пользователя '{target_username}' (ID: {session_id}) успешно завершена."
    except Exception as e:
        logger.error(f"Ошибка SSH: {e}")
        return f"❌ Произошла ошибка: {str(e)}"