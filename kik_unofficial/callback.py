from kik_unofficial.message.chat import MessageDeliveredResponse, MessageReadResponse, MessageResponse, \
    GroupMessageResponse, FriendAttributionResponse, GroupStatusResponse, IsTypingResponse, GroupIsTypingResponse, \
    GroupReceiptResponse, StatusResponse
from kik_unofficial.message.roster import RosterResponse, FriendMessageResponse
from kik_unofficial.message.unauthorized.checkunique import CheckUniqueResponse
from kik_unofficial.message.unauthorized.register import RegisterError, RegisterResponse, LoginResponse, \
    ConnectionFailedResponse


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

    def on_is_typing(self, response: IsTypingResponse):
        raise NotImplementedError

    def on_group_is_typing(self, response: GroupIsTypingResponse):
        raise NotImplementedError

    def on_group_receipt(self, response: GroupReceiptResponse):
        raise NotImplementedError

    def on_connection_failed(self, response: ConnectionFailedResponse):
        raise NotImplementedError

    def on_status_message(self, response: StatusResponse):
        raise NotImplementedError


class KikAdapter(KikCallback):
    def on_status_message(self, response: StatusResponse):
        pass

    def on_check_unique(self, response: CheckUniqueResponse):
        pass

    def on_group_message(self, response: GroupMessageResponse):
        pass

    def on_register(self, response: RegisterResponse):
        pass

    def on_authorized(self):
        pass

    def on_peer_info(self, response: FriendMessageResponse):
        pass

    def on_friend_attribution(self, response: FriendAttributionResponse):
        pass

    def on_message_read(self, response: MessageReadResponse):
        pass

    def on_login(self, response: LoginResponse):
        pass

    def on_message_delivered(self, response: MessageDeliveredResponse):
        pass

    def on_group_is_typing(self, response: GroupIsTypingResponse):
        pass

    def on_message(self, response: MessageResponse):
        pass

    def on_is_typing(self, response: IsTypingResponse):
        pass

    def on_group_status(self, response: GroupStatusResponse):
        pass

    def on_group_receipt(self, response: GroupReceiptResponse):
        pass

    def on_login_error(self, response: RegisterError):
        pass

    def on_register_error(self, response: RegisterError):
        pass

    def on_roster(self, response: RosterResponse):
        pass

    def on_connection_failed(self, response: ConnectionFailedResponse):
        pass
