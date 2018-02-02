from kik_unofficial.client import KikClient
from kik_unofficial.datatypes.callbacks import KikClientCallback
from kik_unofficial.datatypes.errors import SignUpError, LoginError
from kik_unofficial.datatypes.xmpp.chatting import IncomingStatusResponse, IncomingGroupReceiptsEvent, IncomingGroupIsTypingEvent, IncomingIsTypingEvent, \
    IncomingGroupStatus, IncomingFriendAttribution, IncomingGroupChatMessage, IncomingChatMessage, IncomingMessageReadEvent, \
    IncomingMessageDeliveredEvent
from kik_unofficial.datatypes.xmpp.roster import FriendResponse, FetchRosterResponse
from kik_unofficial.datatypes.xmpp.sign_up import ConnectionFailedResponse, LoginResponse, RegisterResponse, UsernameUniquenessResponse

import logging

username = 'your_kik_username_here'
password = 'your_kik_password_here'


class PrintCallback(KikClientCallback):
    def on_username_uniqueness_received(self, response: UsernameUniquenessResponse):
        print("Is {} a unique username? {}".format(response.username, response.unique))

    def on_register_error(self, response: SignUpError):
        print("Register error: {}".format(response.message))

    def on_login_error(self, response: LoginError):
        print("Login error: {}".format(response.message))

    def on_sign_up_ended(self, response: RegisterResponse):
        print("Registered as " + response.node)

    def on_login_ended(self, response: LoginResponse):
        print("Logged in as " + response.username)

    def on_roster_received(self, response: FetchRosterResponse):
        print("Roster:\n" + '\n'.join([str(m) for m in response.members]))

    def on_authorized(self):
        print("Authorized, requesting roster")
        client.request_roster()

    def on_message_delivered(self, response: IncomingMessageDeliveredEvent):
        print("{} delivered.".format(response.message_id))

    def on_message_read(self, response: IncomingMessageReadEvent):
        print("{} read.".format(response.message_id))

    def on_chat_message_received(self, response: IncomingChatMessage):
        print("{}: {}".format(response.from_jid, response.body))

    def on_group_message_received(self, response: IncomingGroupChatMessage):
        print("{} in {}: {}".format(response.from_jid, response.group_jid, response.body))

    def on_friend_attribution(self, response: IncomingFriendAttribution):
        print("Friend attribution request from " + response.referrer_jid)

    def on_peer_info_received(self, response: FriendResponse):
        print("Peer info: " + str(response.user))

    def on_group_status_received(self, response: IncomingGroupStatus):
        print("Status message in {}: {}".format(response.group_jid, response.status))

    def on_is_typing_event_received(self, response: IncomingIsTypingEvent):
        print("{} is {}typing".format(response.from_jid, "not " if not response.is_typing else ""))

    def on_group_is_typing_event_received(self, response: IncomingGroupIsTypingEvent):
        print("{} is {}typing in {}".format(response.from_jid, "not " if not response.is_typing else "",
                                            response.group_jid))

    def on_group_receipts_received(self, response: IncomingGroupReceiptsEvent):
        print("Receipt in {}: {}".format(response.group_jid, ",".join(response.receipt_ids)))

    def on_connection_failed(self, response: ConnectionFailedResponse):
        print("Connection failed: " + response.message)

    def on_status_message(self, response: IncomingStatusResponse):
        print("Status message from {}: {}".format(response.from_jid, response.status))


if __name__ == '__main__':
    callback = PrintCallback()
    client = KikClient(callback, username, password)
