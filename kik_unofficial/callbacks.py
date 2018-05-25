from kik_unofficial.datatypes.xmpp.errors import LoginError, SignUpError
from kik_unofficial.datatypes.xmpp.chatting import IncomingMessageDeliveredEvent, IncomingMessageReadEvent, IncomingChatMessage, \
    IncomingGroupChatMessage, IncomingFriendAttribution, IncomingGroupStatus, IncomingIsTypingEvent, IncomingGroupIsTypingEvent, \
    IncomingGroupReceiptsEvent, IncomingStatusResponse, IncomingGroupSticker
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse, PeerInfoResponse, GroupSearchResponse
from kik_unofficial.datatypes.xmpp.sign_up import RegisterResponse, UsernameUniquenessResponse
from kik_unofficial.datatypes.xmpp.login import LoginResponse, ConnectionFailedResponse


class KikClientCallback:
    def on_authenticated(self):
        """
        Gets called when the kik user is fully logged-in and authenticated as himself.
        Only from this point on you can start doing things, such as sending messages, searching for groups, etc.
        """
        pass

    def on_chat_message_received(self, chat_message: IncomingChatMessage):
        """
        Gets called when a new chat message is received from a person (not a group).
        :param chat_message: The chat message received
        """
        pass

    def on_group_message_received(self, chat_message: IncomingGroupChatMessage):
        """
        Gets called when a new chat message is received from a group
        :param chat_message: The new group message
        """
        pass

    def on_status_message_received(self, response: IncomingStatusResponse):
        pass

    def on_username_uniqueness_received(self, response: UsernameUniquenessResponse):
        pass

    def on_sign_up_ended(self, response: RegisterResponse):
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

    def on_is_typing_event_received(self, response: IncomingIsTypingEvent):
        pass

    def on_group_status_received(self, response: IncomingGroupStatus):
        pass

    def on_group_receipts_received(self, response: IncomingGroupReceiptsEvent):
        pass

    def on_group_sticker(self, response: IncomingGroupSticker):
        pass

    def on_group_search_response(self, response: GroupSearchResponse):
        pass

    # --- errors ---

    def on_login_error(self, response: LoginError):
        pass

    def on_register_error(self, response: SignUpError):
        pass

    def on_roster_received(self, response: FetchRosterResponse):
        pass

    def on_connection_failed(self, response: ConnectionFailedResponse):
        pass

