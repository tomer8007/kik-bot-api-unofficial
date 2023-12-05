"""
Defines classes for dealing with generic chatting (text messaging, read receipts, etc)
"""

import time
from typing import Union

import requests
import json
import base64
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup

from kik_unofficial.datatypes.peers import Group
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse, XMPPContentResponse, \
    XMPPReceiptResponse, XMPPOutgoingContentMessageElement, XMPPOutgoingMessageElement, XMPPOutgoingIsTypingMessageElement
from kik_unofficial.utilities.parsing_utilities import ParsingUtilities, get_text_safe


class OutgoingChatMessage(XMPPOutgoingMessageElement):
    """
    Represents an outgoing text chat message to another kik entity (member or group)
    """

    def __init__(self, peer_jid, body):
        super().__init__(peer_jid)
        self.body = body

    def serialize(self) -> bytes:
        data = (f'<message type="{self.message_type}" to="{self.peer_jid}" id="{self.message_id}" cts="{self.timestamp}">'
                f'<body>{ParsingUtilities.escape_xml(self.body)}</body>'
                f'<preview>{ParsingUtilities.escape_xml(self.body[:20])}</preview>'
                f'<kik push="true" qos="true" timestamp="{self.timestamp}" />'
                '<request xmlns="kik:message:receipt" r="true" d="true" />'
                '<ri></ri>'
                '</message>')
        return data.encode()


class OutgoingChatImage(XMPPOutgoingContentMessageElement):
    """
   Represents an outgoing image chat message to another kik entity (member or group)
   """

    def __init__(self, peer_jid, file_location, forward=True):
        super().__init__(peer_jid)
        self.allow_forward = forward
        self.parsed = ParsingUtilities.parse_image(file_location)

    def serialize(self) -> bytes:
        data = (
            f'<message to="{self.peer_jid}" id="{self.message_id}" cts="{self.timestamp}" type="{self.message_type}" xmlns="{self.xmlns}">'
            f'<kik timestamp="{self.timestamp}" qos="true" push="true" />'
            '<request xmlns="kik:message:receipt" d="true" r="true" />'
            f'<content id="{self.content_id}" v="2" app-id="com.kik.ext.gallery">'
            '<strings>'
            '<app-name>Gallery</app-name>'
            f'<file-size>{self.parsed["size"]}</file-size>'
            f'<allow-forward>{str(self.allow_forward).lower()}</allow-forward>'
            '<disallow-save>false</disallow-save>'
            '<file-content-type>image/jpeg</file-content-type>'
            f'<file-name>{self.content_id}.jpg</file-name>'
            '</strings>'
            '<extras />'
            '<hashes>'
            f'<sha1-original>{self.parsed["SHA1"]}</sha1-original>'
            f'<sha1-scaled>{self.parsed["SHA1Scaled"]}</sha1-scaled>'
            f'<blockhash-scaled>{self.parsed["blockhash"]}</blockhash-scaled>'
            '</hashes>'
            '<images>'
            f'<preview>{self.parsed["base64"]}</preview>'
            '<icon></icon>'
            '</images>'
            '<uris />'
            '</content>'
            '</message>'
        )
        return data.encode()


