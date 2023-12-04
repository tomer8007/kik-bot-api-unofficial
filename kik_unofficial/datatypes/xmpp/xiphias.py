import base64
from builtins import NotImplementedError
from typing import List, TypeVar, final

from bs4 import BeautifulSoup
from google.protobuf import message as proto_message

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse
from kik_unofficial.protobuf.entity.v1.entity_service_pb2 import \
    GetUsersRequest, GetUsersResponse, GetUsersByAliasRequest, RequestedJid, GetUsersByAliasResponse

from kik_unofficial.protobuf.groups.v1.group_search_service_pb2 import FindGroupsRequest, FindGroupsResponse
from kik_unofficial.utilities.parsing_utilities import ParsingUtilities

GROUP_SEARCH_SERVICE_NAME = 'mobile.groups.v1.GroupSearch'
ENTITY_SERVICE_NAME = 'mobile.entity.v1.Entity'

# Generic type for objects that extend google.protobuf.Message
T = TypeVar("T", bound=proto_message)


class XiphiasRequest(XMPPElement):
    def __init__(self, service: str, method: str):
        super().__init__()
        self.service = service
        self.method = method

    def get_protobuf_payload(self) -> T:
        raise NotImplementedError

    @final
    def serialize(self) -> bytes:
        payload = self.get_protobuf_payload()
        protobuf_data = base64.b64encode(payload.SerializeToString()).decode()
        data = (f'<iq type="set" id="{self.message_id}">'
                f'<query xmlns="kik:iq:xiphias:bridge" service="{self.service}" method="{self.method}">'
                f'<body>{protobuf_data}</body>'
                '</query>'
                '</iq>')
        return data.encode()


class XiphiasResponse(XMPPResponse):
    def __init__(self, data: BeautifulSoup, message: T):
        super().__init__(data)
        self.message = message
        message.ParseFromString(base64.urlsafe_b64decode(ParsingUtilities.fix_base64_padding(data.query.body.text)))


class UsersRequest(XiphiasRequest):
    def __init__(self, peer_jids):
        super().__init__(service=ENTITY_SERVICE_NAME, method='GetUsers')
        self.peer_jids = peer_jids if isinstance(peer_jids, List) else [peer_jids]

    def get_protobuf_payload(self) -> T:
        request = GetUsersRequest()
        for peer_jid in self.peer_jids:
            jid = request.ids.add()
            jid.local_part = peer_jid.split('@')[0]
        return request


class UsersResponseUser:
    """
    Normal jids (used with client.xiphias_get_users):
        Includes user data such as profile creation date and background picture URL.

    Alias jids provided in public groups (used with client.xiphias_get_users_by_alias):
        Includes all the private profile data (username, display_name, etc) of a user
        if you're chatting with them, else it'll get the local jid and the creation date.
    """
    username = None
    jid = None
    alias_jid = None
    display_name = None
    creation_date_seconds = None
    creation_date_nanos = None
    bio = None
    background_pic_full_sized = None
    background_pic_thumbnail = None
    background_pic_updated_seconds = None
    interests = None
    kin_user_id = None

    def __init__(self, user):
        if hasattr(user, 'private_profile'):
            self.username = user.private_profile.username.username
            if user.private_profile.id.local_part:
                # The attribute seems to exist with an empty string
                self.jid = f"{user.private_profile.id.local_part}@talk.kik.com"
        if user.id:
            if hasattr(user.id, 'local_part') and user.id.local_part:
                self.jid = f"{user.id.local_part}@talk.kik.com"
            if hasattr(user.id, 'alias_jid') and user.id.alias_jid.local_part:
                self.alias_jid = f"{user.id.alias_jid.local_part}@talk.kik.com"

        if hasattr(user, 'public_group_member_profile'):
            # The attrs below are found in the member's profile
            user = user.public_group_member_profile

        if user.registration_element:
            self.creation_date_seconds = user.registration_element.creation_date.seconds
            self.creation_date_nanos = user.registration_element.creation_date.nanos
        if hasattr(user, 'display_name'):
            self.display_name = user.display_name.display_name
        if hasattr(user, 'bio_element'):
            self.bio = user.bio_element.bio
        if hasattr(user, 'background_profile_pic_extension'):
            pic = user.background_profile_pic_extension.extension_detail.pic
            self.background_pic_full_sized = pic.full_sized_url
            self.background_pic_thumbnail = pic.thumbnail_url
            self.background_pic_updated_seconds = pic.last_updated_timestamp.seconds
        if hasattr(user, 'interests_element'):
            self.interests = [element.localized_verbiage for element in user.interests_element.interests_element]
        if hasattr(user, 'kin_user_id_element'):
            self.kin_user_id = user.kin_user_id_element.kin_user_id.id


class UsersResponse(XiphiasResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data, GetUsersResponse())
        self.users = [UsersResponseUser(user) for user in self.message.users]


class UsersByAliasRequest(XiphiasRequest):
    def __init__(self, alias_jids):
        super().__init__(service=ENTITY_SERVICE_NAME, method='GetUsersByAlias')
        self.alias_jids = alias_jids if isinstance(alias_jids, List) else [alias_jids]

    def get_protobuf_payload(self) -> T:
        request = GetUsersByAliasRequest()
        for peer_jid in self.alias_jids:
            jid = request.ids.add()  # type: RequestedJid
            jid.alias_jid.local_part = peer_jid.split('@')[0]
        return request


class UsersByAliasResponse(XiphiasResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data, GetUsersByAliasResponse())
        self.users = [UsersResponseUser(payload) for payload in self.message.payloads]


class GroupSearchRequest(XiphiasRequest):
    """
    Represents a request to search for groups by name
    """
    def __init__(self, query):
        super().__init__(service=GROUP_SEARCH_SERVICE_NAME, method='FindGroups')
        self.query = query.lstrip('#')

    def get_protobuf_payload(self) -> T:
        request = FindGroupsRequest()
        request.query = self.query
        return request


class GroupSearchResponse(XiphiasResponse):
    """
    Represents a response to a groups search, that was previously conducted using a query
    """
    def __init__(self, data: BeautifulSoup):
        super().__init__(data, message=FindGroupsResponse())
        self.groups = [self.GroupSearchEntry(result) for result in self.message.match]  # type: List[GroupSearchResponse.GroupSearchEntry]

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
