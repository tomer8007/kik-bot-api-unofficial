from typing import List, Union

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement


class AddToGroupRequest(XMPPElement):
    def __init__(self, group_jid, peer_jid):
        super().__init__()
        self.group_jid = group_jid
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:groups:admin">'
                '<g jid="{}">'
                '<m>{}</m>'
                '</g>'
                '</query>'
                '</iq>').format(self.message_id, self.group_jid, self.peer_jid)
        return data.encode()

class ChangeGroupNameRequest(XMPPElement):
    def __init__(self, group_jid, new_name):
        super().__init__()
        self.group_jid = group_jid
        self.new_name = new_name

    def serialize(self) -> bytes:
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:groups:admin">'
                '<g jid="{}">'
                '<n>{}</n>'
                '</g>'
                '</query>'
                '</iq>').format(self.message_id, self.group_jid, self.new_name)
        return data.encode()

class RemoveFromGroupRequest(XMPPElement):
    def __init__(self, group_jid, peer_jid):
        super().__init__()
        self.group_jid = group_jid
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:groups:admin">'
                '<g jid="{}">'
                '<m r="1">{}</m>'
                '</g>'
                '</query>'
                '</iq>').format(self.message_id, self.group_jid, self.peer_jid)
        return data.encode()


class UnbanRequest(XMPPElement):
    def __init__(self, group_jid, peer_jid):
        super().__init__()
        self.group_jid = group_jid
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:groups:admin">'
                '<g jid="{}">'
                '<b r="1">{}</b>'
                '</g>'
                '</query>'
                '</iq>').format(self.message_id, self.group_jid, self.peer_jid)
        return data.encode()


class BanMemberRequest(XMPPElement):
    def __init__(self, group_jid, peer_jid):
        super().__init__()
        self.group_jid = group_jid
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:groups:admin">'
                '<g jid="{}">'
                '<b>{}</b>'
                '</g>'
                '</query>'
                '</iq>').format(self.message_id, self.group_jid, self.peer_jid)
        return data.encode()


class LeaveGroupRequest(XMPPElement):
    def __init__(self, group_jid):
        super().__init__()
        self.group_jid = group_jid

    def serialize(self) -> bytes:
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:groups:admin">'
                '<g jid="{}">'
                '<l />'
                '</g>'
                '</query>'
                '</iq>').format(self.message_id, self.group_jid)
        return data.encode()


class PromoteToAdminRequest(XMPPElement):
    def __init__(self, group_jid, peer_jid):
        super().__init__()
        self.group_jid = group_jid
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:groups:admin">'
                '<g jid="{}">'
                '<m a="1">{}</m>'
                '</g>'
                '</query>'
                '</iq>').format(self.message_id, self.group_jid, self.peer_jid)
        return data.encode()


class DemoteAdminRequest(XMPPElement):
    def __init__(self, group_jid, peer_jid):
        super().__init__()
        self.group_jid = group_jid
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:groups:admin">'
                '<g jid="{}">'
                '<m a="0">{}</m>'
                '</g>'
                '</query>'
                '</iq>').format(self.message_id, self.group_jid, self.peer_jid)
        return data.encode()


class AddMembersRequest(XMPPElement):
    def __init__(self, group_jid, peer_jids: Union[str, List[str]]):
        super().__init__()
        self.group_jid = group_jid
        if isinstance(peer_jids, List):
            self.peer_jids = peer_jids
        else:
            self.peer_jids = [peer_jids]

    def serialize(self) -> bytes:
        items = ''.join(['<m>{}</m>'.format(jid) for jid in self.peer_jids])
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:groups:admin">'
                '<g jid="{}">'
                '{}'
                '</g>'
                '</query>'
                '</iq>').format(self.message_id, self.group_jid, items)
        return data.encode()
