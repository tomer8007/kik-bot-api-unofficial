from kik_unofficial.api import KikApi
from kik_unofficial.callback import KikCallback
from kik_unofficial.message.chat import StatusResponse, GroupReceiptResponse, GroupIsTypingResponse, IsTypingResponse, \
    GroupStatusResponse, FriendAttributionResponse, GroupMessageResponse, MessageResponse, MessageReadResponse, \
    MessageDeliveredResponse
from kik_unofficial.message.roster import FriendMessageResponse, RosterResponse
from kik_unofficial.message.unauthorized.checkunique import CheckUniqueResponse
from kik_unofficial.message.unauthorized.register import ConnectionFailedResponse, LoginResponse, RegisterResponse, \
    RegisterError

username = 'username'
password = 'password'


class EchoClient(KikCallback):
    def on_check_unique(self, response: CheckUniqueResponse):
        print("Is {} a unique username? {}".format(response.username, response.unique))

    def on_register_error(self, response: RegisterError):
        print("Register error: {}".format(response.message))

    def on_login_error(self, response: RegisterError):
        print("Login error: {}".format(response.message))

    def on_register(self, response: RegisterResponse):
        print("Registered as " + response.node)

    def on_login(self, response: LoginResponse):
        print("Logged in as " + response.username)

    def on_roster(self, response: RosterResponse):
        print("Roster:\n" + '\n'.join([str(m) for m in response.members]))

    def on_authorized(self):
        print("Authorized, requesting roster")
        client.request_roster()

    def on_message_delivered(self, response: MessageDeliveredResponse):
        print("{} delivered.".format(response.message_id))

    def on_message_read(self, response: MessageReadResponse):
        print("{} read.".format(response.message_id))

    def on_message(self, response: MessageResponse):
        print("{}: {}".format(response.from_jid, response.body))

    def on_group_message(self, response: GroupMessageResponse):
        print("{} in {}: {}".format(response.from_jid, response.group_jid, response.body))

    def on_friend_attribution(self, response: FriendAttributionResponse):
        print("Friend attribution request from " + response.referrer_jid)

    def on_peer_info(self, response: FriendMessageResponse):
        print("Peer info: " + str(response.user))

    def on_group_status(self, response: GroupStatusResponse):
        print("Status message in {}: {}".format(response.group_jid, response.status))

    def on_is_typing(self, response: IsTypingResponse):
        print("{} is {}typing".format(response.from_jid, "not " if not response.is_typing else ""))

    def on_group_is_typing(self, response: GroupIsTypingResponse):
        print("{} is {}typing in {}".format(response.from_jid, "not " if not response.is_typing else "",
                                            response.group_jid))

    def on_group_receipt(self, response: GroupReceiptResponse):
        print("Receipt in {}: {}".format(response.group_jid, ",".join(response.receipt_ids)))

    def on_connection_failed(self, response: ConnectionFailedResponse):
        print("Connection failed: " + response.message)

    def on_status_message(self, response: StatusResponse):
        print("Status message from {}: {}".format(response.from_jid, response.status))


if __name__ == '__main__':
    client = KikApi(EchoClient(), username, password)