class IncomingChatMessage(XMPPResponse):
    """
    Represents an incoming text chat message from another user
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)

        self.status = get_text_safe(data, 'status')
        self.preview = get_text_safe(data, 'preview')
        self.body = get_text_safe(data, 'body')

        is_typing = data.find('is-typing', recursive=False)
        self.is_typing = is_typing['val'] == 'true' if is_typing else None


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

    def __init__(self, peer_jid, receipt_message_id: Union[str, list[str]], group_jid=None):
        super().__init__(peer_jid)
        self.group_jid = group_jid
        self.receipt_message_ids = receipt_message_id if isinstance(receipt_message_id, list) else [receipt_message_id]

    def serialize(self) -> bytes:
        data = (f'<message type="receipt" id="{self.message_id}" to="{self.peer_jid}" cts="{self.timestamp}">'
                f'<kik push="false" qos="true" timestamp="{self.timestamp}" />'
                '<receipt xmlns="kik:message:receipt" type="read">'
                f'{''.join([f'<msgid id="{msg_id}" />' for msg_id in self.receipt_message_ids])}'
                '</receipt>'
                f'{f'<g jid="{self.group_jid}" />' if self.group_jid else ''}'
                '</message>')
        return data.encode()


class OutgoingIsTypingEvent(XMPPOutgoingIsTypingMessageElement):
    def __init__(self, peer_jid, is_typing):
        super().__init__(peer_jid, is_typing)

    def serialize(self) -> bytes:
        data = (f'<message type="{self.message_type}" to="{self.peer_jid}" id="{self.message_id}">'
                f'<kik push="false" qos="false" timestamp="{self.timestamp}" />'
                f'<is-typing val="{'true' if self.is_typing else 'false'}" />'
                '</message>')
        return data.encode()


class OutgoingLinkShareEvent(XMPPOutgoingContentMessageElement):
    def __init__(self, peer_jid, link, title, text, app_name):
        super().__init__(peer_jid)
        self.link = link
        self.title = title
        self.text = text
        self.app_name = app_name

    def serialize(self) -> bytes:
        data = (f'<message type="{self.message_type}" xmlns="{self.xmlns}" to="{self.peer_jid}" id="{self.message_id}" cts="{self.timestamp}">'
                '<pb></pb>'
                f'<kik push="true" qos="true" timestamp="{self.timestamp}" />'
                '<request xmlns="kik:message:receipt" r="true" d="true" />'
                f'<content id="{self.content_id}" app-id="com.kik.cards" v="2">'
                '<strings>'
                f'<app-name>{self.app_name}</app-name>'
                '<layout>article</layout>'
                f'<title>{self.title}</title>'
                f'<text>{self.text}</text>'
                '<allow-forward>true</allow-forward>'
                '</strings>'
                '<extras />'
                '<hashes />'
                '<images>'
                '</images>'
                '<uris>'
                f'<uri platform="cards">{self.link}</uri>'
                '<uri></uri>'
                '<uri>http://cdn.kik.com/cards/unsupported.html</uri>'
                '</uris>'
                '</content>'
                '</message>')

        return data.encode()


class IncomingMessageReadEvent(XMPPReceiptResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.receipt_message_id = self.receipt_ids[0]


class IncomingMessageDeliveredEvent(XMPPReceiptResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.receipt_message_id = self.receipt_ids[0]


class IncomingIsTypingEvent(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        is_typing = data.find('is-typing', recursive=False)
        self.is_typing = is_typing == 'true' if is_typing else False


class IncomingGroupIsTypingEvent(IncomingIsTypingEvent):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)


class IncomingStatusResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        status = data.find('status', recursive=False)
        self.status = status.text
        self.special_visibility = status['special-visibility'] == 'true'
        self.status_jid = status['jid'] if 'jid' in status.attrs else None
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
        self.sysmsg_xmlns = sysmsg['xmlns'] if 'xmlns' in sysmsg.attrs else None
        self.sysmsg = sysmsg.text
        group = data.find('g', recursive=False)
        self.group = Group(group) if group and len(group.contents) > 0 else None


class IncomingGroupReceiptsEvent(XMPPReceiptResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)


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
        if friend_attribution:
            context = friend_attribution.find('context', recursive=False)
            if context:
                self.context_type = context['type']
                self.referrer_jid = context['referrer']
                self.referrer_group_jid = context['jid']
                self.referrer_url = context['url']
                self.referrer_name = context['name']
                self.reply = context['reply'] == 'true'

            body = friend_attribution.find('body', recursive=False)
            if body:
                # mobile clients remove quotes from the beginning and end of the string
                self.body = body.text.strip('"')


class IncomingImageMessage(XMPPContentResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.image_url = self.file_url


class IncomingGroupSticker(XMPPContentResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.sticker_pack_id = self.extras['sticker_pack_id']  # type: str | None
        self.sticker_url = self.extras['sticker_url']          # type: str | None
        self.sticker_id = self.extras['sticker_id']            # type: str | None
        self.sticker_source = self.extras['sticker_source']    # type: str | None
        self.png_preview = self.images['png-preview']          # type: bytes | None


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

    def __init__(self, peer_jid, search_term, api_key):
        super().__init__(peer_jid)
        self.allow_forward = True
        self.gif_preview, self.gif_data = self.get_gif_data(search_term, api_key)

    def serialize(self) -> bytes:
        data = (
            f'<message cts="{self.timestamp}" type="{self.message_type}" to="{self.peer_jid}" id="{self.message_id}" xmlns="{self.xmlns}">'
            f'<kik push="true" timestamp="{self.timestamp}" qos="true" />'
            '<pb/>'
            f'<content id="{self.content_id}" v="2" app-id="com.kik.ext.gif">'
            '<strings>'
            '<app-name>GIF</app-name>'
            '<layout>video</layout>'
            f'<allow-forward>{'true' if self.allow_forward else 'false'}</allow-forward>'
            '<disallow-save>true</disallow-save>'
            '<video-should-autoplay>true</video-should-autoplay>'
            '<video-should-loop>true</video-should-loop>'
            '<video-should-be-muted>true</video-should-be-muted>'
            '</strings>'
            '<images>'
            '<icon></icon>'
            f'<preview>{self.gif_preview}</preview>'
            '</images>'
            '<uris>'
            f'<uri priority="0" type="video" file-content-type="video/mp4">{self.gif_data["mp4"]["url"]}</uri>'
            f'<uri priority="1" type="video" file-content-type="video/webm">{self.gif_data["webm"]["url"]}</uri>'
            f'<uri priority="0" type="video" file-content-type="video/tinymp4">{self.gif_data["tinymp4"]["url"]}</uri>'
            f'<uri priority="1" type="video" file-content-type="video/tinywebm">{self.gif_data["tinywebm"]["url"]}</uri>'
            f'<uri priority="0" type="video" file-content-type="video/nanomp4">{self.gif_data["nanomp4"]["url"]}</uri>'
            f'<uri priority="1" type="video" file-content-type="video/nanowebm">{self.gif_data["nanowebm"]["url"]}</uri>'
            '</uris>'
            '</content>'
            '<request r="true" d="true" xmlns="kik:message:receipt" />'
            '</message>'
        )
        return data.encode()

    def get_gif_data(self, search_term, api_key):
        if not api_key:
            raise Exception("A tenor.com API key is required to search for GIFs images. please get one and change it")

        r = requests.get(f"https://tenor.googleapis.com/v2/search?q={search_term}&key={api_key}&limit=1")
        if r.status_code == 200:
            gif = json.loads(r.content.decode('ascii'))
            response = requests.get(gif["results"][0]["media_formats"]["nanogifpreview"]["url"])
            img = Image.open(BytesIO(response.content))
            buffered = BytesIO()

            img.convert("RGB").save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('ascii')
            return img_str, gif["results"][0]["media_formats"]
        else:
            return ""


class IncomingVideoMessage(XMPPContentResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.video_url = self.file_url                              # type: str | None
        self.file_content_type = self.strings['file-content-type']  # type: str | None
        self.duration_milliseconds = self.strings['duration']       # type: str | None
        self.file_size = self.strings['file-size']                  # type: str | None


class IncomingCardMessage(XMPPContentResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.app_name = self.strings['app-name']    # type: str | None
        self.card_icon = self.strings['card-icon']  # type: str | None
        self.layout = self.strings['layout']        # type: str | None
        self.title = self.strings['title']          # type: str | None
        self.text = self.strings['text']            # type: str | None
        self.allow_forward = self.strings['allow-forward'] == 'true'  # type: bool
        self.icon = self.images['icon']                               # type: bytes | None
        self.uri = self.uris[0] if self.uris and len(self.uris) > 0 else None


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
