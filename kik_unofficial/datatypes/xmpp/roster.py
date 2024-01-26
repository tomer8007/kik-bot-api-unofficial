from __future__ import annotations

import base64
from typing import List, Union
from lxml import etree

from bs4 import BeautifulSoup
from lxml.etree import Element

from kik_unofficial.datatypes.peers import Group, User, Peer, RosterUser
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse
from kik_unofficial.device_configuration import kik_version_info
from kik_unofficial.utilities import jid_utilities
from kik_unofficial.utilities.parsing_utilities import get_optional_attribute


class FetchRosterRequest(XMPPElement):
    """
    Represents a request to get the chat partners list (the roster)

    :param is_batched: pass in True if the last successful roster request had `FetchRosterResponse.more == True`
    :param timestamp: pass in the roster timestamp from the last successful roster request. `FetchRosterResponse.timestamp`
    :param mts: pass in the roster mts from the last successful roster request. `FetchRosterResponse.mts`
    """

    def __init__(self, is_batched: bool, timestamp: Union[str, None] = None, mts: Union[str, None] = None):
        super().__init__()
        self.timestamp = timestamp
        self.mts = mts
        self.is_batched = is_batched

    def serialize(self) -> Element:
        iq = etree.Element("iq")
        iq.set("type", "get")
        iq.set("id", self.message_id)

        query = etree.SubElement(iq, "query")

        v9 = self._needs_v9_protocol()
        query.set("p", "9" if v9 else "8")

        if self.timestamp:
            query.set("ts", self.timestamp)
        if self.mts and v9:
            query.set("mts", self.mts)
        if self.is_batched:
            query.set("b", "1")

        query.set("xmlns", "jabber:iq:roster")
        return iq

    @staticmethod
    def _needs_v9_protocol():
        version_number = int(kik_version_info["kik_version"].replace(".", ""))
        # 15.56.0.28947 is the first version where the protocol was changed to 9 (mts)
        return version_number >= 15_56_0_28947


class FetchRosterResponse(XMPPResponse):
    """
    Represents the response to a 'get roster' request which contains the peers list
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.peers: list[Peer] = []
        self.removed_users: list[str] = []
        self.removed_groups: list[str] = []
        self.more = data.query.get("more") == "1"
        self.timestamp = data.query.get("ts")
        self.mts = data.query.get("mts")
        self.is_roster_full = False

        for element in iter(data.query):
            self.parse_peer(element)

    def parse_peer(self, element):
        name = element.name

        if name == "item":
            # 'item' contains new or updated user accounts in the roster.
            self.peers.append(RosterUser(element))
        elif name == "g":
            # 'g' contains new or updated groups in the roster.
            self.peers.append(Group(element))
        elif name == "remove":
            # 'remove' indicates that the user JID is no longer in the callers roster.
            self.removed_users.append(element["jid"])
        elif name == "remove-group":
            # 'remove-group' indicates that the group JID is no longer in the callers roster.
            self.removed_groups.append(element["jid"])
        elif name == "roster" and get_optional_attribute(element, "full") == "1":
            # If encountered, Kik is indicating that a full refresh is needed.
            # Client should delete the 'ts' and 'mts' page tokens from its cache / storage,
            # and request roster after 30-60 seconds without any page tokens specified.
            self.is_roster_full = True


class PeersInfoRequest(XMPPElement):
    """
    Represents a request to get basic information (display name, JID, etc.) of 1-50 user JIDs
    """

    def __init__(self, peer_jids: Union[str, List[str]]):
        super().__init__()
        self.peer_jids = peer_jids if isinstance(peer_jids, List) else [peer_jids]
        if len(self.peer_jids) == 0:
            raise ValueError("Can't request an empty list of peer_jids")
        if len(self.peer_jids) > 50:
            raise ValueError(f"Can't request more than 50 peer_jids at a time, got {len(self.peer_jids)}")

    def serialize(self) -> bytes:
        items = ""
        for jid in self.peer_jids:
            if jid_utilities.is_pm_jid(jid) or jid_utilities.is_alias_jid(jid):
                items += f'<item jid="{jid}" />'
            else:
                raise ValueError(f"Invalid JID {jid}, must be a valid user JID")

        data = f'<iq type="get" id="{self.message_id}">' f'<query xmlns="kik:iq:friend:batch">{items}</query>' "</iq>"

        return data.encode()


class PeersInfoResponse(XMPPResponse):
    """
    Represents the response to a peers query request, which contains the basic information of the peers
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.users = []  # type: list[User]
        self.failed_user_jids = []  # type: list[str]


