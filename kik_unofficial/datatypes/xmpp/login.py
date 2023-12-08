import base64
import binascii
import hashlib
import hmac
import uuid

import rsa
from bs4 import BeautifulSoup
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement
from kik_unofficial.device_configuration import kik_version_info
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils
from kik_unofficial.utilities.parsing_utilities import is_tag_present

kik_version = kik_version_info["kik_version"]

private_key_pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIBPAIBAAJBANEWUEINqV1KNG7Yie9GSM8t75ZvdTeqT7kOF40kvDHIp" \
                  "/C3tX2bcNgLTnGFs8yA2m2p7hKoFLoxh64vZx5fZykCAwEAAQJAT" \
                  "/hC1iC3iHDbQRIdH6E4M9WT72vN326Kc3MKWveT603sUAWFlaEa5T80GBiP/qXt9PaDoJWcdKHr7RqDq" \
                  "+8noQIhAPh5haTSGu0MFs0YiLRLqirJWXa4QPm4W5nz5VGKXaKtAiEA12tpUlkyxJBuuKCykIQbiUXHEwzFYbMHK5E" \
                  "/uGkFoe0CIQC6uYgHPqVhcm5IHqHM6/erQ7jpkLmzcCnWXgT87ABF2QIhAIzrfyKXp1ZfBY9R0H4pbboHI4uatySKc" \
                  "Q5XHlAMo9qhAiEA43zuIMknJSGwa2zLt/3FmVnuCInD6Oun5dbcYnqraJo=\n-----END RSA PRIVATE KEY----- "
private_key = rsa.PrivateKey.load_pkcs1(private_key_pem.encode('utf-8'), format='PEM')


class LoginRequest(XMPPElement):
    """
    Represents a Kik Login request.
    """

    def __init__(self, email_or_username, password, captcha_result=None, device_id=None, android_id=None):
        super().__init__()
        self.email_or_username = email_or_username
        self.password = password
        self.captcha_result = captcha_result
        self.device_id = device_id
        self.android_id = android_id

    def serialize(self) -> bytes:
        password_key = CryptographicUtils.key_from_password(self.email_or_username, self.password)
        captcha = f'<challenge><response>{self.captcha_result}</response></challenge>' if self.captcha_result else ''

        if '@' in self.email_or_username:
            creds = f'<email>{self.email_or_username}</email><passkey-e>{password_key}</passkey-e>'
        else:
            creds = f'<username>{self.email_or_username}</username><passkey-u>{password_key}</passkey-u>'

        data = (f'<iq type="set" id="{self.message_id}">'
                f'<query xmlns="jabber:iq:register">'
                f'{creds}'
                f'<device-id>{self.device_id}</device-id>'
                '<install-referrer>utm_source=google-play&amp;utm_medium=organic</install-referrer>'
                '<operator>unknown</operator>'
                '<install-date>unknown</install-date>'
                '<device-type>android</device-type>'
                '<brand>samsung</brand>'
                '<logins-since-install>0</logins-since-install>'
                f'<version>{kik_version}</version>'
                '<lang>en_US</lang>'
                '<android-sdk>34</android-sdk>'
                '<registrations-since-install>0</registrations-since-install>'
                '<prefix>CAN</prefix>'
                f'<android-id>{self.android_id}</android-id>'
                '<model>Samsung Galaxy S23 Ultra</model>'
                f'{captcha}'
                '</query>'
                '</iq>')

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


