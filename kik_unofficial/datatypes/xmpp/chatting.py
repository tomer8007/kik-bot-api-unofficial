"""
Defines classes for dealing with generic chatting (text messaging, read receipts, etc)
"""

import time
import os
import requests
import json
import base64
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
from kik_unofficial.datatypes.peers import Group
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse
from kik_unofficial.utilities.parsing_utilities import ParsingUtilities


class OutgoingChatMessage(XMPPElement):
    """
    Represents an outgoing text chat message to another kik entity (member or group)
    """
    def __init__(self, peer_jid, body, is_group=False, bot_mention_jid=None):
        super().__init__()
        self.peer_jid = peer_jid
        self.body = body
        self.is_group = is_group
        self.bot_mention_jid = bot_mention_jid

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))
        message_type = "groupchat" if self.is_group else "chat"
        bot_mention_data = (
            f'<mention><bot>{self.bot_mention_jid}</bot></mention>'
            if self.bot_mention_jid
            else ''
        )
        data = (f'<message type="{message_type}" to="{self.peer_jid}" id="{self.message_id}" cts="{timestamp}">'
                f'<body>{ParsingUtilities.escape_xml(self.body)}</body>'
                f'{bot_mention_data}'
                f'<preview>{ParsingUtilities.escape_xml(self.body[:20])}</preview>'
                f'<kik push="true" qos="true" timestamp="{timestamp}" />'
                '<request xmlns="kik:message:receipt" r="true" d="true" />'
                '<ri></ri>'
                '</message>')
        return data.encode()


class OutgoingGroupChatMessage(OutgoingChatMessage):
    """
    Represents an outgoing text chat message to a group
    """
    def __init__(self, group_jid, body, bot_mention_jid):
        super().__init__(group_jid, body, is_group=True, bot_mention_jid=bot_mention_jid)


class OutgoingChatImage(XMPPElement):
    """
   Represents an outgoing image chat message to another kik entity (member or group)
   """
    def __init__(self, peer_jid, file_location, is_group=False, forward=True):
        super().__init__()
        self.peer_jid = peer_jid
        self.allow_forward = forward
        self.is_group = is_group
        self.parsed = ParsingUtilities.parse_image(file_location)
        self.timestamp = time.time()

    def serialize(self):
        timestamp = str(int(round(self.timestamp * 1000)))
        message_type = "groupchat" if self.is_group else "chat"
        data = (
            f'<message to="{self.peer_jid}" id="{self.message_id}" cts="{timestamp}" type="{message_type}" xmlns="jabber:client">'
            f'<kik timestamp="{timestamp}" qos="true" push="true"/>'
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

        
        packets =  [data[s:s+16384].encode() for s in range(0, len(data), 16384)]
        return list(packets)


class OutgoingGroupChatImage(OutgoingChatImage):
    """
    Represents an outgoing image chat message to a group
    """
    def __init__(self, group_jid, file_location, forward):
        super().__init__(group_jid, file_location, is_group=True, forward=forward)


class IncomingChatMessage(XMPPResponse):
    """
    Represents an incoming text chat message from another user
    """
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true' if 'd' in data.request.attrs else False
        self.request_read_receipt = data.request['r'] == 'true' if 'r' in data.request.attrs else False
        self.status = data.status.text if data.status else None
        self.preview = data.preview.text if data.preview else None

        self.from_jid = data['from']
        self.to_jid = data['to']
        self.body = data.body.text if data.body else None
        self.is_typing = data.find('is-typing')
        self.is_typing = self.is_typing['val'] == 'true' if self.is_typing else None


class IncomingGroupChatMessage(IncomingChatMessage):
    """
    Represents an incoming text chat message from a group
    """
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.group_jid = data.g['jid']
        # Messages from public groups include an alias user which can be resolved with client.xiphias_get_users_by_alias
        self.alias_sender = data.find('alias-sender').text if data.find('alias-sender') else None


class OutgoingReadReceipt(XMPPElement):
    """
    Represents an outgoing read receipt to a specific user, for one or more messages
    """
    def __init__(self, peer_jid, receipt_message_id, group_jid=None):
        super().__init__()
        self.peer_jid = peer_jid
        self.receipt_message_id = receipt_message_id
        self.group_jid = group_jid

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))
        group_line = f'<g jid=\"{self.group_jid}\" />'
        data = (f'<message type="receipt" id="{self.message_id}" to="{self.peer_jid}" cts="{timestamp}">'
                f'<kik push="false" qos="true" timestamp="{timestamp}" />'
                '<receipt xmlns="kik:message:receipt" type="read">'
                f'<msgid id="{self.receipt_message_id}" />'
                '</receipt>')
        if 'groups' in group_line:
            data = data + group_line + '</message>'
        else:
            data = f'{data}</message>'
        return data.encode()


