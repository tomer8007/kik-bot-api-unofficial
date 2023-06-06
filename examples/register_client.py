#!/usr/bin/env python3

import argparse
import logging
import yaml

from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.errors import SignUpError
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse
from kik_unofficial.datatypes.xmpp.login import LoginResponse
from kik_unofficial.datatypes.xmpp.sign_up import RegisterResponse
from kik_unofficial.utilities.credential_utilities import random_device_id, random_android_id

class RegisterClient(KikClientCallback):
    def on_sign_up_ended(self, response: RegisterResponse):
        print(f"Registered on node {response.kik_node}.")

    def on_authenticated(self):
        print("Authorized connection initiated.")
        client.request_roster()

    def on_login_ended(self, response: LoginResponse):
        print(f"Logged in as {response.username}.")

    def on_register_error(self, response: SignUpError):
        if "captcha_url" in dir(response):
            print(response.captcha_url)
            result = input("Captcha result:")
            client.register(args.email, args.username, args.password,
                    args.firstname, args.lastname, args.birthday, result)
        else:
            print(f"Unable to register! error information:\r\n{response}")

    def on_roster_received(self, response: FetchRosterResponse):
        print(f"Friends: {response.peers}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('email')
    parser.add_argument('-p', '--password')
    parser.add_argument('--firstname', default='Not A')
    parser.add_argument('--lastname', default='Human')
    parser.add_argument('--birthday', default='01-01-1990')
    parser.add_argument('--credentials-file', default='new_creds.yaml')
    args = parser.parse_args()
    if args.password is None:
        args.password = input('Password: ')

    device_id = random_device_id()
    android_id = random_android_id()
    logging.basicConfig(format=KikClient.log_format(), level=logging.DEBUG)
    client = KikClient(callback=RegisterClient(),
                       kik_username=None, kik_password=None, 
                       device_id=device_id, android_id=android_id)
    client.register(args.email, args.username, args.password,
            args.firstname, args.lastname, args.birthday)

    file_obj = {
            'device_id': device_id,
            'android_id': android_id,
            'username': args.username,
            'password': args.password,
            'node': client.kik_node,
            }
    with open(args.credentials_file, 'w') as f:
        yaml.dump(file_obj, f)

    client.wait_for_messages()
