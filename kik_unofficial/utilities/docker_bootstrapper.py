#!/usr/bin/env python3

import logging
import sys

from examples.bootstrap_bot import BootstrapBot
from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.configuration import env

# /// ENVIRONMENT VARIABLES /// #
# Create your own `.env` file to store the environment variables for Docker.
# See `.env.example` for an example. You can also just set the environment variables manually.
BOT_USERNAME = env.get("BOT_USERNAME", None)
BOT_PASSWORD = env.get("BOT_PASSWORD", None)
BOT_NODE_JID = env.get("BOT_NODE_JID", None)


if BOT_USERNAME == "" or BOT_USERNAME is None:
    raise ValueError("BOT_USERNAME must be set in the environment variables.")

if BOT_PASSWORD == "" or BOT_PASSWORD is None:
    raise ValueError("BOT_PASSWORD must be set in the environment variables.")

if BOT_NODE_JID == "":
    BOT_NODE_JID = None


def main():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(KikClient.log_format()))
    logger.addHandler(stream_handler)

    # Create the bootstrappable bot and start it up. See examples/bootstrap_bot.py for more info.
    # You can create your own bootstrappable bot class, and pass it to the bootstrapper.
    bot = BootstrapBot()
    _ = DockerBootstrapper(
        bot,
        BOT_USERNAME,
        BOT_PASSWORD,
        BOT_NODE_JID)


class DockerBootstrapper:
    """
    A utility class used to bootstrap a bot for Docker, and then run it.
    """

    __slots__ = ["client", "bot"]

    def __init__(self, bot: KikClientCallback, username: str, password: str, node_jid: str = None):
        self.client = KikClient(
            callback=bot,
            kik_username=username,
            kik_password=password,
            kik_node=node_jid)
        self.bot = bot
        self.bot.client = self.client


if __name__ == '__main__':
    main()
