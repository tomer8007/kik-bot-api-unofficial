import hashlib
import hmac
import rsa
import base64
import binascii
from bs4 import BeautifulSoup

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement
from kik_unofficial.utilities.cryptographics import CryptographicUtils
from kik_unofficial.device_configuration import device_id, kik_version, android_id

captcha_element = '<challenge><response>{}</response></challenge>'


class LoginRequest(XMPPElement):
    """
    Represents a Kik Login request.
    """
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
                '<android-id>{}</android-id>'
                '<model>Samsung Galaxy S5 - 4.4.4 - API 19 - 1080x1920</model>'
                '{}'
                '</query>'
                '</iq>').format(self.message_id, self.username, password_key,
                                device_id, kik_version, android_id, captcha)
        return data.encode()


class LoginResponse:
    """
    Represents a Kik Login response.
    """
    def __init__(self, data: BeautifulSoup):
        self.kik_node = data.query.node.text
        self.email = data.query.email.text
        self.is_email_confirmed = data.query.email['confirmed'] == "true"
        self.username = data.query.username.text
        self.first_name = data.query.first.text
        self.last_name = data.query.last.text


class EstablishAuthenticatedSessionRequest(XMPPElement):
    """
    a request sent on the begging of the connection to establish
    an authenticated session. That is, on the behalf of a specific kik user, with his credentials.
    """
    def __init__(self, node, username, password):
        super().__init__()
        self.node = node
        self.username = username
        self.password = password

    def serialize(self):
        jid = self.node + "@talk.kik.com"
        jid_with_resource = jid + "/CAN" + device_id
        timestamp = "1496333389122"
        sid = CryptographicUtils.make_kik_uuid()
        version = "11.1.1.12218"

        # some super secret cryptographic stuff
        private_key_pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIBPAIBAAJBANEWUEINqV1KNG7Yie9GSM8t75ZvdTeqT7kOF40kvDHIp" \
                          "/C3tX2bcNgLTnGFs8yA2m2p7hKoFLoxh64vZx5fZykCAwEAAQJAT" \
                          "/hC1iC3iHDbQRIdH6E4M9WT72vN326Kc3MKWveT603sUAWFlaEa5T80GBiP/qXt9PaDoJWcdKHr7RqDq" \
                          "+8noQIhAPh5haTSGu0MFs0YiLRLqirJWXa4QPm4W5nz5VGKXaKtAiEA12tpUlkyxJBuuKCykIQbiUXHEwzFYbMHK5E" \
                          "/uGkFoe0CIQC6uYgHPqVhcm5IHqHM6/erQ7jpkLmzcCnWXgT87ABF2QIhAIzrfyKXp1ZfBY9R0H4pbboHI4uatySKc" \
                          "Q5XHlAMo9qhAiEA43zuIMknJSGwa2zLt/3FmVnuCInD6Oun5dbcYnqraJo=\n-----END RSA PRIVATE KEY----- "
        private_key = rsa.PrivateKey.load_pkcs1(private_key_pem, format='PEM')
        signature = rsa.sign("{}:{}:{}:{}".format(jid, version, timestamp, sid).encode(), private_key, 'SHA-256')
        signature = base64.b64encode(signature, '-_'.encode()).decode()[:-2]
        hmac_data = timestamp + ":" + jid
        hmac_secret_key = CryptographicUtils.build_hmac_key()
        cv = binascii.hexlify(hmac.new(hmac_secret_key, hmac_data.encode(), hashlib.sha1).digest()).decode()

        password_key = CryptographicUtils.key_from_password(self.username, self.password)

        the_map = {'from': jid_with_resource, 'to': 'talk.kik.com', 'p': password_key, 'cv': cv, 'v': version,
                   'sid': sid, 'n': '1', 'conn': 'WIFI', 'ts': timestamp, 'lang': 'en_US', 'signed': signature}
        packet = CryptographicUtils.make_connection_payload(CryptographicUtils.sort_kik_map(the_map)).encode()
        return packet


class ConnectionFailedResponse:
    def __init__(self, data: BeautifulSoup):
        self.message = data.find('msg').text
