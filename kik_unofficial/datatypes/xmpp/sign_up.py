from bs4 import BeautifulSoup
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse
from kik_unofficial.device_configuration import device_id, android_id, kik_version_info
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils

captcha_element = '<challenge><response>{}</response></challenge>'


class RegisterRequest(XMPPElement):
    """
    Represents a Kik sign up request
    """

    def __init__(self, email, username, password, first_name, last_name, birthday="1974-11-20", captcha_result=None, device_id_override=None,
                 android_id_override=None):
        super().__init__()
        self.email = email
        self.username = username
        self.password = password
        self.first_name = first_name
        self.last_name = last_name
        self.birthday = birthday
        self.captcha_result = captcha_result
        self.device_id_override = device_id_override
        self.android_id_override = android_id_override

    def serialize(self):
        passkey_e = CryptographicUtils.key_from_password(self.email, self.password)
        passkey_u = CryptographicUtils.key_from_password(self.username, self.password)
        captcha = captcha_element.format(self.captcha_result) if self.captcha_result else ''
        data = ('<iq type="set" id="{}">'
                '<query xmlns="jabber:iq:register">'
                '<email>{}</email>'
                '<passkey-e>{}</passkey-e>'
                '<passkey-u>{}</passkey-u>'
                '<device-id>{}</device-id>'
                '<username>{}</username>'
                '<first>{}</first>'
                '<last>{}</last>'
                '<birthday>{}</birthday>'
                '{}'
                '<version>{}</version>'
                '<device-type>android</device-type>'
                '<model>Nexus 7</model>'
                '<android-sdk>25</android-sdk>'
                '<registrations-since-install>1</registrations-since-install>'
                '<install-date>unknown</install-date>'
                '<logins-since-install>0</logins-since-install>'
                '<prefix>CAN</prefix>'
                '<lang>en_US</lang>'
                '<brand>google</brand>'
                '<android-id>{}</android-id>'
                '</query>'
                '</iq>').format(self.message_id, self.email, passkey_e, passkey_u, self.device_id_override if self.device_id_override else device_id,
                                self.username, self.first_name, self.last_name, self.birthday, captcha, kik_version_info["kik_version"],
                                self.android_id_override if self.android_id_override else android_id)

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
        data = ('<iq type="get" id="{}">'
                '<query xmlns="kik:iq:check-unique">'
                '<username>{}</username>'
                '</query>'
                '</iq>').format(self.message_id, self.username)

        return data.encode()


class UsernameUniquenessResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        username_element = data.find('username')
        self.unique = True if username_element['is-unique'] == "true" else False
        self.username = username_element.text
