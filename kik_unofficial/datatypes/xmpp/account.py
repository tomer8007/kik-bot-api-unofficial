import datetime
from typing import Union

from bs4 import BeautifulSoup

from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse


class GetMyProfileRequest(XMPPElement):
    def __init__(self):
        super().__init__()

    def serialize(self) -> bytes:
        data = (f'<iq type="get" id="{self.message_id}">'
                '<query xmlns="kik:iq:user-profile" />'
                '</iq>')
        return data.encode()


class GetMyProfileResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.first_name = get_text_safe(data, "first")
        self.last_name = get_text_safe(data, "last")
        self.username = get_text_safe(data, "username")
        # Birthday set upon registration using date format yyyy-MM-dd
        # Server seems to default to 2000-01-01 if a birthday wasn't set during sign up
        self.birthday = get_text_safe(data, "birthday")
        # Token that is used to start the OAuth flow for Kik Live API requests
        self.session_token = get_text_safe(data, "session-token")
        # Token expiration date in ISO 8601 format
        # When the token expires, requesting your profile information again
        # should return the new session token.
        self.session_token_expiration = get_text_safe(data, "session-token-expiration")
        self.notify_new_people = get_text_safe(data, "notify-new-people") == "true"
        self.verified = bool(data.verified)
        if data.find("email"):
            self.email = data.find("email").text
            self.email_is_confirmed = data.find("email").get("confirmed") == "true"
        else:
            self.email = None
            self.email_is_confirmed = False
        self.pic_url = data.find("pic").text if data.find("pic") else None

    # Once the session token is expired, call get_my_profile again to get the new token
    def is_valid_token(self):
        if self.session_token is None or self.session_token_expiration is None:
            return False
        now = datetime.datetime.now()
        try:
            expire_time = datetime.datetime.strptime(self.session_token_expiration, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            return False

        return now < expire_time

    def __str__(self):
        return f'Username: {self.username}' \
               f'\nDisplay name: {self.first_name} {self.last_name}' \
               f'\nBirthday: {self.birthday}' \
               f'\nEmail: {self.email} (confirmed: {self.email_is_confirmed})' \
               f'\nPic: {self.pic_url + "/orig.jpg" if self.pic_url else "none"}'

    def __repr__(self):
        return f"GetMyProfileResponse(first_name={self.first_name}, last_name={self.last_name}, username={self.username}, birthday={self.birthday}, " \
               f"session_token={self.session_token}, session_token_expiration={self.session_token_expiration}, notify_new_people={self.notify_new_people}, " \
               f"verified={self.verified}, email={self.email}, email_is_confirmed={self.email_is_confirmed}, pic_url={self.pic_url})"


def get_text_safe(data: BeautifulSoup, tag: str):
    element = data.find(tag, recursive=False)
    return element.text if element else None


class GetMutedConvosResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup, convos: list):
        super().__init__(data)
        self.convos = convos

    def __repr__(self):
        return f'GetMutedConvosResponse(convos={self.convos})'

    class MutedConvo:
        def __init__(self, jid: str, mute_expires: Union[int, None]):
            self.jid = jid
            self.mute_expires = mute_expires

        def __repr__(self):
            return f'MutedConvo(jid={self.jid}, mute_expires={self.mute_expires})'


class ChangeNameRequest(XMPPElement):
    def __init__(self, first_name, last_name):
        super().__init__()
        self.first_name = first_name
        self.last_name = last_name

    def serialize(self) -> bytes:
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:iq:user-profile">'
                f'<first>{self.first_name}</first>'
                f'<last>{self.last_name}</last>'
                '</query>'
                '</iq>')
        return data.encode()


class ChangePasswordRequest(XMPPElement):
    def __init__(self, old_password, new_password, email, username):
        super().__init__()
        self.old_password = old_password
        self.new_password = new_password
        self.email = email
        self.username = username

    def serialize(self) -> bytes:
        passkey_e = CryptographicUtils.key_from_password(self.email, self.new_password)
        passkey_u = CryptographicUtils.key_from_password(self.username, self.new_password)
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:iq:user-profile">'
                f'<passkey-e>{passkey_e}</passkey-e>'
                f'<passkey-u>{passkey_u}</passkey-u>'
                '</query>'
                '</iq>')
        return data.encode()


class ChangeEmailRequest(XMPPElement):
    def __init__(self, password, new_email):
        super().__init__()
        self.password = password
        self.new_email = new_email

    def serialize(self) -> bytes:
        passkey_e = CryptographicUtils.key_from_password(self.new_email, self.password)
        data = (f'<iq type="set" id="{self.message_id}">'
                f'<query xmlns="kik:iq:user-profile">'
                f'<email>{self.new_email}</email>'
                f'<passkey-e>{passkey_e}</passkey-e>'
                f'</query>'
                f'</iq>')
        return data.encode()
