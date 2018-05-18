"""
A Kik bot that just logs every event that it gets (new message, message read, etc.),
and echos back whatever chat messages it receives.
"""

from kik_unofficial.client import KikClient
from kik_unofficial.datatypes.callbacks import KikClientCallback
from kik_unofficial.datatypes.errors import SignUpError, LoginError
from kik_unofficial.datatypes.xmpp.chatting import IncomingStatusResponse, IncomingGroupReceiptsEvent, IncomingGroupIsTypingEvent, IncomingIsTypingEvent, \
    IncomingGroupStatus, IncomingFriendAttribution, IncomingGroupChatMessage, IncomingChatMessage, IncomingMessageReadEvent, \
    IncomingMessageDeliveredEvent
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse
from kik_unofficial.datatypes.xmpp.sign_up import ConnectionFailedResponse, RegisterResponse, UsernameUniquenessResponse
from kik_unofficial.datatypes.xmpp.login import LoginResponse

username = 'your_kik_username'
password = 'your_kik_password'


def main():
    bot = EchoBot()


class EchoBot(KikClientCallback):
    def __init__(self):
        self.client = KikClient(self, username, password)

    def on_authorized(self):
        print("[+] Authorized, requesting roster")
        self.client.request_roster()

    def on_login_ended(self, response: LoginResponse):
        print("[+] Logged in as " + response.username)

    def on_chat_message_received(self, chat_message: IncomingChatMessage):
        print("[+] '{}' says: {}".format(chat_message.from_jid, chat_message.body))
        print("[+] Replaying.")
        self.client.send_chat_message(chat_message.from_jid, "You said \"" + chat_message.body + "\"!")

    def on_message_delivered(self, response: IncomingMessageDeliveredEvent):
        print("[+] Chat message with ID {} is delivered.".format(response.message_id))

    def on_message_read(self, response: IncomingMessageReadEvent):
        print("[+] Human has read the message with ID {}.".format(response.message_id))

    def on_group_message_received(self, response: IncomingGroupChatMessage):
        print("[+] '{}' from group ID {} says: {}".format(response.from_jid, response.group_jid, response.body))

    def on_is_typing_event_received(self, response: IncomingIsTypingEvent):
        print("[+] {} is now {}typing.".format(response.from_jid, "not " if not response.is_typing else ""))

    def on_group_is_typing_event_received(self, response: IncomingGroupIsTypingEvent):
        print("[+] {} is now {}typing in group {}".format(response.from_jid, "not " if not response.is_typing else "",
                                            response.group_jid))

    def on_roster_received(self, response: FetchRosterResponse):
        print("[+] Roster:\n" + '\n'.join([str(m) for m in response.members]))

    def on_friend_attribution(self, response: IncomingFriendAttribution):
        print("[+] Friend attribution request from " + response.referrer_jid)

    def on_peer_info_received(self, response: FetchRosterResponse):
        print("[+] Peer info: " + str(response.user))

    def on_group_status_received(self, response: IncomingGroupStatus):
        print("[+] Status message in {}: {}".format(response.group_jid, response.status))

    def on_group_receipts_received(self, response: IncomingGroupReceiptsEvent):
        print("[+] Received receipts in group {}: {}".format(response.group_jid, ",".join(response.receipt_ids)))

    def on_status_message(self, response: IncomingStatusResponse):
        print("[+] Status message from {}: {}".format(response.from_jid, response.status))

    def on_username_uniqueness_received(self, response: UsernameUniquenessResponse):
            print("Is {} a unique username? {}".format(response.username, response.unique))

    def on_sign_up_ended(self, response: RegisterResponse):
        print("[+] Registered as " + response.node)

    # Error handling

    def on_connection_failed(self, response: ConnectionFailedResponse):
        print("[-] Connection failed: " + response.message)

    def on_login_error(self, response: LoginError):
        print("[-] Login error: {}".format(response.message))

    def on_register_error(self, response: SignUpError):
            print("[-] Register error: {}".format(response.message))


if __name__ == '__main__':
    main()
