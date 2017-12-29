from bs4 import BeautifulSoup

from kik_unofficial.message.message import Message


class RosterMessage(Message):
    def __init__(self):
        super().__init__()

    def serialize(self) -> bytes:
        data = ('<iq type="get" id="{}">'
                '<query p="8" xmlns="jabber:iq:roster" />'
                '</iq>').format(self.message_id)

        return data.encode()


class RosterResponse:
    def __init__(self, data: BeautifulSoup):
        raise NotImplementedError

