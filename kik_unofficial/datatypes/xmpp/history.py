from __future__ import annotations

from typing import Union, final

from bs4 import BeautifulSoup
from lxml import etree

from lxml.etree import Element

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse
from kik_unofficial.utilities.kik_server_clock import KikServerClock


class OutgoingAcknowledgement(XMPPElement):
    """
    Represents an outgoing acknowledgement for a list of history items
    """
    def __init__(self, messages: Union[list[XMPPResponse], XMPPResponse, None], request_history: bool = False):
        super().__init__()
        self.request_history = request_history
        if isinstance(messages, list):
            self.messages = messages
        elif isinstance(messages, XMPPResponse):
            self.messages = [messages]
        else:
            self.messages = []

    @final
    def serialize(self) -> Element:
        timestamp = str(KikServerClock.get_server_time())

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

        return iq

    def _compute_msg_acks(self, msg_acks):
        sender_map = dict()
        for message in self.messages:
            map_key = message.from_jid
            if message.is_group:
                map_key += message.group_jid

            if map_key in sender_map:
                items = sender_map.get(map_key)
            else:
                items = list[XMPPResponse]()
                sender_map[map_key] = items
            items.append(message)

        for batch in sender_map.values():
            owner = batch[0]
            correspondent_jid = owner.from_jid
            needs_group_tag = owner.group_jid is not None and owner.group_jid != correspondent_jid

            sender = etree.SubElement(msg_acks, 'sender')
            sender.set('jid', owner.from_jid)
            if needs_group_tag:
                sender.set('g', owner.group_jid)

            for message in batch:
                ack_id = etree.SubElement(sender, 'ack-id')
                ack_id.set('receipt', 'true' if message.request_delivered_receipt else 'false')
                ack_id.text = message.message_id


class OutgoingHistoryRequest(OutgoingAcknowledgement):
    """
    Represents an outgoing request for the account's messaging history
    """
    def __init__(self):
        super().__init__(messages=None, request_history=True)


class HistoryResponse(XMPPResponse):
    """
    Represents a Kik messaging history response.
    """
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.more = False
        self.messages = []  # type: list[XMPPResponse]

        history = data.find('query', recursive=False).find('history', recursive=False)
        if history:
            self.more = history['more'] == '1' if history.has_attr('more') else False
            for message in history.find_all('msg', recursive=False):
                self.messages.append(XMPPResponse(message))