class MakeAnonymousStreamInitTag(XMPPElement):
    def __init__(self, device_id=None, n=1):
        super().__init__()
        self.device_id = device_id
        self.n = n

    def serialize(self) -> bytes:
        can = 'CAN'  # XmppSocketV2.java line 180, 

        device = self.device_id
        timestamp = str(CryptographicUtils.make_kik_timestamp())
        sid = str(uuid.uuid4())

        signature = rsa.sign(f"{can + device}:{kik_version}:{timestamp}:{sid}".encode(), private_key, 'SHA-256')
        signature = base64.b64encode(signature, '-_'.encode()).decode().rstrip('=')

        hmac_data = f"{timestamp}:{can}{device}"
        hmac_secret_key = CryptographicUtils.build_hmac_key()
        cv = binascii.hexlify(hmac.new(hmac_secret_key, hmac_data.encode(), hashlib.sha1).digest()).decode()

        the_map = {
            'signed': signature,
            'lang': 'en_US',
            'sid': sid,
            'anon': '1',
            'ts': timestamp,
            'v': kik_version,
            'cv': cv,
            'conn': 'WIFI',
            'dev': can + device,
        }

        # Test data to confirm the sort_kik_map function returns the correct result.
        # the_map = { 
        #     'signed': 'signature',
        #     'lang': 'en_US',
        #     'sid': 'sid',
        #     'anon': '1',
        #     'ts': 'timestamp',
        #     'v': 'kik_version',
        #     'cv': 'cv',
        #     'conn': 'WIFI',
        #     'dev': 'can+device',
        # }

        if self.n > 0:
            the_map['n'] = self.n

        packet = CryptographicUtils.make_connection_payload(*CryptographicUtils.sort_kik_map(the_map))
        return packet.encode()


class EstablishAuthenticatedSessionRequest(XMPPElement):
    """
    a request sent on the begging of the connection to establish
    an authenticated session. That is, on the behalf of a specific kik user, with his credentials.
    """

    def __init__(self, node, username, password, device_id=None):
        super().__init__()
        self.node = node
        self.username = username
        self.password = password
        self.device_id = device_id

    def serialize(self) -> bytes:
        jid = f"{self.node}@talk.kik.com"
        jid_with_resource = f"{jid}/CAN{self.device_id}"
        timestamp = str(CryptographicUtils.make_kik_timestamp())
        sid = str(uuid.uuid4())

        # some super secret cryptographic stuff

        signature = rsa.sign(f"{jid}:{kik_version}:{timestamp}:{sid}".encode(), private_key, 'SHA-256')
        signature = base64.b64encode(signature, '-_'.encode()).decode().rstrip('=')
        hmac_data = f"{timestamp}:{jid}"
        hmac_secret_key = CryptographicUtils.build_hmac_key()
        cv = binascii.hexlify(hmac.new(hmac_secret_key, hmac_data.encode(), hashlib.sha1).digest()).decode()

        password_key = CryptographicUtils.key_from_password(self.username, self.password)

        the_map = {
            'from': jid_with_resource,
            'to': 'talk.kik.com',
            'p': password_key,
            'cv': cv,
            'v': kik_version,
            'sid': sid,
            'n': '1',
            'conn': 'WIFI',
            'ts': timestamp,
            'lang': 'en_US',
            'signed': signature
        }
        packet = CryptographicUtils.make_connection_payload(*CryptographicUtils.sort_kik_map(the_map))
        return packet.encode()


class ConnectionFailedResponse:
    """
    Describes an error response when attempting to connect.
    """
    def __init__(self, data: BeautifulSoup):
        """True if the password / device ID pair was invalidated (auth rejected)"""
        self.is_auth_revoked = is_tag_present(data, 'noauth')
        """the error message received. Will be an empty string if is_auth_revoked = False"""
        self.message = data.noauth.msg.text if is_tag_present(data, 'noauth') else ''

        """True if a backoff was requested by Kik's server"""
        self.is_backoff = is_tag_present(data, 'wait')
        if self.is_backoff:
            """
            the number of seconds that Kik requested the client to wait for before reconnecting. 
            Will be undefined if is_backoff = False
            """
            self.backoff_seconds = int(data.find('wait', recursive=False)['t'])


class CaptchaElement:
    """
    The 'stc' element is received when Kik requires a captcha to be filled in, it's followed up by a 'hold' element after
    which the connection is paused.
    """

    def __init__(self, data: BeautifulSoup):
        self.type = data.stp['type']
        self.captcha_url = f"{data.stp.text}&callback_url=https://kik.com/captcha-url"
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
        data = f'<stc id="{self.stc_id}"><sts>{self.captcha_result}</sts></stc>'
        return data.encode()


class TempBanElement:
    """
    When this is received, you will not be able to send or receive any stanzas until after the ban time
    """

    def __init__(self, data: BeautifulSoup):
        self.type = data.stp['type']
        self.stc_id = data['id']
        self.ban_title = data.dialog.find('dialog-title').text
        self.ban_message = data.dialog.find('dialog-body').text
        self.ban_end_time = int(data.dialog.find('ban-end').text)
