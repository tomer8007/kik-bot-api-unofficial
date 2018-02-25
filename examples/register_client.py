import logging

from kik_unofficial.client import KikClient
from kik_unofficial.datatypes.callbacks import KikClientCallback
from kik_unofficial.datatypes.errors import SignUpError
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse
from kik_unofficial.datatypes.xmpp.sign_up import LoginResponse, RegisterResponse


class RegisterClient(KikClientCallback):
    def on_sign_up_ended(self, response: RegisterResponse):
        print("Registered on node {}.".format(response.node))

    def on_authorized(self):
        print("Authorized connection initiated.")
        client.request_roster()

    def on_login_ended(self, response: LoginResponse):
        print("Logged in as {}.".format(response.username))

    def on_register_error(self, response: SignUpError):
        if "captcha_url" in dir(response):
            print(response.captcha_url)
            result = input("Captcha result:")
            client.register(email, username, password, first, last, birthday, result)
        else:
            print("Unable to register! error information:\r\n{}".format(response))

    def on_roster_received(self, response: FetchRosterResponse):
        print("Friends: {}".format(response.members))


if __name__ == '__main__':
    username = input('Username: ')
    password = input('Password: ')
    first = input('First name: ')
    last = input('Last name: ')
    email = input('Email: ')
    birthday = input('Birthday: (like 01-01-1990): ')
    client = KikClient(callback=RegisterClient(), log_level=logging.DEBUG)
    client.register(email, username, password, first, last, birthday)
