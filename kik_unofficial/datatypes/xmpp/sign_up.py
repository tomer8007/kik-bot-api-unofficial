from bs4 import BeautifulSoup
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse
from kik_unofficial.device_configuration import kik_version_info
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils


class RegisterRequest(XMPPElement):
    """
    Represents a Kik sign up request
    """

    def __init__(self, email, username, password, first_name, last_name, birthday, captcha_result=None, device_id=None,
                 android_id=None):
        super().__init__()
        self.email = email
        self.username = username
        self.password = password
        self.first_name = first_name
        self.last_name = last_name
        self.birthday = birthday
        self.captcha_result = captcha_result
        self.device_id = device_id
        self.android_id = android_id

    def serialize(self) -> bytes:
        passkey_e = CryptographicUtils.key_from_password(self.email, self.password)
        passkey_u = CryptographicUtils.key_from_password(self.username, self.password)
        captcha = f'<challenge><response>{self.captcha_result}</response></challenge>' if self.captcha_result else ''
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="jabber:iq:register">'
                f'<email>{self.email}</email>'
                f'<passkey-e>{passkey_e}</passkey-e>'
                f'<passkey-u>{passkey_u}</passkey-u>'
                f'<device-id>{self.device_id}</device-id>'
                f'<username>{self.username}</username>'
                f'<first>{self.first_name}</first>'
                f'<last>{self.last_name}</last>'
                f'<birthday>{self.birthday}</birthday>'
                f'{captcha}'
                f'<version>{kik_version_info["kik_version"]}</version>'
                '<device-type>android</device-type>'
                '<model>Samsung Galaxy S23 Ultra</model>'
                '<android-sdk>34</android-sdk>'
                '<registrations-since-install>0</registrations-since-install>'
                '<install-date>unknown</install-date>'
                '<logins-since-install>0</logins-since-install>'
                '<prefix>CAN</prefix>'
                '<lang>en_US</lang>'
                '<brand>samsung</brand>'
                f'<android-id>{self.android_id}</android-id>'
                '</query>'
                '</iq>')

        return data.encode()


class RegisterResponse(XMPPResponse):
    """
    Represents a response for a Kik sign up request.
    """
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.kik_node = data.query.node.text


class CheckUsernameUniquenessRequest(XMPPElement):
    def __init__(self, username):
        super().__init__()
        self.username = username

    def serialize(self) -> bytes:
        data = (f'<iq type="get" id="{self.message_id}">'
                '<query xmlns="kik:iq:check-unique">'
                f'<username>{self.username}</username>'
                '</query>'
                '</iq>')

        return data.encode()


class UsernameUniquenessResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        username_element = data.find('username')
        self.unique = username_element['is-unique'] == "true"
        self.username = username_element.text
