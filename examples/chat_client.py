import logging
import time

from kik_unofficial.api import KikApi
from kik_unofficial.callback import KikAdapter
from kik_unofficial.message.chat import MessageResponse, GroupMessageResponse, StatusResponse, GroupStatusResponse
from kik_unofficial.message.roster import RosterResponse
from kik_unofficial.message.unauthorized.register import ConnectionFailedResponse

username = 'username'
password = 'password'

friends = {}


class ChatClient(KikAdapter):
    def on_authorized(self):
        client.request_roster()

    def on_roster(self, response: RosterResponse):
        for m in response.members:
            friends[m.jid] = m
        print("-Peers-\n{}".format("\n".join([str(m) for m in response.members])))

    def on_message(self, response: MessageResponse):
        print("{}: {}".format(jid_to_username(response.from_jid), response.body))
        if response.from_jid not in friends:
            print("New friend: {}".format(jid_to_username(response.from_jid)))
            client.send(response.from_jid, "Hi!")
            time.sleep(1)
            client.add_friend(response.from_jid)
            client.request_roster()

    def on_group_message(self, response: GroupMessageResponse):
        print("{} - {}: {}".format(friends[response.group_jid].name, jid_to_username(response.from_jid),
                                   jid_to_username(response.body)))

    def on_connection_failed(self, response: ConnectionFailedResponse):
        print("Connection failed")

    def on_status_message(self, response: StatusResponse):
        print(response.status)
        client.add_friend(response.from_jid)

    def on_group_status(self, response: GroupStatusResponse):
        client.request_info_from_jid(response.status_jid)


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
                client.send(peer_jid, message)


if __name__ == '__main__':
    callback = ChatClient()
    client = KikApi(callback=callback, username=username, password=password, loglevel=logging.DEBUG)
    chat()
