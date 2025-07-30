import dataclasses
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

@dataclasses.dataclass
class Loggers:
    DBSessions = logging.getLogger("Database::active_sessions")
    DBUsers = logging.getLogger("Database::bot_users")
    DBAny = logging.getLogger("Database::Any")
    Logger = logging.getLogger()
