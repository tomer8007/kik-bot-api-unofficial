#!/usr/bin/env python3

import argparse
import json
import logging
import os
import sys
import time
import threading

from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.chatting import IncomingChatMessage, IncomingGroupChatMessage, IncomingStatusResponse, IncomingGroupStatus
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse
from kik_unofficial.datatypes.xmpp.login import ConnectionFailedResponse

friends = {}


class InteractiveChatClient(KikClientCallback):
    def on_authenticated(self):
        cli_thread = threading.Thread(target=chat)
        cli_thread.start()

    def on_roster_received(self, response: FetchRosterResponse):
        for peer in response.peers:
            friends[peer.jid] = peer

        print("-Peers-\n{}".format("\n".join([str(m) for m in response.peers])))

    def on_chat_message_received(self, chat_message: IncomingChatMessage):
        print(f"{jid_to_username(chat_message.from_jid)}: {chat_message.body}")

        if chat_message.from_jid not in friends:
            print(f"New friend: {jid_to_username(chat_message.from_jid)}")
            client.send_chat_message(chat_message.from_jid, "Hi!")
            time.sleep(1)
            client.add_friend(chat_message.from_jid)
            client.request_roster()

    def on_group_message_received(self, chat_message: IncomingGroupChatMessage):
        print(f"{friends[chat_message.group_jid].name} - {jid_to_username(chat_message.from_jid)}: {chat_message.body}")

    def on_connection_failed(self, response: ConnectionFailedResponse):
        print("Connection failed")

    def on_status_message_received(self, response: IncomingStatusResponse):
        print(response.status)
        client.add_friend(response.from_jid)

    def on_group_status_received(self, response: IncomingGroupStatus):
        client.request_info_of_users(response.status_jid)


def jid_to_username(jid):
    return jid.split('@')[0][:-4]


def chat():
    print("-Usage-\n\n"
          "/c [first letters of username]  -  Chat with peer\n"
          "/f  -  List peers\n\n"
          "Type a line to send a message.\n")
    peer_jid = None
    while True:
        message = input()
        if message.startswith('/'):
            action = message[1]
            if action == 'c' and len(message) > 3:
                for jid in friends:
                    if jid.startswith(message[3:]):
                        print(f"Chatting with {jid_to_username(jid)}")
                        peer_jid = jid
                        break
            elif action == 'f':
                client.request_roster()
        elif peer_jid and message:
            client.send_chat_message(peer_jid, message)

def main():
    # The credentials file where you store the bot's login information
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--creds', default='creds.json', help='Path to credentials file')
    args = parser.parse_args()

    # Changes the current working directory to /examples
    if not os.path.isfile(args.creds):
        print("Can't find credentials file.")
        return

    # load the bot's credentials from creds.json
    with open(args.creds, "r") as f:
        creds = json.load(f)

    device_id = creds['device_id']
    android_id = creds['android_id']
    username = creds['username']
    node = creds.get('node')
    password = creds.get('password')
    if not password:
        password = input('Password: ')

    # set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(KikClient.log_format()))
    logger.addHandler(stream_handler)

    # create the client
    callback = InteractiveChatClient()
    client = KikClient(callback=callback, kik_username=username, kik_password=password, kik_node=node, device_id=device_id, android_id=android_id, enable_logging=True, log_level=2)
    client.wait_for_messages()

if __name__ == '__main__':
    main()
