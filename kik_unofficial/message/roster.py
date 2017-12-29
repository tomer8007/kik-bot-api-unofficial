from bs4 import BeautifulSoup

from kik_unofficial.message.message import Message, Response
from kik_unofficial.peer import Group, User


class RosterMessage(Message):
    def __init__(self):
        super().__init__()

    def serialize(self) -> bytes:
        data = ('<iq type="get" id="{}">'
                '<query p="8" xmlns="jabber:iq:roster" />'
                '</iq>').format(self.message_id)
        return data.encode()


class RosterResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.members = [self.parse_member(element) for element in iter(data.query)]

    @staticmethod
    def parse_member(element):
        if element.name == "m":
            return Group(element)
        elif element.name == "item":
            return User(element)
