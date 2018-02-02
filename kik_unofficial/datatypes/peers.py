from bs4 import BeautifulSoup

from kik_unofficial.datatypes.exceptions import KikApiException


class Peer:
    def __init__(self, jid):
        self.jid = jid


class User(Peer):
    def __init__(self, data: BeautifulSoup):
        if 'jid' not in data.attrs:
            raise KikApiException("No jid in user xml {}".format(data))
        super().__init__(data['jid'])
        self.username = data.username.text if data.username else None
        self.display_name = data.find('display-name').text if data.find('display-name') else None
        self.pic = data.pic.text if data.pic else None
        self.verified = True if data.verified else False

    def __str__(self):
        return "{} ({})".format(self.display_name, self.username)

    def __repr__(self):
        return "User(jid={}, username={}, display_name={})".format(self.jid, self.username, self.display_name)


class Group(Peer):
    def __init__(self, data: BeautifulSoup):
        if 'jid' not in data.attrs:
            raise KikApiException("No jid in group xml")
        super().__init__(data['jid'])
        self.members = [GroupMember(m) for m in data.findAll('m')]
        self.code = data.code.text if data.code else None
        self.pic = data.pic.text if data.pic else None
        self.name = data.n.text if data.n else None
        self.is_public = 'is-public' in data and data['is-public'] == "true"

    def __repr__(self):
        return "Group(jid={}, name={}, code={}, members={})".format(self.jid, self.name, self.code, len(self.members))


class GroupMember(Peer):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data.text)
        self.is_admin = 'a' in data and data['a'] == '1'
        self.is_owner = 's' in data and data['s'] == '1'
