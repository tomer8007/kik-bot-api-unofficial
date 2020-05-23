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
        message_type = "chat" if not self.is_group else "groupchat"
        bot_mention_data = ('<mention>'
                            '<bot>{}</bot>'
                            '</mention>').format(self.bot_mention_jid) if self.bot_mention_jid else ''
        data = ('<message type="{}" to="{}" id="{}" cts="{}">'
                '<body>{}</body>'
                '{}'
                '<preview>{}</preview>'
                '<kik push="true" qos="true" timestamp="{}" />'
                '<request xmlns="kik:message:receipt" r="true" d="true" />'
                '<ri></ri>'
                '</message>'
                ).format(message_type, self.peer_jid, self.message_id, timestamp,
                         ParsingUtilities.escape_xml(self.body), bot_mention_data,
                         ParsingUtilities.escape_xml(self.body[0:20]),
                         timestamp)
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
        message_type = "chat" if not self.is_group else "groupchat"
        data = (
            '<message to="{0}" id="{1}" cts="{2}" type="{3}" xmlns="jabber:client">'
            '<kik timestamp="{2}" qos="true" push="true"/>'
            '<request xmlns="kik:message:receipt" d="true" r="true" />'
            '<content id="{4}" v="2" app-id="com.kik.ext.gallery">'
            '<strings>'
            '<app-name>Gallery</app-name>'
            '<file-size>{5}</file-size>'
            '<allow-forward>{6}</allow-forward>'
            '<disallow-save>false</disallow-save>'
            '<file-content-type>image/jpeg</file-content-type>'
            '<file-name>{4}.jpg</file-name>'
            '</strings>'
            '<extras />'
            '<hashes>'
            '<sha1-original>{8}</sha1-original>'
            '<sha1-scaled>{9}</sha1-scaled>'
            '<blockhash-scaled>{10}</blockhash-scaled>'
            '</hashes>'
            '<images>'
            '<preview>{7}</preview>'
            '<icon></icon>'
            '</images>'
            '<uris />'
            '</content>'
            '</message>'
        ).format(self.peer_jid, self.message_id, timestamp, message_type, self.content_id,
                 self.parsed['size'], str(self.allow_forward).lower(), self.parsed['base64'], self.parsed['SHA1'], 
                 self.parsed['SHA1Scaled'], self.parsed['blockhash'])

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
        self.request_delivered_receipt = data.request['d'] == 'true' if data.request else False
        self.request_read_receipt = data.request['r'] == 'true' if data.request else False
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
        group_line = "<g jid=\"{}\" />".format(self.group_jid)
        data = ('<message type="receipt" id="{}" to="{}" cts="{}">'
                '<kik push="false" qos="true" timestamp="{}" />'
                '<receipt xmlns="kik:message:receipt" type="read">'
                '<msgid id="{}" />'
                '</receipt>').format(self.message_id, self.peer_jid, timestamp, timestamp, self.receipt_message_id)
        if 'groups' in group_line:
            data = data + group_line + '</message>'
        else:
            data = data + '</message>'
        return data.encode()


class OutgoingDeliveredReceipt(XMPPElement):
    def __init__(self, peer_jid, receipt_message_id):
        super().__init__()
        self.peer_jid = peer_jid
        self.receipt_message_id = receipt_message_id

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))
        data = ('<message type="receipt" id="{}" to="{}" cts="{}">'
                '<kik push="false" qos="true" timestamp="{}" />'
                '<receipt xmlns="kik:message:receipt" type="delivered">'
                '<msgid id="{}" />'
                '</receipt>'
                '</message>').format(self.message_id, self.peer_jid, timestamp, timestamp, self.receipt_message_id)
        return data.encode()


class OutgoingIsTypingEvent(XMPPElement):
    def __init__(self, peer_jid, is_typing):
        super().__init__()
        self.peer_jid = peer_jid
        self.is_typing = is_typing

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))
        data = ('<message type="chat" to="{}" id="{}">'
                '<kik push="false" qos="false" timestamp="{}" />'
                '<is-typing val="{}" />'
                '</message>').format(self.peer_jid, self.message_id, timestamp, str(self.is_typing).lower())
        return data.encode()


