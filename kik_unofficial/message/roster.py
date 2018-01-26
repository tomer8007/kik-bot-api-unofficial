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
        if element.name == "g":
            return Group(element)
        elif element.name == "item":
            return User(element)


class FriendMesssage(Message):
    def __init__(self, username):
        super().__init__()
        self.username = username

    def serialize(self) -> bytes:
        data = ('<iq type="get" id="{}">'
                '<query xmlns="kik:iq:friend">'
                '<item username="{}" />'
                '</query>'
                '</iq>').format(self.message_id, self.username)
        return data.encode()


class FriendMessageResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.user = User(data.query.item)


class BatchFriendMesssage(Message):
    def __init__(self, peer_jid):
        super().__init__()
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = ('<iq type="get" id="{}">'
                '<query xmlns="kik:iq:friend:batch">'
                '<item jid="{}" />'
                '</query>'
                '</iq>').format(self.message_id, self.peer_jid)
        return data.encode()


class AddFriendMessage(Message):
    def __init__(self, peer_jid):
        super().__init__()
        self.peer_jid = peer_jid

    def serialize(self):
        data = '<iq type="set" id="{}">' \
               '<query xmlns="kik:iq:friend">' \
               '<add jid="{}" />' \
               '</query>' \
               '</iq>'.format(self.message_id, self.peer_jid)
        return data.encode()
