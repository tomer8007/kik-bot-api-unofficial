import logging

from kik_unofficial.api import KikApi
from kik_unofficial.callback import KikAdapter
from kik_unofficial.message.roster import RosterResponse
from kik_unofficial.message.unauthorized.register import RegisterError, LoginResponse, RegisterResponse


class RegisterClient(KikAdapter):
    def on_register(self, response: RegisterResponse):
        print("Registered on node {}.".format(response.node))

    def on_authorized(self):
        print("Authorized connection initiated.")
        client.request_roster()

    def on_login(self, response: LoginResponse):
        print("Logged in as {}.".format(response.username))

    def on_register_error(self, response: RegisterError):
        if response.captcha_url:
            print(response.captcha_url)
            result = input("Captcha result:")
            client.register(email, username, password, first, last, birthday, result)

    def on_roster(self, response: RosterResponse):
        print("Friends: {}".format(response.members))


if __name__ == '__main__':
    username = input('Username: ')
    password = input('Password: ')
    first = input('First name: ')
    last = input('Last name: ')
    email = input('Email: ')
    birthday = input('Birthday: (like 01-01-1990): ')
    client = KikApi(callback=RegisterClient(), loglevel=logging.DEBUG)
    client.register(email, username, password, first, last, birthday)
