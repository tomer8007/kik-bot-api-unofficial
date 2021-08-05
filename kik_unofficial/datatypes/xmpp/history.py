from bs4 import BeautifulSoup
import time

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse

class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)

class OutgoingAcknowledgement(XMPPElement):
    """
    Represents an outgoing acknowledgement for a message ID
    """
    def __init__(self, sender_jid, is_receipt, ack_id, group_jid):
        super().__init__()
        self.sender_jid = sender_jid
        self.group_jid = group_jid
        self.is_receipt = is_receipt
        self.ack_id = ack_id

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))

        user_ack_data = (
                        '<sender jid="{}">'
                        '<ack-id receipt="{}">{}</ack-id>'
                        '</sender>'
                        ).format(self.sender_jid, str(self.is_receipt).lower(), self.ack_id)

        group_ack_data = (
                         '<sender jid="{}" g="{}">'
                         '<ack-id receipt="{}">{}</ack-id>'
                         '</sender>'
                         ).format(self.sender_jid, self.group_jid, str(self.is_receipt).lower(), self.ack_id)

        data = ('<iq type="set" id="{}" cts="{}">'
                '<query xmlns="kik:iq:QoS">'
                '<msg-acks>'
                '{}'
                '</msg-acks>'
                '<history attach="false" />'
                '</query>'
                '</iq>'
                ).format(self.message_id, timestamp, user_ack_data if self.group_jid != None else group_ack_data)
        return data.encode()

class OutgoingHistoryRequest(XMPPElement):
    """
    Represents an outgoing request for the account's messaging history
    """
    def __init__(self):
        super().__init__()

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))

        data = ('<iq type="set" id="{}" cts="{}">'
                '<query xmlns="kik:iq:QoS">'
                '<msg-acks />'
                '<history attach="true" />'
                '</query>'
                '</iq>'
                ).format(self.message_id, timestamp,)
        return data.encode()

class HistoryResponse(XMPPResponse):
    """
    Represents a Kik messaging history response.
    """
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.id = data["id"]

        if data.query.history:
            self.more = data.query.history.has_attr("more")
            self.from_jid = data["from"]
            self.messages = []
            for message in data.query.history:
                if message["type"] == "receipt":
                    args = {
                            'type':'receipt',
                            'from_jid': message["from"],
                            'receipt_type':message.receipt["type"],
                            'id':message.receipt.msgid["id"]
                            }
                    self.messages.append(Struct(**args))
                elif message["type"] == "chat":
                    args = {
                            'type':'chat',
                            'id':message["id"],
                            'from_jid':message["from"],
                            'body': message.body.text if message.body else None,
                            'preview': message.preview.text if message.preview else None,
                            'timestamp': message.kik["timestamp"]
                            }
                    self.messages.append(Struct(**args))
                elif message["type"] == "groupchat":
                    args = {
                            'type': 'groupchat',
                            'id': message["id"],
                            'from_jid': message["from"],
                            'body': message.body.text if message.body else None,
                            'preview': message.preview.text if message.preview else None,
                            'timestamp': message.kik["timestamp"],
                            'group_jid': message.g["jid"]
                            }
                    self.messages.append(Struct(**args))
