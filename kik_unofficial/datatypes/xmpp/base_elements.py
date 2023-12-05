import base64
import binascii
import uuid
from typing import Union, final

from bs4 import BeautifulSoup
from lxml import etree
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

    @final
    def serialize(self) -> Element:
        message = etree.Element('message')
        message.set('type', self.message_type)
        if self.is_group:
            message.set('xmlns', 'kik:groups')
        message.set('to', self.peer_jid)
        message.set('id', self.message_id)
        if not self.message_type == 'is-typing':
            message.set('cts', self.timestamp)
        self.serialize_message(message)
        return message

    def serialize_message(self, message: Element) -> None:
        raise NotImplementedError

    @final
    def add_kik_element(self, message: Element, push: bool = True, qos: bool = True) -> None:
        kik = etree.SubElement(message, 'kik')
        kik.set('push', 'true' if push else 'false')
        kik.set('qos', 'true' if qos else 'false')
        kik.set('timestamp', self.timestamp)

    @final
    def add_request_element(self, message: Element, request_delivered: bool = True, request_read: bool = False) -> None:
        if not request_read and not request_delivered:
            return
        request = etree.SubElement(message, 'request')
        request.set('xmlns', 'kik:message:receipt')
        request.set('d', 'true' if request_delivered else 'false')
        request.set('r', 'true' if request_read else 'false')

    @final
    def add_empty_element(self, message: Element, name: str) -> None:
        etree.SubElement(message, name).text = ''


class XMPPOutgoingContentMessageElement(XMPPOutgoingMessageElement):
    def __init__(self, peer_jid: str, app_id: str):
        super().__init__(peer_jid)
        self.content_id = str(uuid.uuid4())  # content ids arent cryptographic
        self.app_id = app_id
        self._content = None
        self._content_strings = None
        self._content_images = None
        self._content_hashes = None
        self._content_extras = None
        self._content_uris = None

    def serialize_content(self) -> None:
        raise NotImplementedError

    @final
    def serialize_message(self, message: Element) -> None:
        self.add_empty_element(message, 'pb')
        self.add_kik_element(message, push=True, qos=True)
        self.add_request_element(message, request_delivered=True, request_read=True)
        content = etree.SubElement(message, 'content')
        content.set('id', self.content_id)
        content.set('app-id', self.app_id)
        content.set('v', '2')
        self._content = content
        self._content_strings = etree.SubElement(content, 'strings')
        self._content_images = etree.SubElement(content, 'images')
        self._content_hashes = etree.SubElement(content, 'hashes')
        self._content_extras = etree.SubElement(content, 'extras')
        self._content_uris = etree.SubElement(content, 'uris')
        self.serialize_content()

    @final
    def set_allow_forward(self, allow_forward: bool) -> None:
        self.add_string('allow-forward', 'true' if allow_forward else 'false')

    @final
    def set_allow_save(self, allow_save: bool) -> None:
        self.add_string('disallow-save', 'false' if allow_save else 'true')

    @final
    def set_video_autoplay(self, auto_play: bool) -> None:
        self.add_string('video-should-autoplay', 'true' if auto_play else 'false')

    @final
    def set_video_loop(self, loop: bool) -> None:
        self.add_string('video-should-loop', 'false' if loop else 'true')

    @final
    def set_video_muted(self, muted: bool) -> None:
        self.add_string('video-should-be-muted', 'true' if muted else 'false')

    @final
    def add_string(self, name: str, value: str) -> None:
        etree.SubElement(self._content_strings, name).text = value

    @final
    def add_image(self, name: str, image_base64: str) -> None:
        if name not in ('icon', 'preview', 'png-preview'):
            raise ValueError(f'invalid image name {name}, must be icon, preview, png-preview')
        etree.SubElement(self._content_images, name).text = image_base64

    @final
    def add_hash(self, name: str, value: str) -> None:
        if name not in ('sha1-original', 'sha1-scaled', 'blockhash-scaled'):
            raise ValueError(f'invalid hash name {name}, must be sha1-original, preview, blockhash-scaled')
        etree.SubElement(self._content_hashes, name).text = value

    @final
    def add_extra(self, key: str, value: str) -> None:
        item = etree.SubElement(self._content_extras, 'item')
        etree.SubElement(item, 'key').name = key
        etree.SubElement(item, 'val').name = value

    @final
    def add_uri(self, url: str, platform: str = None, type: str = None, file_content_type: str = None, priority: str = None) -> None:
        uri = etree.SubElement(self._content_uris, 'uri')
        uri.text = url
        if platform:
            uri.set('platform', platform)
        if type:
            uri.set('type', type)
        if file_content_type:
            uri.set('file-content-type', file_content_type)
        if priority:
            uri.set('priority', priority)


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
        When true, Kik sends a push notification to the user.
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
        self.receipt_message_id = self.receipt_ids[0]

