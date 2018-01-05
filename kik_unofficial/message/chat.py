import time

from bs4 import BeautifulSoup
from kik_unofficial.message.message import Message, Response
from kik_unofficial.utilities import Utilities


class ChatMessage(Message):
    def __init__(self, peer_jid, body):
        super().__init__()
        self.peer_jid = peer_jid
        self.body = body

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))
        data = ('<message type="chat" to="{}" id="{}" cts="{}">'
                '<body>{}</body>'
                '<preview>{}</preview>'
                '<kik push="true" qos="true" timestamp="{}" />'
                '<request xmlns="kik:message:receipt" r="true" d="true" />'
                '<ri></ri>'
                '</message>'
                ).format(self.peer_jid, self.message_id, timestamp, Utilities.escape_xml(self.body),
                         Utilities.escape_xml(self.body[0:20]), timestamp)
        return data.encode()


class GroupChatMessage(Message):
    def __init__(self, group_jid, body):
        super().__init__()
        self.group_jid = group_jid
        self.body = body

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))
        data = ('<message type="groupchat" to="{}" id="{}" cts="{}">'
                '<body>{}</body>'
                '<pb></pb>'
                '<preview>{}</preview>'
                '<kik push="true" qos="true" timestamp="{}" />'
                '<request xmlns="kik:message:receipt" r="true" d="true" />'
                '<ri></ri>'
                '</message>'
                ).format(self.group_jid, self.message_id, timestamp, Utilities.escape_xml(self.body),
                         Utilities.escape_xml(self.body[0:20]), timestamp)
        return data.encode()


class ReadReceiptMessage(Message):
    def __init__(self, peer_jid, receipt_message_id):
        super().__init__()
        self.peer_jid = peer_jid
        self.receipt_message_id = receipt_message_id

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))
        data = ('<message type="receipt" id="{}" to="{}" cts="{}">'
                '<kik push="false" qos="true" timestamp="{}" />'
                '<receipt xmlns="kik:message:receipt" type="read">'
                '<msgid id="{}" />'
                '</receipt>'
                '</message>').format(self.message_id, self.peer_jid, timestamp, timestamp, self.receipt_message_id)
        return data.encode()


class DeliveredReceiptMessage(Message):
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


class IsTypingMessage(Message):
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


class IsTypingResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.from_jid = data['from']
        self.is_typing = data.find('is-typing')['val'] == 'true'


class GroupIsTypingMessage(Message):
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


class GroupIsTypingResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.from_jid = data['from']
        self.is_typing = data.find('is-typing')['val'] == 'true'
        self.group_jid = data.g['jid']


class MessageDeliveredResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.receipt_message_id = data.receipt.msgid['id']
        self.from_jid = data['from']


class MessageReadResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.receipt_message_id = data.receipt.msgid['id']
        self.from_jid = data['from']


class MessageResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true'
        self.requets_read_receipt = data.request['r'] == 'true'
        self.body = data.body.text
        self.status = data.status.text if data.status else None
        self.from_jid = data['from']
        self.to_jid = data['to']


class GroupMessageResponse(Response):
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


class GroupStatusResponse(Response):
    """ xmlns=jabber:client type=groupchat """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true' if data.request else False
        self.requets_read_receipt = data.request['r'] == 'true' if data.request else False
        self.group_jid = data['from']
        self.to_jid = data['to']
        self.sysmsg = data.sysmsg.text if data.sysmsg else None
        self.status = data.status.text if data.status else None


class GroupReceiptResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.from_jid = data['from']
        self.to_jid = data['to']
        self.group_jid = data.g['jid']
        self.receipt_ids = [msgid['id'] for msgid in data.receipt.findAll('msgid')]


class FriendAttributionResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        friend_attribution = data.find('friend-attribution')
        self.context_type = friend_attribution.context['type']
        self.referrer_jid = friend_attribution.context['referrer']
        self.reply = friend_attribution.context['reply'] == 'true'
        self.body = friend_attribution.body.text