class OutgoingDeliveredReceipt(XMPPElement):
    def __init__(self, peer_jid, receipt_message_id, group_jid=None):
        super().__init__()

        self.group_jid = group_jid
        self.peer_jid = peer_jid
        self.receipt_message_id = receipt_message_id

    def serialize(self):
        if self.group_jid and 'groups.kik.com' in self.group_jid:
            g_tag = f' g=\"{self.group_jid}\"'
        else:
            g_tag = ''

        timestamp = str(int(round(time.time() * 1000)))
        data = (f'<iq type="set" id="{self.message_id}" cts="{timestamp}">'
                '<query xmlns="kik:iq:QoS">'
                '<msg-acks>'
                f'<sender jid="{self.peer_jid}"{g_tag}>'
                f'<ack-id receipt="true">{self.receipt_message_id}</ack-id>'
                '</sender>'
                '</msg-acks>'
                '<history attach="false" />'
                '</query>'
                '</iq>')
        return data.encode()


class OutgoingIsTypingEvent(XMPPElement):
    def __init__(self, peer_jid, is_typing):
        super().__init__()
        self.peer_jid = peer_jid
        self.is_typing = is_typing

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))
        data = (f'<message type="chat" to="{self.peer_jid}" id="{self.message_id}">'
                f'<kik push="false" qos="false" timestamp="{timestamp}" />'
                f'<is-typing val="{str(self.is_typing).lower()}" />'
                '</message>')
        return data.encode()


class OutgoingGroupIsTypingEvent(XMPPElement):
    def __init__(self, group_jid, is_typing):
        super().__init__()
        self.peer_jid = group_jid
        self.is_typing = is_typing

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))
        data = (f'<message type="groupchat" to="{self.peer_jid}" id="{self.message_id}">'
                '<pb></pb>'
                f'<kik push="false" qos="false" timestamp="{timestamp}" />'
                f'<is-typing val="{str(self.is_typing).lower()}" />'
                '</message>')
        return data.encode()


