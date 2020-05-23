import base64
import bs4
import hashlib
import hmac
import logging
import pyDes
import rsa
import time

from kik_unofficial.device_configuration import device_id
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils


log = logging.getLogger(__name__)
identifierHex = "30820122300d06092a864886f70d01010105000382010f00"


class AuthStanza():
    client: 'KikClient' = None
    keyBytes: bytes = None
    secretKey: bytes = None
    public_key: rsa.key.PublicKey = None
    private_key: rsa.key.PrivateKey = None
    encrypted_public_key: bytes = None
    decrypted_public_key: bytes = None
    revalidate: int = None
    cert_url: str = None

    def __init__(self, client):
        self.client = client

    def sendStanza(self) -> None:
        """Send the outgoing auth stanza"""
        stanza = self.searlize()
        log.info('[+] Sending authentication certificate')
        self.client.loop.call_soon_threadsafe(self.client.connection.send_raw_data, stanza)

    def revalidator(self) -> None:
        """Revalidates the keys after n amount of time which is provided by Kik"""
        if time.time() < self.revalidate:
            return
        stanza = self.searlize()
        log.info('[+] Revalidating the authentication certificate')
        self.client.loop.call_soon_threadsafe(self.client.connection.send_raw_data, stanza)

    def searlize(self) -> bytes:
        """Generates/Gets the generated public key and builds an auth stanza"""
        UUID = CryptographicUtils.make_kik_uuid()
        der = self.getPublicKeyBase64()
        signature = self.getSignature()
        urlattr = f' url="{self.cert_url}"' if self.cert_url else ''

        query = (
            '<iq type="set" id="{}"><query xmlns="kik:auth:cert"{}>'
            '<key type="rsa">'
            '<der>{}</der><signature>{}</signature>'
            '</key>'
            '</query></iq>'
        ).format(UUID, urlattr, der, signature)
        return query.encode()

    def generateKeys(self) -> None:
        """Generate new 2048 bits RSA keys, could take from about a second to six"""
        (pubkey, privkey) = rsa.newkeys(2048)
        self.public_key = bytes.fromhex(identifierHex) + pubkey.save_pkcs1('DER')
        self.private_key = bytes.fromhex(identifierHex) + privkey.save_pkcs1('DER')

    def getKeyPhrase(self) -> bytes:
        """Salted username passkey"""
        username = self.client.username
        password = self.client.password
        return CryptographicUtils.key_from_password(username, password).encode()

    def getDESSecret(self) -> bytes:
        """The secret Kik uses for the DESKeySpec"""
        username = self.client.username
        device = self.client.device_id_override or device_id
        data = (device + '-' + username).encode()
        return hashlib.sha1(data).digest()

    def getPublicKeyBytes(self) -> bytes:
        """Generates all the secrets then encrypts and decrypts the public key"""
        if not self.public_key:
            self.generateKeys()
        if not (self.keyBytes and self.secretKey):
            key = self.DESKeySpec(self.getDESSecret())
            self.setParityBit(key, 0)
        if not self.decrypted_public_key:
            des = pyDes.des(self.secretKey, mode=pyDes.ECB, padmode=pyDes.PAD_PKCS5)
            self.encrypted_public_key = des.encrypt(self.public_key)
            self.decrypted_public_key = des.decrypt(self.encrypted_public_key)
        return self.decrypted_public_key

    def getPublicKeyBase64(self) -> str:
        """Base64 encodes the encrypted and decrypted data"""
        return base64.urlsafe_b64encode(self.getPublicKeyBytes()).decode()

    def DESKeySpec(self, key) -> bytes:
        """Equivalent to new DESKeySpec(key).getKey() in Java"""
        if not isinstance(key, bytes):
            key = bytes(key)
        self.keyBytes = key[:8]  # DES keys are only 8 bytes in length
        return self.keyBytes

    def getKey(self) -> bytes:
        """Returns the normal DESKey bytes"""
        return self.keyBytes

    def getSecretKey(self) -> bytes:
        """Returns the secret of the DESKey"""
        return self.secretKey

    def setParityBit(self, bArr: bytes, i: int = 0) -> bytes:
        """Same as calling generateSecret(DESKeySpec).getEncoded() in Java"""
        tmp = list(bArr)
        for _ in range(8):
            b = tmp[i] & 254
            tmp[i] = (((bin(b).count('1') & 1) ^ 1) | b)
            i = i + 1
        self.secretKey = bytes(tmp)
        return self.secretKey

    def getSignature(self) -> str:
        """Base64 of the encrypted and decrypted public key with our username passkey"""
        msg = self.getPublicKeyBytes()
        key = self.getKeyPhrase()
        digest = hashlib.sha1
        signature = hmac.new(key, msg, digest).digest()
        return base64.urlsafe_b64encode(signature).decode()

    def handle(self, data: bs4.BeautifulSoup):
        """Handle the response (result/error) sent by Kik"""
        if data.error:
            log.error('[!] kik:auth:cert [' + data.error.get('code') + '] ' + data.error.get_text())
            log.debug(str(data))
            return
        if data.find_all('regenerate-key', recursive=True):
            log.info('[!] Regenerating the keys for certificate authentication')
            self.teardown()
            self.sendStanza()
            return
        current = round(time.time() * 1000)
        revalidate = int(data.certificate.revalidate.text)
        self.cert_url = data.certificate.url.text
        self.revalidate = current + (revalidate * 1000)
        self.client.loop.call_later(revalidate, self.revalidator)
        log.info('[+] Successfully validated the authentication certificate')

    def teardown(self):
        """Remove all the generated data to build a new Key"""
        self.keyBytes = None
        self.secretKey = None
        self.public_key = None
        self.private_key = None
        self.encrypted_public_key = None
        self.decrypted_public_key = None
        self.revalidate = None
        self.cert_url = None
