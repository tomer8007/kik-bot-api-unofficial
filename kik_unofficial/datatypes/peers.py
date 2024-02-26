from __future__ import annotations
import base64
from typing import Union

from bs4 import BeautifulSoup

from kik_unofficial.utilities.parsing_utilities import ParsingUtilities, get_text_of_tag, is_tag_present
from kik_unofficial.datatypes.exceptions import KikApiException
from kik_unofficial.protobuf.entity.v1.entity_common_pb2 import EntityUser


class Peer:
    """
    a base class for representing a kik entity that has a JID (such as a user or a group)
    """

    def __init__(self, jid: str):
        self.jid = jid


class ProfilePic:
    def __init__(self, url: str, thumb_url: str, last_modified: int, is_background: bool):
        self.url = url
        self.thumb_url = thumb_url
        self.last_modified = last_modified
        self.is_background = is_background

    def cache_bust_url(self, full_size: bool = True) -> str:
        """
        Returns a cache busted url (contains the request_ts parameter)
        """
        url = self.url if full_size else self.thumb_url
        return url + "?request_ts=" + str(self.last_modified)

    def get_pic_id(self) -> str:
        """
        Returns the ID of the picture.

        Given URL http://profilepics.cf.kik.com/0WdUM1_QkB2n6BSSF6r-c4_jqi8/orig.jpg,
        the ID is 0WdUM1_QkB2n6BSSF6r-c4_jqi8
        """
        return self.url.split(sep="/", maxsplit=4)[3]

    def __str__(self):
        return f"URL: {self.cache_bust_url()}"

    def __repr__(self):
        return f"ProfilePic(url={self.url}, last_modified={self.last_modified}, is_background={self.is_background})"

    @staticmethod
    def parse(data: BeautifulSoup) -> Union[ProfilePic, None]:
        pic = data.find("pic", recursive=False)
        if pic is None:
            return None

        pic_url = pic.text
        if pic_url.startswith("http://"):
            pic_url = "https://" + pic_url[7:]

        orig_url = pic_url + "/orig.jpg"
        thumb_url = pic_url + "/thumb.jpg"

        return ProfilePic(orig_url, thumb_url, int(pic["ts"]), False) if pic else None


class User(Peer):
    """
    Represents a user (person) in kik messenger.
    Every user has a username, display name, etc.
    """

    def __init__(self, data: BeautifulSoup):
        if "jid" not in data.attrs:
            raise KikApiException(f"No jid in user xml {data}")
        super().__init__(data["jid"])
        self.username = get_text_of_tag(data, "username")
        self.display_name = get_text_of_tag(data, "display-name")
        self.verified = is_tag_present(data, "verified")
        if data.entity:
            self._parse_entity(data.entity.text)

        self.profile_pic = ProfilePic.parse(data)

        # Deprecated field kept for backwards compatibility.
        # Callers should migrate to self.profile_pic
        self.pic = self.profile_pic.url if self.profile_pic else None

        # Known user types: "TEST", "RAGEBOT"
        # Normal users will have a type of None
        self.user_type = get_text_of_tag(data, "user-type")

    def _parse_entity(self, entity):
        decoded_entity = base64.urlsafe_b64decode(ParsingUtilities.fix_base64_padding(entity))
        user = EntityUser()
        user.ParseFromString(decoded_entity)
        if user.registration_element:
            self.creation_date_seconds = user.registration_element.creation_date.seconds
        if user.background_profile_pic_extension:
            self.background_pic_full_sized = user.background_profile_pic_extension.extension_detail.pic.full_sized_url
            self.background_pic_thumbnail = user.background_profile_pic_extension.extension_detail.pic.thumbnail_url
            self.background_pic_updated_seconds = user.background_profile_pic_extension.extension_detail.pic.last_updated_timestamp.seconds
        if user.interests_element:
            self.interests = [element.localized_verbiage for element in user.interests_element.interests_element]

    def __str__(self):
        return f"{self.display_name} ({self.username})"

    def __repr__(self):
        return f"User(jid={self.jid}, username={self.username}, display_name={self.display_name})"


class RosterUser(User):
    """
    Represents a user roster entry.
    """

    def __init__(self, data: BeautifulSoup):
        """
        Represents a user (person) in Kik, as received from the roster.
        Includes the same fields as User but includes is_blocked.
        """
        super().__init__(data)
        self.is_blocked = is_tag_present(data, "blocked")  # True if the authenticated user has this user blocked

    def __str__(self):
        return f"{self.display_name} ({self.username}){' (blocked)' if self.is_blocked else ''}"

    def __repr__(self):
        return f"RosterUser(jid={self.jid}, username={self.username}, display_name={self.display_name}, is_blocked={self.is_blocked})"


class Group(Peer):
    """
    Represents a group of kik users.
    Each group has its members, public code (such as #Music), name, etc.
    """

    def __init__(self, data: BeautifulSoup):
        if "jid" not in data.attrs:
            raise KikApiException("No jid in group xml")
        super().__init__(data["jid"])
        self.members = [GroupMember(m) for m in data.find_all("c", recursive=False)]  # creators of the group (used when a user initially creates a group)
        self.members += [GroupMember(m) for m in data.find_all("m", recursive=False)]  # members in the group
        self.banned_members = [GroupMember(m) for m in data.find_all("b", recursive=False)]  # banned member jids
        self.removed_members = [
            GroupMember(m) for m in data.find_all("l", recursive=False)
        ]  # jids of members that left (used for 'has left the chat' status message events)
        self.code = get_text_of_tag(data, "code")
        self.name = get_text_of_tag(data, "n")
        self.is_public = data.get("is-public") == "true"
        self.profile_pic = ProfilePic.parse(data)

        # Deprecated field kept for backwards compatibility.
        # Callers should migrate to self.profile_pic
        self.pic = self.profile_pic.url if self.profile_pic else None

    def __repr__(self):
        return f"Group(jid={self.jid}, name={self.name}, code={self.code}, members={len(self.members)})"


class GroupMember(Peer):
    """
    Represents a user who is a member of a group.
    Members may also admin or own the group
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data.text)
        # This is only true when sent as part of a server message when a user creates a group
        self.is_creator = data.name == "c"

        self.is_admin = self.is_creator or data.get("a") == "1"  # Group creator is always an admin
        self.is_owner = self.is_creator or data.get("s") == "1"  # Group creator is always an owner
        self.is_dm_disabled = data.get("dmd") == "1"
