import datetime

from bs4 import BeautifulSoup

from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse


class GetMyProfileRequest(XMPPElement):
    def __init__(self):
        super().__init__()

    def serialize(self) -> bytes:
        data = ('<iq type="get" id="{}">'
                '<query xmlns="kik:iq:user-profile" />'
                '</iq>').format(self.message_id)
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
        self.notify_new_people = True if get_text_safe(data, "notify-new-people") == "true" else False
        self.verified = True if data.verified else False
        if data.find("email"):
            self.email = data.find("email").text
            self.email_is_confirmed = "true" == data.find("email").get("confirmed")
        else:
            self.email = None
            self.email_is_confirmed = False
        if data.find("pic"):
            # append /orig.jpg for the full resolution
            # append /thumb.jpg for a smaller resolution
            self.pic_url = data.find("pic").text
        else:
            self.pic_url = None

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
        return "GetMyProfileResponse(first_name={}, last_name={}, username={}, birthday={}, " \
               "session_token={}, session_token_expiration={}, notify_new_people={}, " \
               "verified={}, email={}, email_is_confirmed={}, pic_url={})".format(self.first_name, self.last_name,
                                                                                  self.username, self.birthday,
                                                                                  self.session_token,
                                                                                  self.session_token_expiration,
                                                                                  self.notify_new_people, self.verified,
                                                                                  self.email, self.email_is_confirmed,
                                                                                  self.pic_url)


def get_text_safe(data: BeautifulSoup, tag: str):
    return data.find(tag).text if data.find(tag) else None


class ChangeNameRequest(XMPPElement):
    def __init__(self, first_name, last_name):
        super().__init__()
        self.first_name = first_name
        self.last_name = last_name

    def serialize(self) -> bytes:
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:iq:user-profile">'
                '<first>{}</first>'
                '<last>{}</last>'
                '</query>'
                '</iq>').format(self.message_id, self.first_name, self.last_name)
        return data.encode()


class ChangePasswordRequest(XMPPElement):
    def __init__(self, old_password, new_password, email, username):
        super().__init__()
        self.old_password = old_password
        self.new_password = new_password
        self.email = email
        self.username = username

    def serialize(self):
        passkey_e = CryptographicUtils.key_from_password(self.email, self.old_password)
        passkey_u = CryptographicUtils.key_from_password(self.username, self.new_password)
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:iq:user-profile">'
                '<passkey-e>{}</passkey-e>'
                '<passkey-u>{}</passkey-u>'
                '</query>'
                '</iq>').format(self.message_id, passkey_e, passkey_u)
        return data.encode()


class ChangeEmailRequest(XMPPElement):
    def __init__(self, password, old_email, new_email):
        super().__init__()
        self.password = password
        self.old_email = old_email
        self.new_email = new_email

    def serialize(self):
        passkey_e = CryptographicUtils.key_from_password(self.old_email, self.password)
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:iq:user-profile">'
                '<email>{}</email>'
                '<passkey-e>{}</passkey-e>'
                '</query>'
                '</iq>').format(self.message_id, self.new_email, passkey_e)
        return data.encode()
