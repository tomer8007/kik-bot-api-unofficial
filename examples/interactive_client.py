import logging
import sys
import time
import threading

from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.chatting import IncomingChatMessage, IncomingGroupChatMessage, IncomingStatusResponse, IncomingGroupStatus
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse
from kik_unofficial.datatypes.xmpp.login import ConnectionFailedResponse

username = sys.argv[1]
password = sys.argv[2] if len(sys.argv) > 2 else input('Password: ')

friends = {}


class InteractiveChatClient(KikClientCallback):
    def on_authenticated(self):
        cli_thread = threading.Thread(target=chat)
        cli_thread.start()

    def on_roster_received(self, response: FetchRosterResponse):
        for m in response.peers:
            friends[m.jid] = m
        print("-Peers-\n{}".format("\n".join([str(m) for m in response.peers])))

    def on_chat_message_received(self, chat_message: IncomingChatMessage):
        print("{}: {}".format(jid_to_username(chat_message.from_jid), chat_message.body))
        if chat_message.from_jid not in friends:
            print("New friend: {}".format(jid_to_username(chat_message.from_jid)))
            client.send_chat_message(chat_message.from_jid, "Hi!")
            time.sleep(1)
            client.add_friend(chat_message.from_jid)
            client.request_roster()

    def on_group_message_received(self, chat_message: IncomingGroupChatMessage):
        print("{} - {}: {}".format(friends[chat_message.group_jid].name, jid_to_username(chat_message.from_jid),
                                   jid_to_username(chat_message.body)))

    def on_connection_failed(self, response: ConnectionFailedResponse):
        print("Connection failed")

    def on_status_message_received(self, response: IncomingStatusResponse):
        print(response.status)
        client.add_friend(response.from_jid)

    def on_group_status_received(self, response: IncomingGroupStatus):
        client.request_info_of_users(response.status_jid)


def jid_to_username(jid):
    return jid.split('@')[0][0:-4]


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
                        print("Chatting with {}".format(jid_to_username(jid)))
                        peer_jid = jid
                        break
            elif action == 'f':
                client.request_roster()
        else:
            if peer_jid and message:
                client.send_chat_message(peer_jid, message)


if __name__ == '__main__':
    logging.basicConfig(format=KikClient.log_format(), level=logging.DEBUG)
    callback = InteractiveChatClient()
    client = KikClient(callback=callback, kik_username=username, kik_password=password)
