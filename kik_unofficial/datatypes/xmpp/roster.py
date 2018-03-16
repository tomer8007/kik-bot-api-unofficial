import base64
from typing import List, Union

from bs4 import BeautifulSoup
from kik_unofficial.datatypes.peers import Group, User
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse
from kik_unofficial.protobuf import group_search_service_pb2


class FetchRoasterRequest(XMPPElement):
    def __init__(self):
        super().__init__()

    def serialize(self) -> bytes:
        data = ('<iq type="get" id="{}">'
                '<query p="8" xmlns="jabber:iq:roster" />'
                '</iq>').format(self.message_id)
        return data.encode()


class FetchRosterResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.members = [self.parse_member(element) for element in iter(data.query)]

    @staticmethod
    def parse_member(element):
        if element.name == "g":
            return Group(element)
        elif element.name == "item":
            return User(element)


class FriendRequest(XMPPElement):
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


class PeerInfoResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        items = data.query.find_all('item')
        self.users = [User(item) for item in items]


class BatchPeerInfoRequest(XMPPElement):
    def __init__(self, peer_jids: Union[str, List[str]]):
        super().__init__()
        if isinstance(peer_jids, List):
            self.peer_jids = peer_jids
        else:
            self.peer_jids = [peer_jids]

    def serialize(self) -> bytes:
        items = ''.join(['<item jid="{}" />'.format(jid) for jid in self.peer_jids])
        data = ('<iq type="get" id="{}">'
                '<query xmlns="kik:iq:friend:batch">'
                '{}'
                '</query>'
                '</iq>').format(self.message_id, items)
        return data.encode()


class AddFriendRequest(XMPPElement):
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


class GroupSearchRequest(XMPPElement):
    def __init__(self, search_query):
        super().__init__()
        self.search_query = search_query

    def serialize(self):
        search_query = self.search_query
        if search_query.startswith("#"):
            search_query = search_query[1:]

        encoded_search_query = base64.b64encode(("\x0a" + chr(len(search_query)) + search_query).encode(), b"-_").decode()
        if encoded_search_query.endswith("="):
            encoded_search_query = encoded_search_query[:encoded_search_query.index("=")]

        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:iq:xiphias:bridge" service="mobile.groups.v1.GroupSearch" method="FindGroups">'
                '<body>{}</body></query></iq>').format(self.message_id, encoded_search_query)
        return data.encode()


class GroupSearchResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)

        encoded_results = base64.b64decode(data.find("body").text.encode(), b"-_")
        results = group_search_service_pb2.FindGroupsResponse()
        results.ParseFromString(encoded_results)
        self.groups = []  # type: List[self.GroupSearchEntry]
        for result in results.match:
            self.groups.append(self.GroupSearchEntry(result))

    class GroupSearchEntry:
        def __init__(self, result):
            self.jid = result.jid.local_part + "@groups.kik.com"
            self.hashtag = result.display_data.hashtag
            self.display_name = result.display_data.display_name
            self.picture_url = result.display_data.display_pic_base_url
            self.member_count = result.member_count
            self.group_join_token = result.group_join_token.token

        def __repr__(self):
            return "GroupSearchEntry(jid={}, hashtag={}, name={}, members={})".format(self.jid, self.hashtag, self.display_name, self.member_count)


class GroupJoinRequest(XMPPElement):
    def __init__(self, group_hashtag, join_token, group_jid):
        super().__init__()
        self.group_hashtag = group_hashtag
        self.join_token = join_token
        self.group_jid = group_jid

    def serialize(self) -> bytes:
        join_token = base64.b64encode(self.join_token, b"-_").decode()
        if join_token.endswith("="):
            join_token = join_token[:join_token.index("=")]
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:groups:admin">'
                '<g jid="{}" action="join">'
                '<code>{}</code>'
                '<token>{}</token>'
                '</g></query></iq>') \
            .format(self.message_id, self.group_jid, self.group_hashtag, join_token)
        return data.encode()
