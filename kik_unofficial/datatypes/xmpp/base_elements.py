import base64
import binascii
import uuid
from typing import Union

from bs4 import BeautifulSoup
from lxml.etree import Element

from kik_unofficial.utilities import jid_utilities
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils
from kik_unofficial.utilities.kik_server_clock import KikServerClock


class XMPPElement:
    def __init__(self):
        self.message_id = CryptographicUtils.make_kik_uuid()

    def serialize(self) -> Union[bytes, Element]:
        raise NotImplementedError


class XMPPOutgoingMessageElement(XMPPElement):
    def __init__(self, peer_jid: str):
        super().__init__()
        self.peer_jid = peer_jid
        self.is_group = jid_utilities.is_group_jid(peer_jid)
        self.timestamp = str(KikServerClock.get_server_time())
        self.message_type = "groupchat" if self.is_group else "chat"
        self.xmlns = "kik:groups" if self.is_group else "jabber:client"


class XMPPOutgoingContentMessageElement(XMPPOutgoingMessageElement):
    def __init__(self, peer_jid: str):
        super().__init__(peer_jid)
        self.content_id = str(uuid.uuid4())  # content ids arent cryptographic


class XMPPOutgoingIsTypingMessageElement(XMPPOutgoingMessageElement):
    def __init__(self, peer_jid: str, is_typing: bool):
        super().__init__(peer_jid)
        self.message_type = 'is-typing'  # IsTyping messages always use this type, even if it's to a group
        self.is_typing = is_typing       # type: bool


class XMPPResponse:
    def __init__(self, data: BeautifulSoup):
        self.message_id = data['id']
        self.raw_element = data

        if data.name in ('message', 'msg'):
            self.type = data['type']
            self.xmlns = data['xmlns']
            self.from_jid = data['from']
            self.to_jid = data['to']

            g = data.find('g', recursive=False)
            self.group_jid = g['jid'] if g and 'jid' in g.attrs and jid_utilities.is_group_jid(g['jid']) else None
            self.is_group = self.group_jid is not None

            kik = data.find('kik', recursive=False)
            self.metadata = XMPPResponseMetadata(kik) if kik else None

            request = data.find('request', recursive=False)
            if request and request['xmlns'] == 'kik:message:receipt':
                self.request_delivered_receipt = request['d'] == 'true'
                self.request_read_receipt = request['r'] == 'true'
            else:
                self.request_delivered_receipt = False
                self.request_read_receipt = False


class XMPPResponseMetadata:
    def __init__(self, data: BeautifulSoup):
        """
        The timestamp of the message, in unix millis.

        Note: callers may receive a string that isn't a valid number from nefarious clients.
        Callers must try catch int() conversion calls.
        """
        self.timestamp = data['timestamp']

        """
        True if this message is a part of QoS history.
        When true, this message must be acked through QoS.
        """
        self.qos = data['qos'] == 'true'

        """
        True if this message requires push.
        When true, Kik sends a push notification to the user
        (iOS clients receive message info, Android receives an invisible push that is designed to wake up the XMPP connection)
        """
        self.push = data['push'] == 'true'

        """
        The name of the Kik service that processed this message.
        This is a flag meant for use internally by Kik and clients shouldn't rely on its behavior.
        """
        self.app = data['app']

        """
        True if the message has been processed by Kik then forwarded to its recipients.
        This is a flag meant for use internally by Kik and clients shouldn't rely on its behavior.
        """
        self.hop = data['hop'] == 'true' if 'hop' in data.attrs else None


class XMPPContentResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.content = data.find('content', recursive=False)
        self.content_id = self.content['id']          # type: str
        self.app_id = self.content['app-id']          # type: str
        self.server_sig = self.content['server-sig']  # type: str
        self.content_version = self.content['v']      # type: str

        self.strings = {}  # type: dict[str, str]
        self.images = {}   # type: dict[str, bytes]
        self.extras = {}   # type: dict[str, str]
        self.hashes = {}   # type: dict[str, str]
        self.uris = []     # type: list[XMPPContentResponse.ContentUri]

        if self.content_version != '2':
            # content version must be 2.
            # Version 2 has been required since ~2012.
            return

        strings_element = self.content.find('strings', recursive=False)
        if strings_element:
            for string in strings_element.find_all(recursive=False):
                self.strings[string.name] = string.text

        images_element = self.content.find('images', recursive=False)
        if images_element:
            for image in images_element.find_all(recursive=False):
                image_name = image.name
                if image_name == 'icon' or image_name == 'preview' or image_name == 'png-preview':
                    image_text = image.text
                    if len(image_text) > 0:
                        try:
                            self.images[image_name] = base64.urlsafe_b64decode(image_text)
                        except binascii.Error:
                            # Guard against invalid base-64 image data (server doesn't validate this data for us)
                            pass

        extras_element = self.content.find('extras', recursive=False)
        if extras_element:
            for extra in extras_element.find_all(recursive=False):
                extra_key = extra.find('key', recursive=False)
                extra_val = extra.find('val', recursive=False)
                if extra_key and extra_val:
                    if len(extra_key.text) > 0 and len(extra_val.text) > 0:
                        self.extras[extra_key.text] = extra_val.text

        hashes_element = self.content.find('hashes', recursive=False)
        if hashes_element:
            for hash_element in hashes_element.find_all(recursive=False):
                hash_name = hash_element.name
                if hash_name == 'sha1-original' or hash_name == 'sha1-scaled' or hash_name == 'blockhash-scaled':
                    self.hashes[hash_name] = hash_element.text

        uris = self.content.find('uris', recursive=False)
        for uri in uris.find_all('uri', recursive=False, limit=50):
            self.uris.append(self.ContentUri(uri))

        self.file_url = self.strings['file-url']
        if self.file_url is not None:
            if not self.file_url.startswith('https://platform.kik.com'):
                raise ValueError(f"invalid file-url (expected https://platform.kik.com, received {self.file_url})")

    class ContentUri:
        def __init__(self, uri: BeautifulSoup):
            self.platform = uri['platform']
            self.type = uri['type']
            self.file_content_type = uri['file-content-type']
            self.priority = uri['priority']
            self.url = uri.text


class XMPPReceiptResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        receipt = data.find('receipt', recursive=False)
        self.type = receipt['type']
        self.receipt_ids = [m['id'] for m in receipt.findAll('msgid')]

