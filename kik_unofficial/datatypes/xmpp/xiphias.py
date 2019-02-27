import base64
from typing import List

from bs4 import BeautifulSoup

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse
from kik_unofficial.protobuf.entity.v1.entity_service_pb2 import GetUsersRequest, GetUsersResponse
from kik_unofficial.utilities.parsing_utilities import ParsingUtilities


class UsersRequest(XMPPElement):
    def __init__(self, peer_jids):
        super().__init__()
        if isinstance(peer_jids, List):
            self.peer_jids = peer_jids
        else:
            self.peer_jids = [peer_jids]

    def serialize(self):
        request = GetUsersRequest()
        for peer_jid in self.peer_jids:
            jid = request.ids.add()
            jid.local_part = peer_jid.split('@')[0]

        protobuf_data = base64.b64encode(request.SerializeToString()).decode()
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:iq:xiphias:bridge" service="mobile.entity.v1.Entity" method="GetUsers">'
                '<body>{}</body>'
                '</query>'
                '</iq>').format(self.message_id, protobuf_data)
        return data.encode()


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
        text = ParsingUtilities.decode_base64(data.query.body.text.encode())
        response = GetUsersResponse()
        response.ParseFromString(text)
        self.users = [UsersResponseUser(user) for user in response.users]
