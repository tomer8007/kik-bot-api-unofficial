import base64
from typing import List, Union

from bs4 import BeautifulSoup
from kik_unofficial.datatypes.peers import Group, User
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse
from kik_unofficial.protobuf.groups.v1 import group_search_service_pb2
from kik_unofficial.datatypes.exceptions import KikParsingException


class FetchRosterRequest(XMPPElement):
    """
    Represents a request to get the chat partners list (the roster)
    """

    def __init__(self, is_big=True, timestamp=None):
        super().__init__()
        self.timestamp = timestamp
        self.is_big = is_big

    def serialize(self) -> bytes:
        ts = f' ts="{self.timestamp}" ' if self.timestamp else ' '
        data = (
            f'<iq type="get" id="{self.message_id}">'
            f'<query p="8"{ts}b="{int(self.is_big)}" xmlns="jabber:iq:roster" />'
            '</iq>'
        )
        return data.encode()


class FetchRosterResponse(XMPPResponse):
    """
    Represents the response to a 'get roster' request which contains the peers list
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.peers = [self.parse_peer(element) for element in iter(data.query)]
        self.more = data.query.get('more')
        self.timestamp = data.query.get('ts')

    @staticmethod
    def parse_peer(element):
        if element.name in ('g', "remove-group"):
            return Group(element)
        elif element.name in ('item', "remove"):
            # remove deletes accounts / accounts no longer in the roster
            return User(element)
        else:
            raise KikParsingException(f"Unsupported peer element tag: {element.name}")


class QueryUsersInfoRequest(XMPPElement):
    """
    Represents a request to get basic information (display name, JID, etc.) of one or more users
    """

    def __init__(self, peer_jids: Union[str, List[str]]):
        super().__init__()
        self.peer_jids = peer_jids if isinstance(peer_jids, List) else [peer_jids]

    def serialize(self) -> bytes:
        items = []
        for jid in self.peer_jids:
            if "@" in jid:
                items.append(f'<item jid="{jid}" />')
            else:
                # this is in fact not a JID, but a username
                items.append(f'<item username="{jid}" />')

        xmlns = 'kik:iq:friend:batch' if len(items) > 1 else "kik:iq:friend"

        data = (f'<iq type="get" id="{self.message_id}">'
                f'<query xmlns="{xmlns}">'
                f'{"".join(items)}'
                '</query>'
                '</iq>')

        return data.encode()


class PeersInfoResponse(XMPPResponse):
    """
    Represents the response to a peers query request, which contains the basic information of the peers
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        items = data.query.find_all('item')
        self.users = [User(item) for item in items]


class AddFriendRequest(XMPPElement):
    """
    Represents a request to add some user (peer) as a friend
    """

    def __init__(self, peer_jid):
        super().__init__()
        self.peer_jid = peer_jid

    def serialize(self):
        data = f'<iq type="set" id="{self.message_id}">' \
               '<query xmlns="kik:iq:friend">' \
               f'<add jid="{self.peer_jid}" />' \
               '</query>' \
               '</iq>'
        return data.encode()


class RemoveFriendRequest(XMPPElement):
    """
    Represents a request to remove some user (peer) as a friend
    """

    def __init__(self, peer_jid):
        super().__init__()
        self.peer_jid = peer_jid

    def serialize(self):
        data = (
            f'<iq type="set" id="{self.message_id}">'
            '<query xmlns="kik:iq:friend">'
            f'<remove jid="{self.peer_jid}" />'
            '</query>'
            '</iq>'
        )
        return data.encode()


class GroupSearchRequest(XMPPElement):
    """
    Represents a request to search for groups by name
    """

    def __init__(self, search_query):
        super().__init__()
        self.search_query = search_query

    def serialize(self):
        search_query = self.search_query
        if search_query.startswith("#"):
            search_query = search_query[1:]

        encoded_search_query = base64.b64encode(("\x0a" + chr(len(search_query)) + search_query).encode(),
                                                b"-_").decode()
        if encoded_search_query.endswith("="):
            encoded_search_query = encoded_search_query[:encoded_search_query.index("=")]

        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:iq:xiphias:bridge" service="mobile.groups.v1.GroupSearch" method="FindGroups">'
                f'<body>{encoded_search_query}</body></query></iq>')
        return data.encode()


class GroupSearchResponse(XMPPResponse):
    """
    Represents a response to a groups search, that was previously conducted using a query
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)

        encoded_results = base64.b64decode(data.find("body").text.encode(), b"-_")
        results = group_search_service_pb2.FindGroupsResponse()
        results.ParseFromString(encoded_results)
        self.groups = []  # type: List[self.GroupSearchEntry]
        self.groups.extend(self.GroupSearchEntry(result) for result in results.match)

    class GroupSearchEntry:
        """
        Represents a group entry that was found in the search results
        """

        def __init__(self, result):
            self.jid = f"{result.jid.local_part}@groups.kik.com"
            self.hashtag = result.display_data.hashtag
            self.display_name = result.display_data.display_name
            self.picture_url = result.display_data.display_pic_base_url
            self.member_count = result.member_count
            self.group_join_token = result.group_join_token.token

        def __repr__(self):
            return f"GroupSearchEntry(jid={self.jid}, hashtag={self.hashtag}, name={self.display_name}, members={self.member_count})"


class GroupJoinRequest(XMPPElement):
    """
    Represents a request to join a specific group
    In order to join a group a special token is needed that is obtained from the search results
    """

    def __init__(self, group_hashtag, join_token, group_jid):
        super().__init__()
        self.group_hashtag = group_hashtag
        self.join_token = join_token
        self.group_jid = group_jid

    def serialize(self) -> bytes:
        join_token = base64.b64encode(self.join_token, b"-_").decode()
        if join_token.endswith("="):
            join_token = join_token[:join_token.index("=")]
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:groups:admin">'
                f'<g jid="{self.group_jid}" action="join">'
                f'<code>{self.group_hashtag}</code>'
                f'<token>{join_token}</token>'
                '</g></query></iq>')
        return data.encode()
