#!/usr/bin/env python3
"""
A bot that sends acknowledgements for every message in the account's past messaging history
"""

import argparse
import logging
import sys
import yaml

import kik_unofficial.datatypes.xmpp.chatting as chatting
from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.errors import LoginError
from kik_unofficial.datatypes.xmpp.login import LoginResponse, ConnectionFailedResponse
from kik_unofficial.datatypes.xmpp.history import HistoryResponse

username = sys.argv[1] if len(sys.argv) > 1 else input("Username: ")
password = sys.argv[2] if len(sys.argv) > 2 else input('Password: ')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--credentials', default='creds.yaml', help='Credentials file containing at least username, device_id and android_id.')
    args = parser.parse_args()
    
    with open(args.credentials) as f:
        creds = yaml.safe_load(f)
    if not creds.get('password'):
        creds['password'] = input('Password: ')
    
    # set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(KikClient.log_format()))
    logger.addHandler(stream_handler)

    # create the bot
    bot = AckBot(creds)


class AckBot(KikClientCallback):
    def __init__(self, creds):
        self.client = KikClient(self, creds['username'], creds['password'], kik_node=creds.get('node'), device_id=creds['device_id'], android_id=creds['android_id'])
        self.client.wait_for_messages()

    def on_authenticated(self):
        print("Authenticated, requesting messaging history")
        self.client.request_messaging_history()

    def on_login_ended(self, response: LoginResponse):
        print(f"Full name: {response.first_name} {response.last_name}")

    def on_message_history_response(self, response: HistoryResponse):
        if len(response.messages) > 0:
            self.client.send_ack(messages=response.messages, request_history=response.more)
        elif response.more:
            self.client.request_messaging_history()

    def on_chat_message_received(self, chat_message: chatting.IncomingChatMessage):
        print(f"[+] '{chat_message.from_jid}' says: {chat_message.body}")
        self.client.send_ack(chat_message)

    def on_group_message_received(self, chat_message: chatting.IncomingGroupChatMessage):
        print(f"[+] '{chat_message.from_jid}' from group ID {chat_message.group_jid} says: {chat_message.body}")
        self.client.send_ack(chat_message)

    # Error handling

    def on_connection_failed(self, response: ConnectionFailedResponse):
        print(f"[-] Connection failed: {response.message}")

    def on_login_error(self, login_error: LoginError):
        if login_error.is_captcha():
            login_error.solve_captcha_wizard(self.client)


if __name__ == '__main__':
    main()
