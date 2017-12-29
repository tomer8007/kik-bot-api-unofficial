import time

from bs4 import BeautifulSoup
from kik_unofficial.message.message import Message, Response


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
                ).format(self.peer_jid, self.message_id, timestamp, self.body, self.body[0:20], timestamp)
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
                ).format(self.group_jid, self.message_id, timestamp, self.body, self.body[0:20], timestamp)
        return data.encode()


class MessageDeliveredResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.receipt_message_id = data.receipt.msgid['id']


class MessageReadResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.receipt_message_id = data.receipt.msgid['id']


class MessageResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true'
        self.requets_read_receipt = data.request['r'] == 'true'
        self.body = data.body.text
        self.from_jid = data['from']
        self.to_jid = data['to']


class GroupMessageResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.request_delivered_receipt = data.request['d'] == 'true'
        self.requets_read_receipt = data.request['r'] == 'true'
        self.body = data.body.text
        self.preview = data.preview.text
        self.from_jid = data['from']
        self.to_jid = data['to']

