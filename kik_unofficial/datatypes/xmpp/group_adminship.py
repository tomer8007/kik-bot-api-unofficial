from typing import List, Union

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement


class AddToGroupRequest(XMPPElement):
    def __init__(self, group_jid: str, peer_jid: str):
        super().__init__()
        self.group_jid = group_jid
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:groups:admin">'
                f'<g jid="{self.group_jid}">'
                f'<m>{self.peer_jid}</m>'
                '</g>'
                '</query>'
                '</iq>')
        return data.encode()


class ChangeGroupNameRequest(XMPPElement):
    def __init__(self, group_jid: str, new_name: str):
        super().__init__()
        self.group_jid = group_jid
        self.new_name = new_name

    def serialize(self) -> bytes:
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:groups:admin">'
                f'<g jid="{self.group_jid}">'
                f'<n>{self.new_name}</n>'
                '</g>'
                '</query>'
                '</iq>')
        return data.encode()


class RemoveFromGroupRequest(XMPPElement):
    def __init__(self, group_jid: str, peer_jid: str):
        super().__init__()
        self.group_jid = group_jid
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:groups:admin">'
                f'<g jid="{self.group_jid}">'
                f'<m r="1">{self.peer_jid}</m>'
                '</g>'
                '</query>'
                '</iq>')
        return data.encode()


class UnbanRequest(XMPPElement):
    def __init__(self, group_jid: str, peer_jid: str):
        super().__init__()
        self.group_jid = group_jid
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:groups:admin">'
                f'<g jid="{self.group_jid}">'
                f'<b r="1">{self.peer_jid}</b>'
                '</g>'
                '</query>'
                '</iq>')

        return data.encode()


class BanMemberRequest(XMPPElement):
    def __init__(self, group_jid: str, peer_jid: str):
        super().__init__()
        self.group_jid = group_jid
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:groups:admin">'
                f'<g jid="{self.group_jid}">'
                f'<b>{self.peer_jid}</b>'
                '</g>'
                '</query>'
                '</iq>')
        return data.encode()


class LeaveGroupRequest(XMPPElement):
    def __init__(self, group_jid: str):
        super().__init__()
        self.group_jid = group_jid

    def serialize(self) -> bytes:
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:groups:admin">'
                f'<g jid="{self.group_jid}">'
                '<l />'
                '</g>'
                '</query>'
                '</iq>')
        return data.encode()


class PromoteToAdminRequest(XMPPElement):
    def __init__(self, group_jid: str, peer_jid: str):
        super().__init__()
        self.group_jid = group_jid
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:groups:admin">'
                f'<g jid="{self.group_jid}">'
                f'<m a="1">{self.peer_jid}</m>'
                '</g>'
                '</query>'
                '</iq>')
        return data.encode()


class DemoteAdminRequest(XMPPElement):
    def __init__(self, group_jid: str, peer_jid: str):
        super().__init__()
        self.group_jid = group_jid
        self.peer_jid = peer_jid

    def serialize(self) -> bytes:
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:groups:admin">'
                f'<g jid="{self.group_jid}">'
                f'<m a="0">{self.peer_jid}</m>'
                '</g>'
                '</query>'
                '</iq>')
        return data.encode()


class AddMembersRequest(XMPPElement):
    def __init__(self, group_jid: str, peer_jids: Union[str, List[str]]):
        super().__init__()
        self.group_jid = group_jid
        self.peer_jids = peer_jids if isinstance(peer_jids, List) else [peer_jids]

    def serialize(self) -> bytes:
        items = ''.join([f'<m>{jid}</m>' for jid in self.peer_jids])
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:groups:admin">'
                f'<g jid="{self.group_jid}">'
                f'{items}'
                '</g>'
                '</query>'
                '</iq>')
        return data.encode()


class ChangeDmDisabledRequest(XMPPElement):
    def __init__(self, group_jid: str, client_jid: str, is_dm_disabled: bool):
        super().__init__()
        self.group_jid = group_jid
        self.client_jid = client_jid
        self.is_dm_disabled = is_dm_disabled

    def serialize(self) -> bytes:
        data = (f'<iq type="set" id="{self.message_id}">'
                '<query xmlns="kik:groups:admin">'
                f'<g jid="{self.group_jid}">')

        is_dm_disabled_string = {'1' if self.is_dm_disabled else '0'}
        data += f'<m dmd="{is_dm_disabled_string}">{self.client_jid}/null</m>'
        '</g>'
        '</query>'
        '</iq>'
        return data.encode()
