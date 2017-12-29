import base64
import binascii
import hashlib
import hmac

import rsa
from bs4 import BeautifulSoup
from kik_unofficial.cryptographic_utils import KikCryptographicUtils
from kik_unofficial.message.message import Message, Response

device_id = "167da12427ee4dc4a36b40e8debafc25"
kik_version = "11.1.1.12218"
android_id = "c10d47ba7ee17193"
captcha_element = '<challenge><response>{}</response></challenge>'


class LoginMessage(Message):
    def __init__(self, username, password, captcha_result=None):
        super().__init__()
        self.username = username
        self.password = password
        self.captcha_result = captcha_result

    def serialize(self) -> bytes:
        password_key = KikCryptographicUtils.key_from_password(self.username, self.password)
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


class RegisterMessage(Message):
    def __init__(self, email, username, password, first_name, last_name, birthday="1974-11-20", captcha_result=None):
        super().__init__()
        self.email = email
        self.username = username
        self.password = password
        self.first_name = first_name
        self.last_name = last_name
        self.birthday = birthday
        self.captcha_result = captcha_result

    def serialize(self):
        passkey_e = KikCryptographicUtils.key_from_password(self.email, self.password)
        passkey_u = KikCryptographicUtils.key_from_password(self.username, self.password)
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
                '</iq>').format(self.message_id, self.email, passkey_e, passkey_u, device_id, self.username,
                                self.first_name, self.last_name, self.birthday, captcha, kik_version, android_id)

        return data.encode()


class RegisterResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.node = data.query.node.text


class RegisterError(Response):
    error_messages = {
        409: "Already registered",
    }

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        error = data.find("error")
        self.code = int(error['code'])
        self.type = error['type']
        self.errors = [e.name for e in error.children]
        if self.code == 406:
            self.captcha_url = data.find('captcha-url').text + "&callback_url=https://kik.com/captcha-url"
            self.message = "Captcha required" if self.captcha_url is not None else "Password mismatch"
        else:
            self.message = self.error_messages[self.code]

    def __str__(self):
        return "IqError code={} type={} errors={}".format(self.code, self.type, ",".join(self.errors))


class EstablishConnectionMessage(Message):
    def __init__(self, node, username, password):
        super().__init__()
        self.node = node
        self.username = username
        self.password = password

    def serialize(self):
        jid = self.node + "@talk.kik.com"
        jid_with_resource = jid + "/CAN" + device_id
        timestamp = "1496333389122"
        sid = KikCryptographicUtils.make_kik_uuid()
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
        hmac_secret_key = KikCryptographicUtils.build_hmac_key()
        cv = binascii.hexlify(hmac.new(hmac_secret_key, hmac_data.encode(), hashlib.sha1).digest()).decode()

        password_key = KikCryptographicUtils.key_from_password(self.username, self.password)

        the_map = {'from': jid_with_resource, 'to': 'talk.kik.com', 'p': password_key, 'cv': cv, 'v': version,
                   'sid': sid, 'n': '1', 'conn': 'WIFI', 'ts': timestamp, 'lang': 'en_US', 'signed': signature}
        packet = KikCryptographicUtils.make_connection_payload(KikCryptographicUtils.sort_kik_map(the_map)).encode()
        return packet
