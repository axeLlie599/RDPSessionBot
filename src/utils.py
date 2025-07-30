import hashlib
import pathlib
import secrets
import sys
import uuid
from dotenv import load_dotenv

from src.main import logger


def check_dotenv(_path):
    if pathlib.Path.exists(pathlib.Path(".env")):
        logger.info(".env found, loading...")
        load_dotenv(".env")
    else:
        logger.error("File not found, please check your env file")
        sys.exit(1)

def generate_hash(_secret: str, _password, hn='sha256', _salt=None, generate_salt: bool = True, encoding = "utf8", _iterations=100000):
    generate_salt = generate_salt if _salt is None else False
    salt = secrets.token_hex(16) if generate_salt else _salt
    return hashlib.pbkdf2_hmac(hn, _password.encode(encoding), (_secret + salt).encode(encoding), _iterations).hex()


if __name__ == "__main__":
    print(generate_hash(uuid.uuid4().hex, "qwerty98078", generate_salt=True))