class OutgoingGroupIsTypingEvent(XMPPElement):
    def __init__(self, group_jid, is_typing):
        super().__init__()
        self.peer_jid = group_jid
        self.is_typing = is_typing

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))
        data = ('<message type="groupchat" to="{}" id="{}">'
                '<pb></pb>'
                '<kik push="false" qos="false" timestamp="{}" />'
                '<is-typing val="{}" />'
                '</message>').format(self.peer_jid, self.message_id, timestamp, str(self.is_typing).lower())
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
        data = ('<message {0} to="{1}" id="{2}" cts="{3}">'
                '<pb></pb>'
                '<kik push="true" qos="true" timestamp="{3}" />'
                '<request xmlns="kik:message:receipt" r="true" d="true" />'
                '<content id="{2}" app-id="com.kik.cards" v="2">'
                '<strings>'
                '<app-name>{4}</app-name>'
                '<layout>article</layout>'
                '<title>{5}</title>'
                '<text>{6}</text>'
                '<allow-forward>true</allow-forward>'
                '</strings>'
                '<extras />'
                '<hashes />'
                '<images>'
                '</images>'
                '<uris>'
                '<uri platform="cards">{7}</uri>'
                '<uri></uri>'
                '<uri>http://cdn.kik.com/cards/unsupported.html</uri>'
                '</uris>'
                '</content>'
                '</message>').format(message_type, self.peer_jid, self.message_id, timestamp, self.app_name, self.title,
                                     self.text, self.link)
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
        self.request_delivered_receipt = data.request['d'] == 'true' if data.request else False
        self.requets_read_receipt = data.request['r'] == 'true' if data.request else False
        self.group_jid = data['from']
        self.to_jid = data['to']
        self.status = data.status.text if data.status else None
        self.status_jid = data.status['jid'] if data.status and 'jid' in data.status.attrs else None
        self.group = Group(data.g) if data.g and len(data.g.contents) > 0 else None


class IncomingGroupSysmsg(XMPPResponse):
    """ xmlns=jabber:client type=groupchat """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true' if data.request else False
        self.requets_read_receipt = data.request['r'] == 'true' if data.request else False
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
        self.request_delivered_receipt = data.request['d'] == 'true'
        self.requets_read_receipt = data.request['r'] == 'true'
        self.image_url = data.find('file-url').get_text() if data.find('file-url') else None
        self.status = data.status.text if data.status else None
        self.from_jid = data['from']
        self.to_jid = data['to']
        self.group_jid = data.g['jid'] if data.g else None


class IncomingGroupSticker(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        content = data.content
        extras_map = self.parse_extras(content.extras)
        self.from_jid = data['from']
        self.group_jid = data.g['jid']
        self.sticker_pack_id = extras_map['sticker_pack_id'] if 'sticker_pack_id' in extras_map else None
        self.sticker_url = extras_map['sticker_url'] if 'sticker_url' in extras_map else None
        self.sticker_id = extras_map['sticker_id'] if 'sticker_id' in extras_map else None
        self.sticker_source = extras_map['sticker_source'] if 'sticker_source' in extras_map else None
        self.png_preview = content.images.find('png-preview').text if content.images.find('png-preview') else None
        self.uris = []
        for uri in content.uris:
            self.uris.append(self.Uri(uri))

    class Uri:
        def __init__(self, uri):
            self.platform = uri['platform']
            self.url = uri.text

    @staticmethod
    def parse_extras(extras):
        extras_map = {}
        for item in extras.findAll('item'):
            extras_map[item.key.string] = item.val.text
        return extras_map


class IncomingGifMessage(XMPPResponse):
    """
    Represents an incoming GIF message from another kik entity, sent as a URL
    """
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true'
        self.requets_read_receipt = data.request['r'] == 'true'
        self.status = data.status.text if data.status else None
        self.from_jid = data['from']
        self.to_jid = data['to']
        self.group_jid = data.g['jid']
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
        message_type = "chat" if not self.is_group else "groupchat"
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
        if apikey == "":
            raise Exception("A tendor.com API key is required to search for GIFs images. please get one and change it")

        r = requests.get("https://api.tenor.com/v1/search?q=%s&key=%s&limit=1" % (search_term, apikey))
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
        self.request_delivered_receipt = data.request['d'] == 'true'
        self.requets_read_receipt = data.request['r'] == 'true'
        self.video_url = data.find('file-url').text
        self.file_content_type = data.find('file-content-type').text if data.find('file-content-type') else None
        self.duration_milliseconds = data.find('duration').text if data.find('duration') else None
        self.file_size = data.find('file-size').text
        self.from_jid = data['from']
        self.to_jid = data['to']
        self.group_jid = data.g['jid']


class IncomingCardMessage(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true'
        self.request_read_receipt = data.request['r'] == 'true'
        self.from_jid = data['from']
        self.to_jid = data['to']
        self.group_jid = data.g['jid']
        self.app_name = data.find('app-name').text if data.find('app-name') else None
        self.card_icon = data.find('card-icon').text if data.find('card-icon') else None
        self.layout = data.find('layout').text if data.find('layout') else None
        self.title = data.find('title').text if data.find('title') else None
        self.text = data.find('text').text if data.find('text') else None
        self.allow_forward = data.find('allow-forward').text if data.find('allow-forward') else None
        self.icon = data.find('icon').text if data.find('icon') else None
        self.uri = data.find('uri').text if data.find('uri') else None


