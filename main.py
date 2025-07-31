
from src.bot import main
from src.logger import logger

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Something went wrong: {e}")