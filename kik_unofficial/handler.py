from bs4 import BeautifulSoup
from kik_unofficial.api import KikCallback
from kik_unofficial.message.roster import RosterResponse
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
            self.callback.on_register_error(RegisterError(data))
        elif message_type == "result":
            if data.find('email'):
                response = LoginResponse(data)
                self.callback.on_login(response)
                self.api.establish_connection(response.node, self.api.username, self.api.password)
            else:
                response = RegisterResponse(data)
                self.callback.on_register(response)
                self.api.establish_connection(response.node, self.api.username, self.api.password)


class RosterHandler(Handler):
    def handle(self, data: BeautifulSoup):
        self.callback.on_roster(RosterResponse(data))