class FriendBatchResponse(PeersInfoResponse):
    """
    Represents the response to a peers query request, which contains the basic information of the peers
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        success = data.query.success
        if success:
            items = success.find_all("item", recursive=False)
            self.users = [User(item) for item in items]

        failed = data.query.failed
        if failed:
            items = failed.find_all("item", recursive=False)
            self.failed_user_jids = [item["jid"] for item in items]


class QueryUserByUsernameRequest(XMPPElement):
    """
    Represents a request to get basic information (display name, JID, etc.) of one username

    Only one username can be retrieved per request.
    """

    def __init__(self, username: str):
        super().__init__()
        self.username = username

    def serialize(self) -> bytes:
        data = f'<iq type="get" id="{self.message_id}">' f'<query xmlns="kik:iq:friend">' f'<item username="{self.username}" />' "</query>" "</iq>"
        return data.encode()


class QueryUserByUsernameResponse(PeersInfoResponse):
    """
    Represents the response to a username query request, which contains the basic information of the peer
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.users = [User(data.query.item)]


class AddFriendRequest(XMPPElement):
    """
    Represents a request to add some user (peer) as a friend
    """

    def __init__(self, peer_jid):
        super().__init__()
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = f'<iq type="set" id="{self.message_id}">' '<query xmlns="kik:iq:friend">' f'<add jid="{self.peer_jid}" />' "</query>" "</iq>"
        return data.encode()


class RemoveFriendRequest(XMPPElement):
    """
    Represents a request to remove some user (peer) as a friend
    """

    def __init__(self, peer_jid):
        super().__init__()
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = f'<iq type="set" id="{self.message_id}">' '<query xmlns="kik:iq:friend">' f'<remove jid="{self.peer_jid}" />' "</query>" "</iq>"
        return data.encode()


class BlockUserRequest(XMPPElement):
    """
    Represents a request to block a user.
    """

    def __init__(self, peer_jid):
        super().__init__()
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = f'<iq type="set" id="{self.message_id}">' '<query xmlns="kik:iq:friend">' f'<block jid="{self.peer_jid}" />' "</query>" "</iq>"
        return data.encode()


class UnblockUserRequest(XMPPElement):
    """
    Represents a request to unblock a user.
    """

    def __init__(self, peer_jid):
        super().__init__()
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = f'<iq type="set" id="{self.message_id}">' '<query xmlns="kik:iq:friend">' f'<unblock jid="{self.peer_jid}" />' "</query>" "</iq>"
        return data.encode()


class GetMutedUsersRequest(XMPPElement):
    """
    Represents a request to mute a user.
    """

    def __init__(self):
        super().__init__()

    def serialize(self) -> bytes:
        data = f'<iq type="get" id="{self.message_id}"><query xmlns="kik:iq:convos" /></iq>'
        return data.encode()


class MuteUserRequest(XMPPElement):
    """
    Represents a request to mute a user.
    """

    def __init__(self, peer_jid, expires: Union[float, int, None] = None):
        super().__init__()
        self.peer_jid = peer_jid
        self.expires = expires

    def serialize(self) -> bytes:
        mute_tag = f'<mute expires="{int(round(self.expires * 1000))}" />' if self.expires else "<mute />"

        data = (
            f'<iq type="set" id="{self.message_id}">'
            '<query xmlns="kik:iq:convos">'
            f'<convo jid="{self.peer_jid}">'
            f"{mute_tag}"
            "</convo>"
            "</query>"
            "</iq>"
        )
        return data.encode()


class UnmuteUserRequest(XMPPElement):
    """
    Represents a request to unmute a user.
    """

    def __init__(self, peer_jid):
        super().__init__()
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = f'<iq type="set" id="{self.message_id}">' '<query xmlns="kik:iq:convos">' f'<convo jid="{self.peer_jid}"><unmute /></convo>' "</query>" "</iq>"
        return data.encode()


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
        join_token = base64.urlsafe_b64encode(self.join_token).decode("utf-8").rstrip("=")
        data = (
            f'<iq type="set" id="{self.message_id}">'
            '<query xmlns="kik:groups:admin">'
            f'<g jid="{self.group_jid}" action="join">'
            f"<code>{self.group_hashtag}</code>"
            f"<token>{join_token}</token>"
            "</g></query></iq>"
        )
        return data.encode()
