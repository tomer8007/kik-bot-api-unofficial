import time

from bs4 import BeautifulSoup
from kik_unofficial.datatypes.peers import Group
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse
from kik_unofficial.utilities.parsing import ParsingUtilities

class OutgoingMessage(XMPPElement):
    def __init__(self, peer_jid, body, message_type):
        super().__init__()
        self.peer_jid = peer_jid
        self.body = body
        self.message_type = message_type

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))
        data = ('<message type="{}" to="{}" id="{}" cts="{}">'
                '<body>{}</body>'
                '<preview>{}</preview>'
                '<kik push="true" qos="true" timestamp="{}" />'
                '<request xmlns="kik:message:receipt" r="true" d="true" />'
                '<ri></ri>'
                '</message>'
                ).format(self.message_type, self.peer_jid, self.message_id, timestamp, ParsingUtilities.escape_xml(self.body),
                         ParsingUtilities.escape_xml(self.body[0:20]), timestamp)
        return data.encode()

class IncomingChatMessage(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true'
        self.requets_read_receipt = data.request['r'] == 'true'
        self.body = data.body.text
        self.status = data.status.text if data.status else None
        self.from_jid = data['from']
        self.to_jid = data['to']


class IncomingGroupChatMessage(XMPPResponse):
    """ xmlns=kik:groups type=groupchat """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true' if data.request else False
        self.requets_read_receipt = data.request['r'] == 'true' if data.request else False
        self.body = data.body.text if data.body else None
        self.preview = data.preview.text if data.preview else None
        self.from_jid = data['from']
        self.to_jid = data['to']
        self.group_jid = data.g['jid']
        self.is_typing = data.find('is-typing')
        self.is_typing = self.is_typing['val'] == 'true' if self.is_typing else None


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
                '</message>').format(self.peer_jid, self.message_id, timestamp, self.is_typing)
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
                '</message>').format(self.peer_jid, self.message_id, timestamp, self.is_typing)
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
        self.image_url = data.find('file-url').get_text()
        self.status = data.status.text if data.status else None
        self.from_jid = data['from']
        self.to_jid = data['to']


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
