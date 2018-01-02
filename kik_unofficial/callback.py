from kik_unofficial.message.chat import MessageDeliveredResponse, MessageReadResponse, MessageResponse, \
    GroupMessageResponse, FriendAttributionResponse, GroupStatusResponse
from kik_unofficial.message.roster import RosterResponse, FriendMessageResponse
from kik_unofficial.message.unauthorized.checkunique import CheckUniqueResponse
from kik_unofficial.message.unauthorized.register import RegisterError, RegisterResponse, LoginResponse


class KikCallback:
    def on_check_unique(self, response: CheckUniqueResponse):
        raise NotImplementedError

    def on_register_error(self, response: RegisterError):
        raise NotImplementedError

    def on_login_error(self, response: RegisterError):
        raise NotImplementedError

    def on_register(self, response: RegisterResponse):
        raise NotImplementedError

    def on_login(self, response: LoginResponse):
        raise NotImplementedError

    def on_roster(self, response: RosterResponse):
        raise NotImplementedError

    def on_authorized(self):
        raise NotImplementedError

    def on_message_delivered(self, response: MessageDeliveredResponse):
        raise NotImplementedError

    def on_message_read(self, response: MessageReadResponse):
        raise NotImplementedError

    def on_message(self, response: MessageResponse):
        raise NotImplementedError

    def on_group_message(self, response: GroupMessageResponse):
        raise NotImplementedError

    def on_friend_attribution(self, response: FriendAttributionResponse):
        raise NotImplementedError

    def on_peer_info(self, response: FriendMessageResponse):
        raise NotImplementedError

    def on_group_status(self, response: GroupStatusResponse):
        raise NotImplementedError
