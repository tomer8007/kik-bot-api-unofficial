import base64
import binascii
import hashlib
import hmac

import rsa
from bs4 import BeautifulSoup
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement
from kik_unofficial.device_configuration import device_id, kik_version_info, android_id
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils

captcha_element = '<challenge><response>{}</response></challenge>'
kik_version = kik_version_info["kik_version"]


class LoginRequest(XMPPElement):
    """
    Represents a Kik Login request.
    """
    def __init__(self, username, password, captcha_result=None, device_id_override=None, android_id_override=None):
        super().__init__()
        self.username = username
        self.password = password
        self.captcha_result = captcha_result
        self.device_id_override = device_id_override
        self.android_id_override = android_id_override

    def serialize(self) -> bytes:
        password_key = CryptographicUtils.key_from_password(self.username, self.password)
        captcha = captcha_element.format(self.captcha_result) if self.captcha_result else ''
        if '@' in self.username:
            tag = ('<email>{}</email>'
                   '<passkey-e>{}</passkey-e>')
        else:
            tag = ('<username>{}</username>'
                   '<passkey-u>{}</passkey-u>')

        data = ('<iq type="set" id="{}">'
                '<query xmlns="jabber:iq:register">'
                '{}'
                '<device-id>{}</device-id>'
                '<install-referrer>utm_source=google-play&amp;utm_medium=organic</install-referrer>'
                '<operator>unknown</operator>'
                '<install-date>unknown</install-date>'
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
                '</iq>').format(self.message_id, tag.format(self.username, password_key),
                                self.device_id_override if self.device_id_override else device_id,
                                kik_version, self.android_id_override if self.android_id_override else android_id, captcha)
        return data.encode()


class LoginResponse:
    """
    Represents a Kik Login response that is received after a log-in attempt.
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
    def __init__(self, node, username, password, device_id_override=None):
        super().__init__()
        self.node = node
        self.username = username
        self.password = password
        self.device_id_override = device_id_override

    def serialize(self):
        jid = self.node + "@talk.kik.com"
        jid_with_resource = jid + "/CAN" + (self.device_id_override if self.device_id_override else device_id)
        timestamp = str(CryptographicUtils.make_kik_timestamp())
        sid = CryptographicUtils.make_kik_uuid()

        # some super secret cryptographic stuff
        private_key_pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIBPAIBAAJBANEWUEINqV1KNG7Yie9GSM8t75ZvdTeqT7kOF40kvDHIp" \
                          "/C3tX2bcNgLTnGFs8yA2m2p7hKoFLoxh64vZx5fZykCAwEAAQJAT" \
                          "/hC1iC3iHDbQRIdH6E4M9WT72vN326Kc3MKWveT603sUAWFlaEa5T80GBiP/qXt9PaDoJWcdKHr7RqDq" \
                          "+8noQIhAPh5haTSGu0MFs0YiLRLqirJWXa4QPm4W5nz5VGKXaKtAiEA12tpUlkyxJBuuKCykIQbiUXHEwzFYbMHK5E" \
                          "/uGkFoe0CIQC6uYgHPqVhcm5IHqHM6/erQ7jpkLmzcCnWXgT87ABF2QIhAIzrfyKXp1ZfBY9R0H4pbboHI4uatySKc" \
                          "Q5XHlAMo9qhAiEA43zuIMknJSGwa2zLt/3FmVnuCInD6Oun5dbcYnqraJo=\n-----END RSA PRIVATE KEY----- "
        private_key = rsa.PrivateKey.load_pkcs1(private_key_pem, format='PEM')
        signature = rsa.sign("{}:{}:{}:{}".format(jid, kik_version, timestamp, sid).encode(), private_key, 'SHA-256')
        signature = base64.b64encode(signature, '-_'.encode()).decode()[:-2]
        hmac_data = timestamp + ":" + jid
        hmac_secret_key = CryptographicUtils.build_hmac_key()
        cv = binascii.hexlify(hmac.new(hmac_secret_key, hmac_data.encode(), hashlib.sha1).digest()).decode()

        password_key = CryptographicUtils.key_from_password(self.username, self.password)

        the_map = {'from': jid_with_resource, 'to': 'talk.kik.com', 'p': password_key, 'cv': cv, 'v': kik_version,
                   'sid': sid, 'n': '1', 'conn': 'WIFI', 'ts': timestamp, 'lang': 'en_US', 'signed': signature}
        packet = CryptographicUtils.make_connection_payload(CryptographicUtils.sort_kik_map(the_map)).encode()
        return packet


class ConnectionFailedResponse:
    def __init__(self, data: BeautifulSoup):
        self.message = data.find('msg').text


class CaptchaElement:
    """
    The 'stc' element is received when Kik requires a captcha to be filled in, it's followed up by a 'hold' element after
    which the connection is paused.
    """
    def __init__(self, data: BeautifulSoup):
        self.type = data.stp['type']
        self.captcha_url = data.stp.text + "&callback_url=https://kik.com/captcha-url"
        self.stc_id = data['id']


class CaptchaSolveRequest(XMPPElement):
    """
    Response to the 'stc' element. Given the result of the captcha, the connection will resume.
    """
    def __init__(self, stc_id: str, captcha_result: str):
        super().__init__()
        self.captcha_result = captcha_result
        self.stc_id = stc_id

    def serialize(self) -> bytes:
        data = (
            '<stc id="{}">'
            '<sts>{}</sts>'
            '</stc>'
        ).format(self.stc_id, self.captcha_result)
        return data.encode()