class OutgoingLinkShareEvent(XMPPElement):
    def __init__(self, peer_jid, link, title, text, app_name):
        super().__init__()
        self.peer_jid = peer_jid
        self.link = link
        self.title = title
        self.text = text
        self.app_name = app_name

    def serialize(self):
        message_type = 'type="groupchat" xmlns="kik:groups"' if 'group' in self.peer_jid else 'type="chat"'
        timestamp = str(int(round(time.time() * 1000)))
        
        data = (f'<message {message_type} to="{self.peer_jid}" id="{self.message_id}" cts="{timestamp}">'
                '<pb></pb>'
                f'<kik push="true" qos="true" timestamp="{timestamp}" />'
                '<request xmlns="kik:message:receipt" r="true" d="true" />'
                f'<content id="{self.message_id}" app-id="com.kik.cards" v="2">'
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


class IncomingMessageReadEvent(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.receipt_message_id = data.receipt.msgid['id']
        self.from_jid = data['from']
        self.group_jid = data.g['jid'] if data.g else None


class IncomingMessageDeliveredEvent(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.receipt_message_id = data.receipt.msgid['id']
        self.from_jid = data['from']
        self.group_jid = data.g['jid'] if data.g else None


class IncomingIsTypingEvent(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.from_jid = data['from']
        self.is_typing = data.find('is-typing')['val'] == 'true'


class IncomingGroupIsTypingEvent(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.from_jid = data['from']
        self.is_typing = data.find('is-typing')['val'] == 'true'
        self.group_jid = data.g['jid']


class IncomingGroupStatus(XMPPResponse):
    """ xmlns=jabber:client type=groupchat """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true' if data.request and 'd' in data.request.attrs else False
        self.requets_read_receipt = data.request['r'] == 'true' if data.request and 'r' in data.request.attrs else False
        self.group_jid = data['from']
        self.to_jid = data['to']
        self.status = data.status.text if data.status else None
        self.status_jid = data.status['jid'] if data.status and 'jid' in data.status.attrs else None
        self.group = Group(data.g) if data.g and len(data.g.contents) > 0 else None


class IncomingGroupSysmsg(XMPPResponse):
    """ xmlns=jabber:client type=groupchat """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true' if data.request and 'd' in data.request.attrs else False
        self.requets_read_receipt = data.request['r'] == 'true' if data.request and 'r' in data.request.attrs else False
        self.group_jid = data['from']
        self.to_jid = data['to']
        self.sysmsg_xmlns = data.sysmsg['xmlns'] if data.sysmsg and 'xmlns' in data.sysmsg.attrs else None
        self.sysmsg = data.sysmsg.text if data.sysmsg else None
        self.group = Group(data.g) if data.g and len(data.g.contents) > 0 else None


class IncomingGroupReceiptsEvent(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.from_jid = data['from']
        self.to_jid = data['to']
        self.group_jid = data.g['jid']
        self.receipt_ids = [msgid['id'] for msgid in data.receipt.findAll('msgid')]
        self.type = data.receipt['type']


class IncomingFriendAttribution(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        friend_attribution = data.find('friend-attribution')
        self.context_type = friend_attribution.context['type']
        self.referrer_jid = friend_attribution.context['referrer']
        self.reply = friend_attribution.context['reply'] == 'true'
        self.body = friend_attribution.body.text


class IncomingStatusResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        status = data.find('status')
        self.from_jid = data['from']
        self.status = status.text
        self.special_visibility = status['special-visibility'] == 'true'
        self.status_jid = status['jid']


class IncomingImageMessage(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true' if data.request and 'd' in data.request.attrs else False
        self.requets_read_receipt = data.request['r'] == 'true' if data.request and 'r' in data.request.attrs else False
        self.image_url = data.find('file-url').get_text() if data.find('file-url') else None
        self.status = data.status.text if data.status else None
        self.from_jid = data['from']
        self.to_jid = data['to']
        self.group_jid = data.g['jid'] if data.g and 'jid' in data.g.attrs else None


class IncomingGroupSticker(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        content = data.content or data
        extras_map = self.parse_extras(content.extras)
        self.from_jid = data['from'] if data else None
        self.group_jid = data.g['jid'] if data.g and 'jid' in data.g.attrs else None
        self.sticker_pack_id = extras_map['sticker_pack_id'] if 'sticker_pack_id' in extras_map else None
        self.sticker_url = extras_map['sticker_url'] if 'sticker_url' in extras_map else None
        self.sticker_id = extras_map['sticker_id'] if 'sticker_id' in extras_map else None
        self.sticker_source = extras_map['sticker_source'] if 'sticker_source' in extras_map else None
        self.png_preview = content.images.find('png-preview').text if content.images.find('png-preview') else None
        self.uris = []
        self.uris.extend(self.Uri(uri) for uri in content.uris)

    class Uri:
        def __init__(self, uri):
            self.platform = uri['platform']
            self.url = uri.text

    @staticmethod
    def parse_extras(extras):
        return {item.key.string: item.val.text for item in extras.findAll('item')}


class IncomingGifMessage(XMPPResponse):
    """
    Represents an incoming GIF message from another kik entity, sent as a URL
    """
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true' if data.request and 'd' in data.request.attrs else False
        self.requets_read_receipt = data.request['r'] == 'true' if data.request and 'r' in data.request.attrs else False
        self.status = data.status.text if data.status else None
        self.from_jid = data['from'] if data else None
        self.to_jid = data['to'] if data else None
        self.group_jid = data.g['jid'] if data.g and 'jid' in data.g.attrs else None
        self.uris = [self.Uri(uri) for uri in data.content.uris]

    class Uri:
        def __init__(self, uri):
            self.file_content_type = uri['file-content-type']
            self.type = uri['type']
            self.url = uri.text


class OutgoingGIFMessage(XMPPElement):
    """
	Represents an outgoing GIF message to another kik entity (member or group)
	"""
    def __init__(self, peer_jid, search_term, is_group=True):
        super().__init__()
        self.peer_jid = peer_jid
        self.allow_forward = True
        self.is_group = is_group
        self.gif_preview, self.gif_data = self.get_gif_data(search_term)

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))
        message_type = "groupchat" if self.is_group else "chat"
        data = (
            '<message cts="{0}" type="{1}" to="{12}" id="{2}" xmlns="jabber:client">'
            '<kik push="true" timestamp="{3}" qos="true"/>'
            '<pb/>'
            '<content id="{4}" v="2" app-id="com.kik.ext.gif">'
            '<strings>'
            '<app-name>GIF</app-name>'
            '<layout>video</layout>'
            '<allow-forward>true</allow-forward>'
            '<disallow-save>true</disallow-save>'
            '<video-should-autoplay>true</video-should-autoplay>'
            '<video-should-loop>true</video-should-loop>'
            '<video-should-be-muted>true</video-should-be-muted>'
            '</strings>'
            '<images>'
            '<icon></icon>'
            '<preview>{5}</preview>'
            '</images>'
            '<uris>'
            '<uri priority="0" type="video" file-content-type="video/mp4">{6}</uri>'
            '<uri priority="1" type="video" file-content-type="video/webm">{7}</uri>'
            '<uri priority="0" type="video" file-content-type="video/tinymp4">{8}</uri>'
            '<uri priority="1" type="video" file-content-type="video/tinywebm">{9}</uri>'
            '<uri priority="0" type="video" file-content-type="video/nanomp4">{10}</uri>'
            '<uri priority="1" type="video" file-content-type="video/nanowebm">{11}</uri>'
            '</uris>'
            '</content>'
            '<request r="true" d="true" xmlns="kik:message:receipt"/>'
            '</message>'
        ).format(timestamp, message_type, self.message_id, timestamp, self.message_id, self.gif_preview,
                    self.gif_data["mp4"]["url"], self.gif_data["webm"]["url"], self.gif_data["tinymp4"]["url"],
                    self.gif_data["tinywebm"]["url"], self.gif_data["nanomp4"]["url"],
                    self.gif_data["nanowebm"]["url"], self.peer_jid)

        packets = [data[s:s + 16384].encode() for s in range(0, len(data), 16384)]
        return list(packets)

    def get_gif_data(self, search_term):
        apikey = ""  # add api key from https://tenor.com/gifapi
        if not apikey:
            raise Exception("A tendor.com API key is required to search for GIFs images. please get one and change it")

        r = requests.get(f"https://api.tenor.com/v1/search?q={search_term}&key={apikey}&limit=1")
        if r.status_code == 200:
            gif = json.loads(r.content.decode('ascii'))
            response = requests.get(gif["results"][0]["media"][0]["nanomp4"]["preview"])
            img = Image.open(BytesIO(response.content))
            buffered = BytesIO()

            img.convert("RGB").save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('ascii')
            return img_str, gif["results"][0]["media"][0]
        else:
            return ""


class IncomingVideoMessage(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true' if data.request and 'd' in data.request.attrs else False
        self.requets_read_receipt = data.request['r'] == 'true' if data.request and 'r' in data.request.attrs else False
        self.video_url = data.find('file-url').text
        self.file_content_type = data.find('file-content-type').text if data.find('file-content-type') else None
        self.duration_milliseconds = data.find('duration').text if data.find('duration') else None
        self.file_size = data.find('file-size').text
        self.from_jid = data['from']
        self.to_jid = data['to']
        self.group_jid = data.g['jid'] if data.g and 'jid' in data.g.attrs else None


class IncomingCardMessage(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true' if data.request and 'd' in data.request.attrs else False
        self.request_read_receipt = data.request['r'] == 'true' if data.request and 'r' in data.request.attrs else False
        self.from_jid = data['from']
        self.to_jid = data['to']
        self.group_jid = data.g['jid'] if data.g and 'jid' in data.g.attrs else None
        self.app_name = data.find('app-name').text if data.find('app-name') else None
        self.card_icon = data.find('card-icon').text if data.find('card-icon') else None
        self.layout = data.find('layout').text if data.find('layout') else None
        self.title = data.find('title').text if data.find('title') else None
        self.text = data.find('text').text if data.find('text') else None
        self.allow_forward = data.find('allow-forward').text if data.find('allow-forward') else None
        self.icon = data.find('icon').text if data.find('icon') else None
        self.uri = data.find('uri').text if data.find('uri') else None


