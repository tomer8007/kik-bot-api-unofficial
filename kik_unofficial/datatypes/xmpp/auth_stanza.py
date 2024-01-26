import base64
import bs4
import hashlib
import hmac
import logging
import pyDes
import rsa

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils
from kik_unofficial.utilities.kik_server_clock import KikServerClock

log = logging.getLogger(__name__)
identifierHex = "30820122300d06092a864886f70d01010105000382010f00"


class AuthStanza(XMPPElement):
    client = None
    des_key_bytes: bytes = None
    des_secret_key: bytes = None
    rsa_public_key: bytes = None
    rsa_private_key: bytes = None
    encrypted_rsa_public_key: bytes = None
    decrypted_rsa_public_key: bytes = None
    cert_revalidate_time: int = None
    cert_url: str = None

    def __init__(self, client):
        super().__init__()
        self.client = client

    def send_stanza(self) -> None:
        """
        Send the outgoing auth stanza
        """
        stanza = self.serialize()
        log.info("Sending authentication certificate")
        self.client.loop.call_soon_threadsafe(self.client.connection.send_raw_data, stanza)

    def revalidate(self) -> None:
        """
        Revalidates the keys after n amount of time which is provided by Kik
        """
        if KikServerClock.get_server_time() < self.cert_revalidate_time:
            return
        stanza = self.serialize()
        log.info("Revalidating the authentication certificate")
        self.client.loop.call_soon_threadsafe(self.client.connection.send_raw_data, stanza)

    def serialize(self) -> bytes:
        """
        Generates/Gets the generated public key and builds an auth stanza
        """
        der = self.get_public_key_base64()
        signature = self.get_signature()
        urlattr = f' url="{self.cert_url}"' if self.cert_url else ""

        query = (
            f'<iq type="set" id="{self.message_id}"><query xmlns="kik:auth:cert"{urlattr}>'
            '<key type="rsa">'
            f"<der>{der}</der><signature>{signature}</signature>"
            "</key>"
            "</query></iq>"
        )
        return query.encode()

    def generate_keys(self) -> None:
        """
        Generate new 2048 bits RSA keys, could take from about a second to six
        """
        (pubkey, privkey) = rsa.newkeys(2048)
        self.rsa_public_key = bytes.fromhex(identifierHex) + pubkey.save_pkcs1("DER")
        self.rsa_private_key = bytes.fromhex(identifierHex) + privkey.save_pkcs1("DER")

    def get_key_phrase(self) -> bytes:
        """
        Calculates salted username passkey
        """
        username = self.client.username
        password = self.client.password
        return CryptographicUtils.key_from_password(username, password).encode()

    def get_des_secret(self) -> bytes:
        """
        The secret Kik uses for the DESKeySpec
        """
        username = self.client.username
        device = self.client.device_id
        data = (device + "-" + username).encode()
        return hashlib.sha1(data).digest()

    def get_public_key_bytes(self) -> bytes:
        """
        Generates all the secrets then encrypts and decrypts the public key
        """
        if not self.rsa_public_key:
            self.generate_keys()
        if not (self.des_key_bytes and self.des_secret_key):
            key = self.get_des_key(self.get_des_secret())
            self.get_parity_bit(key, 0)
        if not self.decrypted_rsa_public_key:
            des = pyDes.des(self.des_secret_key, mode=pyDes.ECB, padmode=pyDes.PAD_PKCS5)
            self.encrypted_rsa_public_key = des.encrypt(self.rsa_public_key)
            self.decrypted_rsa_public_key = des.decrypt(self.encrypted_rsa_public_key)
        return self.decrypted_rsa_public_key

    def get_public_key_base64(self) -> str:
        """
        Base64 encodes the encrypted and decrypted data
        """
        return base64.urlsafe_b64encode(self.get_public_key_bytes()).decode()

    def get_des_key(self, key) -> bytes:
        """
        Equivalent to new DESKeySpec(key).getKey() in Java
        """
        if not isinstance(key, bytes):
            key = bytes(key)
        self.des_key_bytes = key[:8]  # DES keys are only 8 bytes in length
        return self.des_key_bytes

    def get_key(self) -> bytes:
        """
        Returns the normal DESKey bytes
        """
        return self.des_key_bytes

    def get_secret_key(self) -> bytes:
        """
        Returns the secret of the DESKey
        """
        return self.des_secret_key

    def get_parity_bit(self, byte_array: bytes, i: int = 0) -> bytes:
        """
        Same as calling generateSecret(DESKeySpec).getEncoded() in Java
        """
        tmp = list(byte_array)
        for _ in range(8):
            b = tmp[i] & 254
            tmp[i] = ((bin(b).count("1") & 1) ^ 1) | b
            i = i + 1
        self.des_secret_key = bytes(tmp)
        return self.des_secret_key

    def get_signature(self) -> str:
        """
        Base64 of the encrypted and decrypted public key with our username passkey
        """
        msg = self.get_public_key_bytes()
        key = self.get_key_phrase()
        digest = hashlib.sha1
        signature = hmac.new(key, msg, digest).digest()
        return base64.urlsafe_b64encode(signature).decode()

    def handle(self, data: bs4.BeautifulSoup):
        """
        Handles the auth response (result/error) sent by Kik
        """
        if data.error:
            log.error("kik:auth:cert [" + data.error.get("code") + "] " + data.error.get_text())
            log.debug(str(data))
            return
        if data.find("regenerate-key", recursive=True):
            log.info("Regenerating the keys for certificate authentication")
            self.teardown()
            self.send_stanza()
            return
        current = KikServerClock.get_server_time()
        revalidate = int(data.certificate.revalidate.text)
        self.cert_url = data.certificate.url.text
        self.cert_revalidate_time = current + (revalidate * 1000)
        self.client.loop.call_later(revalidate, self.revalidate)
        log.info("Successfully validated the authentication certificate")

    def teardown(self):
        """
        Removes all the generated data to build a new Key
        """
        self.des_key_bytes = None
        self.des_secret_key = None
        self.rsa_public_key = None
        self.rsa_private_key = None
        self.encrypted_rsa_public_key = None
        self.decrypted_rsa_public_key = None
        self.cert_url = None
        self.cert_revalidate_time = None
