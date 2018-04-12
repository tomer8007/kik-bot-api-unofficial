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
