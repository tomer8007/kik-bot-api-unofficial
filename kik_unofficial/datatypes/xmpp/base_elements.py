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
    """
    Represents an outgoing stanza of any kind.

    Subclasses must override `serialize`.
    """
    def __init__(self):
        self.message_id = CryptographicUtils.make_kik_uuid()

    def serialize(self) -> Union[bytes, Element]:
        raise NotImplementedError


class XMPPOutgoingMessageElement(XMPPElement):
    """
    Represents an outgoing message of any kind to a user.

    Subclasses must override `serialize_message` and add
    the child elements necessary to build the message stanza for sending.
    """
    def __init__(self, peer_jid: str):
        super().__init__()
        self.peer_jid = peer_jid
        self.is_group = jid_utilities.is_group_jid(peer_jid)
        self.timestamp = str(KikServerClock.get_server_time())
        self.message_type = "groupchat" if self.is_group else "chat"

    def serialize_message(self, message: Element) -> None:
        raise NotImplementedError

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

    @final
    def add_kik_element(self, message: Element, push: bool = True, qos: bool = True) -> None:
        """
        Adds a kik child element. Exactly one of these must be present in every outgoing message.

        :param message: the message parameter from serialize_message()
        :param push: if True, the recipient will be sent a push notification by Kik.
        :param qos: if True, the message will be placed in the QoS pool (the client can receive it while disconnected)
        """
        kik = etree.SubElement(message, 'kik')
        kik.set('push', 'true' if push else 'false')
        kik.set('qos', 'true' if qos else 'false')
        kik.set('timestamp', self.timestamp)

    @final
    def add_request_element(self, message: Element, request_delivered: bool = True, request_read: bool = False) -> None:
        """
        Adds a request element. Request elements are indicators to the receiving client for sending receipts.

        :param message: the message parameter from serialize_message()
        :param request_delivered: if True, the receiving client sends a delivered back when the message is received
        :param request_read: if True, the receiving client sends a read receipt when the message is opened or read
        """
        if not request_read and not request_delivered:
            return
        request = etree.SubElement(message, 'request')
        request.set('xmlns', 'kik:message:receipt')
        request.set('d', 'true' if request_delivered else 'false')
        request.set('r', 'true' if request_read else 'false')

    @final
    def add_empty_element(self, message: Element, name: str) -> None:
        """
        Adds an empty element.

        For example:
        self.add_empty_element(message, 'foo')
        becomes '<foo></foo>' when serialized.
        """
        etree.SubElement(message, name).text = ''


