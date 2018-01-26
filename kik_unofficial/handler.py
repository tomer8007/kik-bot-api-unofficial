from bs4 import BeautifulSoup
from kik_unofficial.api import KikCallback
from kik_unofficial.message.chat import MessageDeliveredResponse, MessageReadResponse, MessageResponse, \
    GroupMessageResponse, FriendAttributionResponse, GroupStatusResponse, IsTypingResponse, GroupIsTypingResponse, \
    StatusResponse
from kik_unofficial.message.roster import RosterResponse, FriendMessageResponse
from kik_unofficial.message.unauthorized.checkunique import CheckUniqueResponse
from kik_unofficial.message.unauthorized.register import RegisterError, RegisterResponse, LoginResponse


class Handler:
    def __init__(self, callback: KikCallback, api):
        self.callback = callback
        self.api = api

    def handle(self, data: BeautifulSoup):
        raise NotImplementedError


class CheckUniqueHandler(Handler):
    def handle(self, data: BeautifulSoup):
        self.callback.on_check_unique(CheckUniqueResponse(data))


class RegisterHandler(Handler):
    def handle(self, data: BeautifulSoup):
        message_type = data['type']
        if message_type == "error":
            if data.find('email'):
                self.callback.on_register_error(RegisterError(data))
            else:
                self.callback.on_login_error(RegisterError(data))
        elif message_type == "result":
            if data.find('node'):
                self.api.node = data.find('node').text
            if data.find('email'):
                response = LoginResponse(data)
                self.callback.on_login(response)
                self.api._establish_auth_connection()
            else:
                response = RegisterResponse(data)
                self.callback.on_register(response)
                self.api._establish_auth_connection()


class RosterHandler(Handler):
    def handle(self, data: BeautifulSoup):
        self.callback.on_roster(RosterResponse(data))


class MessageHandler(Handler):
    def handle(self, data: BeautifulSoup):
        if data['type'] == 'chat':
            if data.body:
                self.callback.on_message(MessageResponse(data))
            elif data.find('friend-attribution'):
                self.callback.on_friend_attribution(FriendAttributionResponse(data))
            elif data.find('status'):
                self.callback.on_status_message(StatusResponse(data))
            else:
                raise NotImplementedError
        elif data['type'] == 'receipt':
            if data.receipt['type'] == 'delivered':
                self.callback.on_message_delivered(MessageDeliveredResponse(data))
            else:
                self.callback.on_message_read(MessageReadResponse(data))
        elif data['type'] == 'is-typing':
            self.callback.on_is_typing(IsTypingResponse(data))
        elif data['type'] == 'groupchat':
            self.callback.on_group_status(GroupStatusResponse(data))
        else:
            raise NotImplementedError


class GroupMessageHandler(Handler):
    def handle(self, data: BeautifulSoup):
        if data.body:
            self.callback.on_group_message(GroupMessageResponse(data))
        elif data.find('is-typing'):
            self.callback.on_group_is_typing(GroupIsTypingResponse(data))
        else:
            raise NotImplementedError


class FriendMessageHandler(Handler):
    def handle(self, data: BeautifulSoup):
        self.callback.on_peer_info(FriendMessageResponse(data))
