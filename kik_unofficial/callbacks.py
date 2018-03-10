from kik_unofficial.datatypes.errors import SignUpError, LoginError
from kik_unofficial.datatypes.xmpp.chatting import IncomingMessageDeliveredEvent, IncomingMessageReadEvent, IncomingChatMessage, \
    IncomingGroupChatMessage, IncomingFriendAttribution, IncomingGroupStatus, IncomingIsTypingEvent, IncomingGroupIsTypingEvent, \
    IncomingGroupReceiptsEvent, IncomingStatusResponse
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse, PeerInfoResponse
from kik_unofficial.datatypes.xmpp.sign_up import RegisterResponse, LoginResponse, \
    ConnectionFailedResponse, UsernameUniquenessResponse


class KikClientCallback:
    def on_status_message(self, response: IncomingStatusResponse):
        pass

    def on_username_uniqueness_received(self, response: UsernameUniquenessResponse):
        pass

    def on_group_message_received(self, response: IncomingGroupChatMessage):
        pass

    def on_sign_up_ended(self, response: RegisterResponse):
        pass

    def on_authorized(self):
        pass

    def on_peer_info_received(self, response: PeerInfoResponse):
        pass

    def on_friend_attribution(self, response: IncomingFriendAttribution):
        pass

    def on_message_read(self, response: IncomingMessageReadEvent):
        pass

    def on_login_ended(self, response: LoginResponse):
        pass

    def on_message_delivered(self, response: IncomingMessageDeliveredEvent):
        pass

    def on_group_is_typing_event_received(self, response: IncomingGroupIsTypingEvent):
        pass

    def on_chat_message_received(self, response: IncomingChatMessage):
        pass

    def on_is_typing_event_received(self, response: IncomingIsTypingEvent):
        pass

    def on_group_status_received(self, response: IncomingGroupStatus):
        pass

    def on_group_receipts_received(self, response: IncomingGroupReceiptsEvent):
        pass

    def on_login_error(self, response: LoginError):
        pass

    def on_register_error(self, response: SignUpError):
        pass

    def on_roster_received(self, response: FetchRosterResponse):
        pass

    def on_connection_failed(self, response: ConnectionFailedResponse):
        pass