class XMPPOutgoingContentMessageElement(XMPPOutgoingMessageElement):
    """
    Represents an outgoing content message.

    Content messages can be images, gifs, videos, stickers, or custom cards.

    Subclasses must override `serialize_content` and add
    the elements necessary to build the content for sending.
    """
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
        """
        Sets the forwarding flag for content.

        :param allow_forward: True if the client is allowed to forward the content
        """
        self.add_string('allow-forward', 'true' if allow_forward else 'false')

    @final
    def set_allow_save(self, allow_save: bool) -> None:
        """
        Sets the allow save flag for content.

        :param allow_save: True if the client is allowed to save the content
        """
        self.add_string('disallow-save', 'false' if allow_save else 'true')

    @final
    def set_video_autoplay(self, auto_play: bool) -> None:
        """
        Sets the auto play flag for content.
        This has no effect if not a video / GIF.

        :param auto_play: True if the client should auto-play the content
        """
        self.add_string('video-should-autoplay', 'true' if auto_play else 'false')

    @final
    def set_video_loop(self, loop: bool) -> None:
        """
        Sets the video loop flag for content.
        This has no effect if not a video / GIF.

        :param loop: True if the client should play the video on a loop
        """
        self.add_string('video-should-loop', 'false' if loop else 'true')

    @final
    def set_video_muted(self, muted: bool) -> None:
        """
        Sets the muted flag for content.
        This has no effect if not a video / GIF.

        :param muted: True if the client should mute the video when playing it
        """
        self.add_string('video-should-be-muted', 'true' if muted else 'false')

    @final
    def add_string(self, name: str, value: str) -> None:
        etree.SubElement(self._content_strings, name).text = value

    @final
    def add_image(self, name: str, image_bytes: bytes) -> None:
        """
        Adds an image to the content message.

        'icon' should be in PNG format and be a perfect square (64x64px or less)
        'preview' should be in JPG format.
        'png-preview' should be in PNG format.

        :param name: the image name. Must be one of 'icon' 'preview' 'png-preview'
        :param image_bytes: the image bytes
        """
        if name not in ('icon', 'preview', 'png-preview'):
            raise ValueError(f'invalid image name {name}, must be icon, preview, png-preview')
        etree.SubElement(self._content_images, name).text = base64.b64encode(image_bytes)

    @final
    def add_hash(self, name: str, value: str) -> None:
        """
        Adds a hash to the content message.

        Hashes should only be used for image messages.

        :param name: the hash name. Must be one of 'sha1-original' 'sha1-scaled' 'blockhash-scaled'
        :param value: the hash value
        """
        if name not in ('sha1-original', 'sha1-scaled', 'blockhash-scaled'):
            raise ValueError(f'invalid hash name {name}, must be sha1-original, preview, blockhash-scaled')
        etree.SubElement(self._content_hashes, name).text = value

    @final
    def add_extra(self, key: str, value: str) -> None:
        """
        Adds an extra to the content message.

        Extras are key value pairs forwarded to a browser when the message is clicked and contains a link.

        :param key: the extra key
        :param value: the extra value
        """
        item = etree.SubElement(self._content_extras, 'item')
        etree.SubElement(item, 'key').name = key
        etree.SubElement(item, 'val').name = value

    @final
    def add_uri(self, url: str, platform: str = None, type: str = None, file_content_type: str = None, priority: str = None) -> None:
        """
        Adds a uri to the content message.

        Uris are URLs to content.
        For GIFs, these are used to play back the GIF.
        For other content types, the link is opened in the browser when the content is tapped.

        :param url: the URL itself
        :param platform: the platform of the URI
        :param type: the type of the URI
        :param file_content_type: the file content type of the URI
        :param priority: the priority of the URI. This should be a positive integer.
        """
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
    """
    An outgoing is typing message to a group
    """
    def __init__(self, peer_jid: str, is_typing: bool):
        super().__init__(peer_jid)
        self.message_type = 'is-typing'  # IsTyping messages always use this type, even if it's to a group
        self.is_typing = is_typing       # type: bool


class XMPPResponse:
    """
    This is an incoming stanza from Kik.

    When a message stanza is encountered, this will parse the basic attributes of the message.
    """
    def __init__(self, data: BeautifulSoup):
        self.message_id = data['id']
        self.raw_element = data

        if data.name in ('message', 'msg'):
            self.type = data['type']
            self.from_jid = data['from']
            self.xmlns = data['xmlns'] if 'xmlns' in data.attrs else None
            self.to_jid = data['to'] if 'to' in data.attrs else None

            g = data.find('g', recursive=False)
            self.group_jid = g['jid'] if g and 'jid' in g.attrs and jid_utilities.is_group_jid(g['jid']) else None
            self.is_group = self.group_jid is not None

            kik = data.find('kik', recursive=False)
            self.metadata = XMPPResponseMetadata(kik) if kik else None

            request = data.find('request', recursive=False)
            if request and request['xmlns'] == 'kik:message:receipt':
                self.request_delivered_receipt = request['d'] == 'true' if 'd' in request.attrs else False
                self.request_read_receipt = request['r'] == 'true' if 'r' in request.attrs else False
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
        """
        A content URI.

        Uris are URLs to content.
        For GIFs, these are used to play back the GIF.
        For other content types, the link is opened in the browser when the content is tapped.
        """
        def __init__(self, uri: BeautifulSoup):
            self.platform = uri['platform']
            self.type = uri['type']
            self.file_content_type = uri['file-content-type']
            self.priority = uri['priority']
            self.url = uri.text


class XMPPReceiptResponse(XMPPResponse):
    """
    An incoming receipt received from another user.
    """
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        receipt = data.find('receipt', recursive=False)
        self.type = receipt['type']
        self.receipt_ids = [m['id'] for m in receipt.findAll('msgid')]
        self.receipt_message_id = self.receipt_ids[0]

