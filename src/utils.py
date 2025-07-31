from pathlib import Path

import dotenv

from src.logger import envLogger


def check_env_file(path: Path = Path(".env"), init_env: bool = True) -> bool:
    """
    This function check if env exists
    You can put init_env to False to disable initialization after
    """
    if Path.exists(path):
        dotenv.load_dotenv(path) if init_env else None
        return True
    envLogger.error("Environment file not loaded")
    return False