from bs4 import BeautifulSoup
from lxml import etree
import time

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse


class KikHistoryItem:
    def __init__(self, message: BeautifulSoup):
        super().__init__()
        self.message = message
        self.type = message['type']
        self.id = message['id']
        self.correspondent_jid = message['from']

        g = message.find('g', recursive=False)
        if g:
            self.bin_jid = g['jid']
        else:
            self.bin_jid = self.correspondent_jid
            self.is_group = False

        from kik_unofficial.client import KikClient
        self.is_group = KikClient.is_group_jid(self.bin_jid)

        request_element = message.find('request', recursive=False)
        if request_element and request_element['xmlns'] == 'kik:message:receipt' and request_element['d'] == 'true':
            self.requests_delivered_receipt = True
        else:
            self.requests_delivered_receipt = False


class OutgoingAcknowledgement(XMPPElement):
    """
    Represents an outgoing acknowledgement for a message ID
    """
    def __init__(self, messages: list[KikHistoryItem] | KikHistoryItem | None, request_history: bool = False):
        super().__init__()
        self.request_history = request_history
        if isinstance(messages, list):
            self.messages = messages
        elif isinstance(messages, KikHistoryItem):
            self.messages = [messages]
        else:
            self.messages = []

        if len(self.messages) == 0 and not self.request_history:
            raise Exception('invalid arguments to OutgoingAcknowledgement (no messages and request_history is false)')

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))

        iq = etree.Element('iq')
        iq.set('type', 'set')
        iq.set('id', self.message_id)
        iq.set('cts', timestamp)

        query = etree.SubElement(iq, 'query')
        query.set('xmlns', 'kik:iq:QoS')

        msg_acks = etree.SubElement(query, 'msg-acks')
        self._compute_msg_acks(msg_acks)

        history = etree.SubElement(query, 'history')
        history.set('attach', 'true' if self.request_history else 'false')

        return etree.tostring(iq, encoding='utf-8', pretty_print=False, method='xml')

    def _compute_msg_acks(self, msg_acks):
        temp_map = {}

        for message in self.messages:
            map_key = message.bin_jid + message.correspondent_jid + str(message.is_group)
            if map_key in temp_map:
                items = temp_map.get(map_key)
            else:
                items = list[KikHistoryItem]()
                temp_map[map_key] = items

            items.append(message)

        batches = list(iter(temp_map.values()))
        for batch in batches:
            owner = batch[0]
            bin_jid = owner.bin_jid
            correspondent_jid = owner.correspondent_jid
            needs_group_tag = owner.is_group and bin_jid != correspondent_jid

            sender = etree.SubElement(msg_acks, 'sender')
            sender.set('jid', correspondent_jid)
            if needs_group_tag:
                sender.set('g', bin_jid)

            for message in batch:
                ack_id = etree.SubElement(sender, 'ack-id')
                ack_id.set('receipt', 'true' if message.requests_delivered_receipt else 'false')
                ack_id.text = message.id


class OutgoingHistoryRequest(XMPPElement):
    """
    Represents an outgoing request for the account's messaging history
    """
    def __init__(self):
        super().__init__()

    def serialize(self):
        timestamp = str(int(round(time.time() * 1000)))

        data = (f'<iq type="set" id="{self.message_id}" cts="{timestamp}">'
                '<query xmlns="kik:iq:QoS">'
                '<msg-acks />'
                '<history attach="true" />'
                '</query>'
                '</iq>')
        return data.encode()


class HistoryResponse(XMPPResponse):
    """
    Represents a Kik messaging history response.
    """
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.more = False
        self.messages = []

        if data.query.history:
            self.more = data.query.history.has_attr('more')
            for message in data.query.history.find_all('msg', recursive=False):
                self.messages.append(KikHistoryItem(message))
