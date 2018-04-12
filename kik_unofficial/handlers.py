from bs4 import BeautifulSoup

from kik_unofficial.client import KikClientCallback
from kik_unofficial.datatypes.errors import SignUpError, LoginError
from kik_unofficial.datatypes.xmpp.chatting import IncomingMessageDeliveredEvent, IncomingMessageReadEvent, IncomingChatMessage, \
    IncomingGroupChatMessage, IncomingFriendAttribution, IncomingGroupStatus, IncomingIsTypingEvent, IncomingGroupIsTypingEvent, \
    IncomingStatusResponse, IncomingGroupSticker
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse, PeerInfoResponse, GroupSearchResponse
from kik_unofficial.datatypes.xmpp.sign_up import RegisterResponse, LoginResponse, UsernameUniquenessResponse


class Handler:
    def __init__(self, callback: KikClientCallback, api):
        self.callback = callback
        self.api = api

    def handle(self, data: BeautifulSoup):
        raise NotImplementedError


class CheckUniqueHandler(Handler):
    def handle(self, data: BeautifulSoup):
        self.callback.on_username_uniqueness_received(UsernameUniquenessResponse(data))


class RegisterHandler(Handler):
    def handle(self, data: BeautifulSoup):
        message_type = data['type']

        if message_type == "error":
            if data.find('email'):
                self.callback.on_register_error(SignUpError(data))
            else:
                self.callback.on_login_error(LoginError(data))
        elif message_type == "result":
            if data.find('node'):
                self.api.node = data.find('node').text
            if data.find('email'):
                response = LoginResponse(data)
                self.callback.on_login_ended(response)
                self.api._establish_auth_connection()
            else:
                response = RegisterResponse(data)
                self.callback.on_sign_up_ended(response)
                self.api._establish_auth_connection()


class RosterHandler(Handler):
    def handle(self, data: BeautifulSoup):
        self.callback.on_roster_received(FetchRosterResponse(data))


class MessageHandler(Handler):
    def handle(self, data: BeautifulSoup):
        if data['type'] == 'chat':
            if data.body:
                self.callback.on_chat_message_received(IncomingChatMessage(data))
            elif data.find('friend-attribution'):
                self.callback.on_friend_attribution(IncomingFriendAttribution(data))
            elif data.find('status'):
                self.callback.on_status_message(IncomingStatusResponse(data))
            else:
                raise NotImplementedError
        elif data['type'] == 'receipt':
            if data.receipt['type'] == 'delivered':
                self.callback.on_message_delivered(IncomingMessageDeliveredEvent(data))
            else:
                self.callback.on_message_read(IncomingMessageReadEvent(data))
        elif data['type'] == 'is-typing':
            self.callback.on_is_typing_event_received(IncomingIsTypingEvent(data))
        elif data['type'] == 'groupchat':
            if data.body:
                self.callback.on_group_message_received(IncomingGroupChatMessage(data))
            elif data.find('is-typing'):
                self.callback.on_group_is_typing_event_received(IncomingGroupIsTypingEvent(data))
            elif data.find('status'):
                self.callback.on_group_status_received(IncomingGroupStatus(data))
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError


class GroupMessageHandler(Handler):
    def handle(self, data: BeautifulSoup):
        if data.body:
            self.callback.on_group_message_received(IncomingGroupChatMessage(data))
        elif data.find('is-typing'):
            self.callback.on_group_is_typing_event_received(IncomingGroupIsTypingEvent(data))
        elif data.content and 'app-id' in data.content.attrs:
            app_id = data.content['app-id']
            if app_id == 'com.kik.ext.stickers':
                self.callback.on_group_sticker(IncomingGroupSticker(data))

        else:
            raise NotImplementedError


class FriendMessageHandler(Handler):
    def handle(self, data: BeautifulSoup):
        self.callback.on_peer_info_received(PeerInfoResponse(data))


class GroupSearchHandler(Handler):
    def handle(self, data: BeautifulSoup):
        self.callback.on_group_search_response(GroupSearchResponse(data))
