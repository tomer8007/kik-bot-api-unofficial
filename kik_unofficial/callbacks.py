from typing import Union

from kik_unofficial.datatypes.xmpp.chatting import *
from kik_unofficial.datatypes.xmpp.errors import LoginError, SignUpError
from kik_unofficial.datatypes.xmpp.login import LoginResponse, ConnectionFailedResponse, CaptchaElement
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse, PeersInfoResponse, GroupSearchResponse
from kik_unofficial.datatypes.xmpp.sign_up import RegisterResponse, UsernameUniquenessResponse
from kik_unofficial.datatypes.xmpp.xiphias import UsersResponse, UsersByAliasResponse


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
        """
        Gets called after a call to check_username_uniqueness(), indicating whether or not a requested username was
        found available for registration
        :param response: a UsernameUniquenessResponse instance whose 'unique' member is True or False
        """
        pass

    def on_sign_up_ended(self, response: RegisterResponse):
        pass

    def on_peer_info_received(self, response: PeersInfoResponse):
        pass

    def on_friend_attribution(self, response: IncomingFriendAttribution):
        pass

    def on_message_read(self, response: IncomingMessageReadEvent):
        pass

    def on_login_ended(self, response: LoginResponse):
        pass

    def on_disconnected(self):
        """
        Called when the connection is closed the loop has ended.
        :return:
        """
        pass

    def on_message_delivered(self, response: IncomingMessageDeliveredEvent):
        pass

    def on_group_is_typing_event_received(self, response: IncomingGroupIsTypingEvent):
        pass

    def on_is_typing_event_received(self, response: IncomingIsTypingEvent):
        pass

    def on_group_status_received(self, response: IncomingGroupStatus):
        pass

    def on_group_sysmsg_received(self, response: IncomingGroupSysmsg):
        pass

    def on_group_receipts_received(self, response: IncomingGroupReceiptsEvent):
        pass

    def on_group_sticker(self, response: IncomingGroupSticker):
        pass

    def on_group_search_response(self, response: GroupSearchResponse):
        """
        Gets called when a search for groups is done and we get a response, usually after calling search_group()
        :param response: Contains the list of groups that were found (see the code of GroupSearchResponse)
        """
        pass

    def on_image_received(self, response: IncomingImageMessage):
        pass

    def on_gif_received(self, response: IncomingGifMessage):
        pass

    def on_video_received(self, response: IncomingVideoMessage):
        pass

    # ----------
    # Errors
    # ----------

    def on_login_error(self, response: LoginError):
        pass

    def on_register_error(self, response: SignUpError):
        pass

    def on_roster_received(self, response: FetchRosterResponse):
        pass

    def on_connection_failed(self, response: ConnectionFailedResponse):
        pass

    def on_captcha_received(self, response: CaptchaElement):
        """
        Gets called when kik servers require us to fill a captcha in order to continue
        To solve the captcha, follow the steps as shown in solve_captcha_wizard() and then call send_captcha_result()
        :param response: The CaptchaElement that kik sent, which contains an stc_id and the captcha URL
        """
        pass

    def on_xiphias_get_users_response(self, response: Union[UsersResponse, UsersByAliasResponse]):
        pass

    def on_card_received(self, response: IncomingCardMessage):
        pass