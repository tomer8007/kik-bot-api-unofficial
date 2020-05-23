import base64

from bs4 import BeautifulSoup

from kik_unofficial.utilities.parsing_utilities import ParsingUtilities
from kik_unofficial.datatypes.exceptions import KikApiException
from kik_unofficial.protobuf.entity.v1.entity_common_pb2 import EntityUser


class Peer:
    """
    a base class for representing a kik entity that has a JID (such as a user or a group)
    """
    def __init__(self, jid):
        self.jid = jid


class User(Peer):
    """"
    Represents a user (person) in kik messenger.
    Every user has a username, display name, etc.
    """
    def __init__(self, xml_data: BeautifulSoup):
        if 'jid' not in xml_data.attrs:
            raise KikApiException("No jid in user xml {}".format(xml_data))
        super().__init__(xml_data['jid'])
        self.username = xml_data.username.text if xml_data.username else None
        self.display_name = xml_data.find('display-name').text if xml_data.find('display-name') else None
        self.pic = xml_data.pic.text if xml_data.pic else None
        self.verified = True if xml_data.verified else False
        if xml_data.entity:
            self._parse_entity(xml_data.entity.text)

    def _parse_entity(self, entity):
        decoded_entity = base64.urlsafe_b64decode(ParsingUtilities.fix_base64_padding(entity))
        user = EntityUser()
        user.ParseFromString(decoded_entity)
        if user.registration_element:
            self.creation_date_seconds = user.registration_element.creation_date.seconds
        if user.background_profile_pic_extension:
            self.background_pic_full_sized = user.background_profile_pic_extension.extension_detail.pic.full_sized_url
            self.background_pic_thumbnail = user.background_profile_pic_extension.extension_detail.pic.thumbnail_url
            self.background_pic_updated_seconds = \
                user.background_profile_pic_extension.extension_detail.pic.last_updated_timestamp.seconds
        if user.interests_element:
            self.interests = [element.localized_verbiage for element in user.interests_element.interests_element]

    def __str__(self):
        return "{} ({})".format(self.display_name, self.username)

    def __repr__(self):
        return "User(jid={}, username={}, display_name={})".format(self.jid, self.username, self.display_name)


class Group(Peer):
    """
    Represents a group of kik users.
    Each group has its members, public code (such as #Music), name, etc.
    """
    def __init__(self, xml_data: BeautifulSoup):
        if 'jid' not in xml_data.attrs:
            raise KikApiException("No jid in group xml")
        super().__init__(xml_data['jid'])
        self.members = [GroupMember(m) for m in xml_data.findAll('m')]
        self.code = xml_data.code.text if xml_data.code else None
        self.pic = xml_data.pic.text if xml_data.pic else None
        self.name = xml_data.n.text if xml_data.n else None
        self.is_public = xml_data.get('is-public') == "true"

    def __repr__(self):
        return "Group(jid={}, name={}, code={}, members={})".format(self.jid, self.name, self.code, len(self.members))


class GroupMember(Peer):
    """
    Represents a user who is a member of a group.
    Members may also admin or own the group
    """
    def __init__(self, xml_data: BeautifulSoup):
        super().__init__(xml_data.text)
        self.is_admin = xml_data.get('a') == '1'
        self.is_owner = xml_data.get('s') == '1'
