#!/usr/bin/env python3
"""
A bot that sends acknowledgements for every message in the account's past messaging history
"""

import logging
import sys

import kik_unofficial.datatypes.xmpp.chatting as chatting
from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.errors import LoginError
from kik_unofficial.datatypes.xmpp.login import LoginResponse, ConnectionFailedResponse
from kik_unofficial.datatypes.xmpp.history import HistoryResponse

username = sys.argv[1] if len(sys.argv) > 1 else input("Username: ")
password = sys.argv[2] if len(sys.argv) > 2 else input('Password: ')


def main():
    # set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(KikClient.log_format()))
    logger.addHandler(stream_handler)

    # create the bot
    bot = AckBot()


class AckBot(KikClientCallback):
    def __init__(self):
        self.client = KikClient(self, username, password)
        self.client.wait_for_messages()

    def on_authenticated(self):
        print("Authenticated, requesting messaging history")
        self.client.request_messaging_history()

    def on_login_ended(self, response: LoginResponse):
        print("Full name: {} {}".format(response.first_name, response.last_name))

    def on_message_history_response(self, response: HistoryResponse):
        if hasattr(response, 'messages'):
            self.client.send_ack(response.from_jid, False, response.id)

            for msg in response.messages:
                print(msg.type)
                if msg.type == 'chat':
                    self.client.send_ack(msg.from_jid, False, msg.id)
                elif msg.type == 'groupchat':
                    self.client.send_ack(msg.from_jid, False, msg.id, msg.group_jid)
                elif msg.type == 'receipt':
                    self.client.send_ack(msg.from_jid, True, msg.id)

            if response.more:
                self.client.request_messaging_history()

    def on_chat_message_received(self, chat_message: chatting.IncomingChatMessage):
        print("[+] '{}' says: {}".format(chat_message.from_jid, chat_message.body))
        self.client.send_ack(chat_message.from_jid, False, chat_message.message_id)

    def on_group_message_received(self, chat_message: chatting.IncomingGroupChatMessage):
        print("[+] '{}' from group ID {} says: {}".format(chat_message.from_jid, chat_message.group_jid, chat_message.body))
        self.client.send_ack(chat_message.from_jid, False, chat_message.message_id, chat_message.group_jid)

    # Error handling

    def on_connection_failed(self, response: ConnectionFailedResponse):
        print("[-] Connection failed: " + response.message)

    def on_login_error(self, login_error: LoginError):
        if login_error.is_captcha():
            login_error.solve_captcha_wizard(self.client)


if __name__ == '__main__':
    main()
