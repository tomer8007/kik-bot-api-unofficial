"""
Defines classes for dealing with generic chatting (text messaging, read receipts, etc)
"""

import time
from typing import Union

from bs4 import BeautifulSoup
from lxml import etree
from lxml.etree import Element

from kik_unofficial.datatypes.peers import Group
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse, XMPPContentResponse, \
    XMPPReceiptResponse, XMPPOutgoingContentMessageElement, XMPPOutgoingMessageElement, XMPPOutgoingIsTypingMessageElement
from kik_unofficial.http_requests.tenor_client import KikTenorClient
from kik_unofficial.utilities.parsing_utilities import ParsingUtilities, get_text_safe, get_attribute_safe


class OutgoingChatMessage(XMPPOutgoingMessageElement):
    """
    Represents an outgoing text chat message to another kik entity (member or group)
    """

    def __init__(self, peer_jid: str, body: str):
        super().__init__(peer_jid)
        self.body = body

    def serialize_message(self, message: Element) -> None:
        etree.SubElement(message, 'body').text = self.body
        etree.SubElement(message, 'preview').text = self.body[:20]
        self.add_kik_element(message, push=True, qos=True)
        self.add_request_element(message, request_delivered=True, request_read=True)
        self.add_empty_element(message, 'ri')


class OutgoingChatImage(XMPPOutgoingContentMessageElement):
    """
   Represents an outgoing image chat message to another kik entity (member or group)
   """

    def __init__(self, peer_jid: str, file_location, forward: bool = True):
        super().__init__(peer_jid, app_id='com.kik.ext.gallery')
        self.allow_forward = forward
        self.parsed = ParsingUtilities.parse_image(file_location)

    def serialize_content(self) -> None:
        self.add_string('app-name', 'Gallery')
        self.add_string('file-size', str(self.parsed['size']))
        self.set_allow_forward(self.allow_forward)
        self.add_string('file-content-type', 'image/jpeg')
        self.add_string('file-name', f'{self.content_id}.jpg')

        self.add_hash('sha1-original', self.parsed['SHA1'])
        self.add_hash('sha1-scaled', self.parsed['SHA1Scaled'])
        self.add_hash('blockhash-scaled', self.parsed['blockhash'])

        self.add_image('preview', self.parsed['image_bytes'])


class IncomingChatMessage(XMPPResponse):
    """
    Represents an incoming text chat message from another user
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.preview = get_text_safe(data, 'preview')
        self.body = get_text_safe(data, 'body')


class IncomingGroupChatMessage(IncomingChatMessage):
    """
    Represents an incoming text chat message from a group
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        # Messages from public groups include an alias user which can be resolved with client.xiphias_get_users_by_alias
        self.alias_sender = get_text_safe(data, 'alias-sender')


class OutgoingReadReceipt(XMPPOutgoingMessageElement):
    """
    Represents an outgoing read receipt to a specific user, for one or more messages
    """

    def __init__(self, peer_jid: str, receipt_message_id: Union[str, list[str]], group_jid: Union[str, None] = None):
        super().__init__(peer_jid)
        self.group_jid = group_jid
        self.receipt_message_ids = receipt_message_id if isinstance(receipt_message_id, list) else [receipt_message_id]
        self.message_type = 'receipt'

    def serialize_message(self, message: Element) -> None:
        self.add_kik_element(message, push=True, qos=True)
        receipt = etree.SubElement(message, 'receipt')
        receipt.set('xmlns', 'kik:message:receipt')
        receipt.set('type', 'read')
        for receipt_id in self.receipt_message_ids:
            msgid = etree.SubElement(receipt, 'msgid')
            msgid.set('id', receipt_id)

        if self.group_jid:
            g = etree.SubElement(message, 'g')
            g.set('jid', self.group_jid)


class OutgoingIsTypingEvent(XMPPOutgoingIsTypingMessageElement):
    """
    Represents an outgoing is-typing event
    """

    def __init__(self, peer_jid: str, is_typing: bool):
        super().__init__(peer_jid, is_typing)

    def serialize_message(self, message: Element) -> None:
        self.add_kik_element(message, push=False, qos=False)
        is_typing = etree.SubElement(message, 'is-typing')
        is_typing.set('val', 'true' if self.is_typing else 'false')


class OutgoingLinkShareEvent(XMPPOutgoingContentMessageElement):
    """
    Represents an outgoing link share event. This appears as a card in the mobile clients.
    """

    def __init__(self, peer_jid: str, link: str, title: str, text: str, app_name: str, preview_bytes: Union[bytes, None]):
        super().__init__(peer_jid, app_id='com.kik.cards')
        self.link = link
        self.title = title
        self.text = text
        self.app_name = app_name
        self.preview_bytes = preview_bytes

    def serialize_content(self) -> None:
        self.add_string('app-name', self.app_name)
        self.add_string('layout', 'article')
        self.add_string('title', self.title)
        self.add_string('text', self.text)
        self.set_allow_forward(True)

        if self.preview_bytes:
            self.add_image('preview', self.preview_bytes)

        self.add_uri(platform='cards', url=self.link)
        self.add_uri(url='')
        self.add_uri(url='http://cdn.kik.com/cards/unsupported.html')


class IncomingMessageReadEvent(XMPPReceiptResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)


class IncomingMessageDeliveredEvent(XMPPReceiptResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)


class IncomingGroupReceiptsEvent(XMPPReceiptResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)


class IncomingIsTypingEvent(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        is_typing = data.find('is-typing', recursive=False)
        self.is_typing = get_attribute_safe(is_typing, 'val') == 'true'


class IncomingGroupIsTypingEvent(IncomingIsTypingEvent):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)


class IncomingStatusResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        status = data.find('status', recursive=False)
        self.status = status.text
        self.status_jid = status['jid']
        self.special_visibility = get_attribute_safe(status, 'special-visibility') == 'true'
        group = data.find('g', recursive=False)
        self.group = Group(group) if group and len(group.contents) > 0 else None


class IncomingGroupStatus(IncomingStatusResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)


class IncomingGroupSysmsg(XMPPResponse):
    """ xmlns=jabber:client type=groupchat """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        sysmsg = data.find('sysmsg', recursive=False)
        self.sysmsg_xmlns = get_attribute_safe(sysmsg, 'xmlns')
        self.sysmsg = sysmsg.text
        group = data.find('g', recursive=False)
        self.group = Group(group) if group and len(group.contents) > 0 else None


class IncomingFriendAttribution(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.context_type = None
        self.referrer_jid = None
        self.referrer_group_jid = None
        self.referrer_url = None
        self.referrer_name = None
        self.reply = None
        self.body = None

        friend_attribution = data.find('friend-attribution', recursive=False)
        context = friend_attribution.find('context', recursive=False)
        if context:
            self.context_type = get_attribute_safe(context, 'type')
            self.referrer_jid = get_attribute_safe(context, 'referrer')
            self.referrer_group_jid = get_attribute_safe(context, 'jid')
            self.referrer_url = get_attribute_safe(context, 'url')
            self.referrer_name = get_attribute_safe(context, 'name')
            self.reply = get_attribute_safe(context, 'reply') == 'true'

            body = friend_attribution.find('body', recursive=False)
            # mobile clients remove quotes from the beginning and end of the string
            self.body = body.text.strip('"') if body else None


class IncomingImageMessage(XMPPContentResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.image_url = self.file_url


class IncomingGroupSticker(XMPPContentResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.sticker_pack_id = self.extras.get('sticker_pack_id')  # type: str | None
        self.sticker_url = self.extras.get('sticker_url')          # type: str | None
        self.sticker_id = self.extras.get('sticker_id')            # type: str | None
        self.sticker_source = self.extras.get('sticker_source')    # type: str | None
        self.png_preview = self.images.get('png-preview')          # type: bytes | None


class IncomingGifMessage(XMPPContentResponse):
    """
    Represents an incoming GIF message.

    See self.uris for the list of GIF URLs.
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)


class OutgoingGIFMessage(XMPPOutgoingContentMessageElement):
    """
    Represents an outgoing GIF message to another kik entity (member or group)
    """

    def __init__(self, peer_jid: str, search_term: str, api_key: str):
        super().__init__(peer_jid, app_id='com.kik.ext.gif')
        self.allow_forward = True
        self.gif_preview, self.gif_data = KikTenorClient(api_key).search_for_gif(search_term)

    def serialize_content(self) -> None:
        self.add_string('app-name', 'GIF')
        self.add_string('layout', 'video')
        self.set_allow_forward(self.allow_forward)
        self.set_allow_save(False)
        self.set_video_autoplay(True)
        self.set_video_loop(True)
        self.set_video_muted(True)

        self.add_image('icon', b'')
        self.add_image('preview', self.gif_preview)

        self.add_uri(url=self.gif_data["mp4"]["url"], priority='0', type='video', file_content_type='video/mp4')
        self.add_uri(url=self.gif_data["webm"]["url"], priority='1', type='video', file_content_type='video/webm')
        self.add_uri(url=self.gif_data["tinymp4"]["url"], priority='0', type='video', file_content_type='video/tinymp4')
        self.add_uri(url=self.gif_data["tinywebm"]["url"], priority='1', type='video', file_content_type='video/tinywebm')
        self.add_uri(url=self.gif_data["nanomp4"]["url"], priority='0', type='video', file_content_type='video/nanomp4')
        self.add_uri(url=self.gif_data["nanowebm"]["url"], priority='1', type='video', file_content_type='video/nanowebm')


class IncomingVideoMessage(XMPPContentResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.video_url = self.file_url                              # type: str | None
        self.file_content_type = self.strings.get('file-content-type')  # type: str | None
        self.duration_milliseconds = self.strings.get('duration')       # type: str | None
        self.file_size = self.strings.get('file-size')                  # type: str | None


class IncomingCardMessage(XMPPContentResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.app_name = self.strings.get('app-name')    # type: str | None
        self.card_icon = self.strings.get('card-icon')  # type: str | None
        self.layout = self.strings.get('layout')        # type: str | None
        self.title = self.strings.get('title')          # type: str | None
        self.text = self.strings.get('text')            # type: str | None
        self.allow_forward = self.strings.get('allow-forward') == 'true'  # type: bool
        self.icon = self.images.get('icon')                               # type: bytes | None
        self.uri = self.uris[0] if len(self.uris) > 0 else None


class KikPingRequest(XMPPElement):
    def __init__(self):
        super().__init__()

    def serialize(self) -> bytes:
        return b'<ping/>'


class KikPongResponse:
    """
    Response to a <ping/> request to kik servers

    :param latency: the round trip time of ping to pong, measured in milliseconds.
    """
    def __init__(self, latency: int):
        self.received_time = time.time()
        self.latency = latency

    def __str__(self):
        return f'pong ({self.latency} ms)'

    def __repr__(self):
        return f'KikPongResponse(received_time={self.received_time}, latency={self.latency})'


class IncomingErrorMessage(XMPPResponse):
    """
    Received as an 'error' type in response to an outgoing message.

    The ID of this message should contain the same ID corresponding to the message that triggered the error.

    This can be used for retry logic when sending messages or debugging.
    """
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.error = data.error
        self.error_message = get_text_safe(self.error, 'text')
