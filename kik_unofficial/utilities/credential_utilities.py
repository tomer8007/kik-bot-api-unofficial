import sys
import os

from kik_unofficial.configuration import env
from typing import Tuple, Union

def random_device_id():
    return os.urandom(16).hex()

def random_android_id():
    return os.urandom(8).hex()

def get_credentials_from_env_or_prompt() -> Union[Tuple[str, str, str], None]:
    # /// ENVIRONMENT VARIABLES /// #
    # Create your own `.env` file to store the environment variables if running with Docker.
    # See `.env.example` for an example. You can also just set the environment variables manually.
    username = env.get("BOT_USERNAME", None)
    password = env.get("BOT_PASSWORD", None)
    node = env.get("BOT_NODE_JID", None)

    if not username:
        username = sys.argv[1] if len(sys.argv) > 1 else input("Username: ")

    if not password:
        password = sys.argv[2] if len(sys.argv) > 2 else input("Password: ")

    if not node:
        node = None

    return username, password, node
