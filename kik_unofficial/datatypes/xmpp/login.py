from bs4 import BeautifulSoup

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement
from kik_unofficial.utilities.cryptographics import CryptographicUtils

device_id = "167da12427ee4dc4a36b40e8debafc25"
kik_version = "11.1.1.12218"
android_id = "c10d47ba7ee17193"
captcha_element = '<challenge><response>{}</response></challenge>'


class LoginRequest(XMPPElement):
    def __init__(self, username, password, captcha_result=None):
        super().__init__()
        self.username = username
        self.password = password
        self.captcha_result = captcha_result

    def serialize(self) -> bytes:
        password_key = CryptographicUtils.key_from_password(self.username, self.password)
        captcha = captcha_element.format(self.captcha_result) if self.captcha_result else ''
        data = ('<iq type="set" id="{}">'
                '<query xmlns="jabber:iq:register">'
                '<username>{}</username>'
                '<passkey-u>{}</passkey-u>'
                '<device-id>{}</device-id>'
                '<install-referrer>utm_source=google-play&amp;utm_medium=organic</install-referrer>'
                '<operator>310260</operator>'
                '<install-date>1494078709023</install-date>'
                '<device-type>android</device-type>'
                '<brand>generic</brand>'
                '<logins-since-install>1</logins-since-install>'
                '<version>{}</version>'
                '<lang>en_US</lang>'
                '<android-sdk>19</android-sdk>'
                '<registrations-since-install>0</registrations-since-install>'
                '<prefix>CAN</prefix>'
                '<android-id>c10d47ba7ee17193</android-id>'
                '<model>Samsung Galaxy S5 - 4.4.4 - API 19 - 1080x1920</model>'
                '{}'
                '</query>'
                '</iq>').format(self.message_id, self.username, password_key, device_id, kik_version, captcha)
        return data.encode()


class LoginResponse:
    def __init__(self, data: BeautifulSoup):
        self.node = data.query.node.text
        self.email = data.query.email.text
        self.email_confirmed = data.query.email['confirmed'] == "true"
        self.username = data.query.username.text
        self.first = data.query.first.text
        self.last = data.query.last.text
        self.last = data.query.last.text