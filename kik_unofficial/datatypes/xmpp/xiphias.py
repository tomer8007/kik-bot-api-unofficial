import base64
from builtins import NotImplementedError
from typing import List

from bs4 import BeautifulSoup
from google.protobuf import message

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse
from kik_unofficial.protobuf.entity.v1.entity_service_pb2 import GetUsersRequest, GetUsersResponse, GetUsersByAliasRequest, RequestedJid, \
    GetUsersByAliasResponse


class XiphiasRequest(XMPPElement):
    def __init__(self, method):
        super().__init__()
        self.method = method

    def get_protobuf_payload(self) -> message.Message:
        raise NotImplementedError

    def serialize(self):
        payload = self.get_protobuf_payload()
        protobuf_data = base64.b64encode(payload.SerializeToString()).decode()
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:iq:xiphias:bridge" service="mobile.entity.v1.Entity" method="{}">'
                '<body>{}</body>'
                '</query>'
                '</iq>').format(self.message_id, self.method, protobuf_data)
        return data.encode()


class UsersRequest(XiphiasRequest):
    def __init__(self, peer_jids):
        super().__init__('GetUsers')
        if isinstance(peer_jids, List):
            self.peer_jids = peer_jids
        else:
            self.peer_jids = [peer_jids]

    def get_protobuf_payload(self):
        request = GetUsersRequest()
        for peer_jid in self.peer_jids:
            jid = request.ids.add()
            jid.local_part = peer_jid.split('@')[0]
        return request


class UsersResponseUser:
    def __init__(self, user):
        if user.registration_element:
            self.creation_date_seconds = user.registration_element.creation_date.seconds
        if user.background_profile_pic_extension:
            self.background_pic_full_sized = user.background_profile_pic_extension.extension_detail.pic.full_sized_url
            self.background_pic_thumbnail = user.background_profile_pic_extension.extension_detail.pic.thumbnail_url
            self.background_pic_updated_seconds = \
                user.background_profile_pic_extension.extension_detail.pic.last_updated_timestamp.seconds
        if user.interests_element:
            self.interests = [element.localized_verbiage for element in user.interests_element.interests_element]


class UsersResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        text = base64.urlsafe_b64decode(data.query.body.text.encode())
        response = GetUsersResponse()
        response.ParseFromString(text)
        self.users = [UsersResponseUser(user) for user in response.users]


class UsersByAliasRequest(XiphiasRequest):
    def __init__(self, alias_jids):
        super().__init__('GetUsersByAlias')
        if isinstance(alias_jids, List):
            self.alias_jids = alias_jids
        else:
            self.alias_jids = [alias_jids]

    def get_protobuf_payload(self):
        request = GetUsersByAliasRequest()
        for peer_jid in self.alias_jids:
            jid = request.ids.add()  # type: RequestedJid
            jid.alias_jid.local_part = peer_jid.split('@')[0]
        return request


class UsersByAliasResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        text = base64.urlsafe_b64decode(data.query.body.text.encode())
        response = GetUsersByAliasResponse()
        response.ParseFromString(text)
        self.users = [UsersResponseUser(payload.public_group_member_profile) for payload in response.payloads]
