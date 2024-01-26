from __future__ import annotations

import asyncio
import io
import pathlib
import ssl
import time
import traceback
from threading import Thread, Event
from typing import Union, List
from asyncio import StreamReader, StreamWriter
from bs4 import BeautifulSoup

import kik_unofficial.callbacks as callbacks
import kik_unofficial.datatypes.xmpp.chatting as chatting
import kik_unofficial.datatypes.xmpp.group_adminship as group_adminship
import kik_unofficial.datatypes.xmpp.login as login
import kik_unofficial.datatypes.xmpp.roster as roster
import kik_unofficial.datatypes.xmpp.history as history
import kik_unofficial.datatypes.xmpp.sign_up as sign_up
import kik_unofficial.xmlns_handlers as xmlns_handlers
from kik_unofficial.datatypes.xmpp.auth_stanza import AuthStanza
from kik_unofficial.datatypes.xmpp import account, xiphias
from kik_unofficial.parser.parser import KikXmlParser
from kik_unofficial.utilities import xml_utilities, jid_utilities
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils
from kik_unofficial.utilities.kik_server_clock import KikServerClock
from kik_unofficial.utilities.threading_utils import run_in_new_thread
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement, XMPPResponse
from kik_unofficial.http_requests import profile_pictures, content
from kik_unofficial.utilities.credential_utilities import random_device_id, random_android_id
from kik_unofficial.utilities.logging_utils import set_up_basic_logging

HOST, PORT = CryptographicUtils.get_kik_host_name(), 5223


class KikClient:
    """
    The main kik class with which you're managing a kik connection and sending commands
    """

    def __init__(
        self,
        callback: callbacks.KikClientCallback,
        kik_username: str,
        kik_password: str,
        kik_node: str = None,
        device_id: str = None,
        android_id: str = random_android_id(),
        log_level: int = 20,
        enable_console_logging: bool = False,
        log_file_path: str = None,
        disable_auth_cert: bool = True,
    ) -> None:
        """
        Initializes a connection to Kik servers.
        If you want to automatically login too, use the username and password parameters.

        :param callback: a callback instance containing your callbacks implementation.
                         This way you'll get notified whenever certain event happen.
                         Look at the KikClientCallback class for more details
        :param kik_username: the kik username or email to log in with.
        :param kik_password: the kik password to log in with.
        :param kik_node: the username plus 3 letters after the "_" and before the "@" in the JID. If you know it,
                         authentication will happen faster and without a login. otherwise supply None.
        :param device_id: a unique device ID. If you don't supply one, a random one will be generated. (generated at _on_connection_made)
        :param android_id: a unique android ID. If you don't supply one, a random one will be generated.
        :param enable_console_logging: If true, turns on logging to stdout (default: False)
        :param log_file_path: If set will create a daily rotated log file and archive for 7 days.
        :param disable_auth_cert: If true, auth certs will not be generated on every connection.
            This greatly improves startup time.
            True by default.
        """
        # turn on logging with basic configuration
        self.log = set_up_basic_logging(
            log_level=log_level, logger_name="kik_unofficial", log_file_path=log_file_path, enable_console_output=enable_console_logging
        )

        self.username = kik_username
        self.password = kik_password
        self.kik_node = kik_node
        self.kik_email = None
        self.device_id = device_id
        self.android_id = android_id

        self.callback = callback
        self.callback._on_client_init(self)
        self.authenticator = AuthStanza(self)

        self.connected = False
        self.authenticated = False
        self.connection = None
        self.is_permanent_disconnection = False
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self._known_users_information = set()
        self._new_user_added_event = Event()

        self.should_login_on_connection = kik_username is not None and kik_password is not None
        self.disable_auth_cert = disable_auth_cert
        self._last_ping_sent_time = 0
        self._connect()

    def _connect(self):
        """
        Runs the kik connection thread, which creates an encrypted (SSL based) TCP connection
        to the kik servers.
        """
        if self.is_permanent_disconnection:
            self.log.debug("Permanent disconnection, ignoring connect attempt")
            return
        self.kik_connection_thread = Thread(target=self._kik_connection_thread_function, name="Kik Connection")
        self.kik_connection_thread.start()

    def wait_for_messages(self, max_retries: int = 5):
        for _ in range(max_retries):
            self.kik_connection_thread.join()
            if self.is_permanent_disconnection:
                self.log.info("Permanent disconnect, exiting...")
                break
            self.log.info("Connection has disconnected, trying again...")
            time.sleep(2)

    def _on_connection_made(self):
        """
        Gets called when the TCP connection to kik's servers is done and we are connected.
        Now we might initiate a login request or an auth request.
        """
        if self.username and self.password and self.kik_node and self.device_id:
            # we have all required credentials, we can authenticate
            self.log.info(
                f"Establishing authenticated connection using kik node '{self.kik_node}', device id '{self.device_id}' and android id '{self.android_id}'..."
            )

            message = login.EstablishAuthenticatedSessionRequest(self.kik_node, self.username, self.password, self.device_id)
        else:
            # if device id is not set, we generate a random one
            self.device_id = self.device_id or random_device_id()
            message = login.MakeAnonymousStreamInitTag(self.device_id, n=1)
        self.initial_connection_payload = message.serialize()
        self.connection.send_raw_data(self.initial_connection_payload)

    def _establish_authenticated_session(self, kik_node):
        """
        Updates the kik node and creates a new connection to kik servers.
        This new connection will be initiated with another payload which proves
        we have the credentials for a specific user. This is how authentication is done.

        :param kik_node: The user's kik node (everything before '@' in JID).
        """
        self.kik_node = kik_node
        self.log.info("Closing current connection and creating a new authenticated one.")

        self.disconnect(permanent=False)

    def login(self, username: str, password: str, captcha_result: str = None):
        """
        Sends a login request with the given kik username and password

        :param username: Your kik username or email
        :param password: Your kik password
        :param captcha_result: If this parameter is provided, it is the answer to the captcha given in the previous
        login attempt.
        """
        self.username = username
        self.password = password
        login_request = login.LoginRequest(username, password, captcha_result, self.device_id, self.android_id)
        login_type = "email" if "@" in self.username else "username"
        self.log.info(f"Logging in with {login_type} '{username}' and a given password {'*' * len(password)}...")
        return self._send_xmpp_element(login_request)

    def register(self, email: str, username: str, password: str, first_name: str, last_name: str, birthday: str, captcha_result: str = None):
        """
        Sends a register request to sign up a new user to kik with the given details.
        """
        self.username = username
        self.password = password
        register_message = sign_up.RegisterRequest(email, username, password, first_name, last_name, birthday, captcha_result, self.device_id, self.android_id)
        self.log.info(f"Sending sign up request (name: {first_name} {last_name}, email: {email})...")
        return self._send_xmpp_element(register_message)

    def request_roster(self, is_batched: bool = False, timestamp: Union[str, None] = None, mts: Union[str, None] = None):
        """
        Requests the list of chat partners (people and groups). This is called roster in XMPP terms.
        """
        self.log.info("Requesting roster (list of chat partners)...")
        return self._send_xmpp_element(roster.FetchRosterRequest(is_batched=is_batched, timestamp=timestamp, mts=mts))

    # -------------------------------
    # Common Messaging Operations
    # -------------------------------

    def send_chat_message(self, peer_jid: str, message: str):
        """
        Sends a text chat message to another person or a group with the given JID/username.

        :param peer_jid: The Jabber ID for which to send the message (looks like username_ejs@talk.kik.com)
                         If you don't know the JID of someone, you can also specify a kik username here.
        :param message: The actual message body
        """
        peer_jid = self.get_jid(peer_jid)

        chat_message = chatting.OutgoingChatMessage(peer_jid, message)
        self.log.info(f"Sending chat message '{message}' to {'group' if chat_message.is_group else 'chat'} '{peer_jid}'...")
        return self._send_xmpp_element(chat_message)

    def send_chat_image(self, peer_jid: str, file, forward: bool = True):
        """
        Sends an image chat message to another person or a group with the given JID/username.
        :param peer_jid: The Jabber ID for which to send the message (looks like username_ejs@talk.kik.com)
                         If you don't know the JID of someone, you can also specify a kik username here.
        :param file: The path to the image file OR its bytes OR an IOBase object to send.
        :param forward: True to allow the client to forward the image to other chats
        """
        peer_jid = self.get_jid(peer_jid)
        image = chatting.OutgoingChatImage(peer_jid, file, forward)
        self.log.info(f"Sending chat image to {'group' if image.is_group else 'user'} '{peer_jid}'...")

        content.upload_gallery_image(
            image,
            f"{self.kik_node}@talk.kik.com",
            self.username,
            self.password,
        )
        return self._send_xmpp_element(image)

    def send_read_receipt(self, peer_jid: str, receipt_message_id: Union[str, list[str]], group_jid=None):
        """
        Sends a receipt indicating that the message was read.

        :param peer_jid: The author of the message to send a receipt for
        :param receipt_message_id: The ID of the message read. Can be a single ID or a list of IDs
        :param group_jid: The Group JID if the message is from a group, else None
        """
        self.log.info(f"Sending read receipt to {peer_jid} for message ID {receipt_message_id}")
        receipt = chatting.OutgoingReadReceipt(peer_jid, receipt_message_id, group_jid)
        return self._send_xmpp_element(receipt)

    def send_read_receipt_with_message(self, messages: Union[XMPPResponse, list[XMPPResponse]]) -> list[str]:
        """
        Sends a receipt indicating that the message was read.

        This makes it easy for callers to read incoming messages.

        :param messages: The message to send a delivered receipt for, can be a single message or a list of messages
        """
        if isinstance(messages, list):
            outgoing_ids = []
            sender_map = dict()
            for message in messages:
                map_key = message.from_jid
                if message.is_group:
                    map_key += message.group_jid

                if map_key in sender_map:
                    items = sender_map.get(map_key)
                else:
                    items = list[XMPPResponse]()
                    sender_map[map_key] = items
                items.append(message)

            for batch in sender_map.values():
                outgoing_ids.append(
                    self.send_read_receipt(peer_jid=batch[0].from_jid, receipt_message_id=[m.message_id for m in batch], group_jid=batch[0].group_jid)
                )
            return outgoing_ids
        else:
            return [self.send_read_receipt(peer_jid=messages.from_jid, receipt_message_id=messages.message_id, group_jid=messages.group_jid)]

    def send_delivered_receipt(self, message: Union[XMPPResponse, list[XMPPResponse]]):
        """
        Sends a receipt indicating that the message was delivered

        :param message: The message to send a delivered receipt for.
                        This can be a single message or a list of messages.
        """
        self.log.info(f"Sending delivered receipt to {message.from_jid} for message ID {message.message_id}")
        return self._send_xmpp_element(history.OutgoingAcknowledgement(message))

    def send_is_typing(self, peer_jid: str, is_typing: bool):
        """
        Updates the 'is typing' status of the bot during a conversation.

        :param peer_jid: The JID that the notification will be sent to
        :param is_typing: If true, indicates that we're currently typing, or False otherwise.
        """
        return self._send_xmpp_element(chatting.OutgoingIsTypingEvent(peer_jid, is_typing))

    # Uncomment if you want to set your api key here
    # def send_gif_image(self, peer_jid, search_term, api_key = "YOUR_API_KEY"):
    def send_gif_image(self, peer_jid: str, search_term: str, api_key: str):
        """
        Sends a GIF image to another person or a group with the given JID/username.
        The GIF is taken from tenor.com, based on search keywords.
        :param peer_jid: The Jabber ID for which to send the message (looks like username_ejs@talk.kik.com
        :param search_term: The search term to use when searching GIF images on tenor.com
        :param api_key: The API key for tenor (Get one from https://developers.google.com/tenor/)
        """
        gif = chatting.OutgoingGIFMessage(peer_jid, search_term, api_key)
        self.log.info(f"Sending a GIF message to {'group' if gif.is_group else 'user'} '{peer_jid}'...")
        return self._send_xmpp_element(gif)

    def request_info_of_users(self, peer_jids: Union[str, List[str]]):
        """
        Requests basic information (username, JID, display name, picture) of some users.
        When the information arrives, the callback on_peer_info_received() will fire.

        :param peer_jids: The JID(s) or the username(s) for which to request the information.
                          If you want to request information for more than one user, supply a list of strings.
                          Otherwise, supply a string
        """
        if isinstance(peer_jids, str) and "@" not in peer_jids:
            return self.request_info_of_username(peer_username=peer_jids)
        elif isinstance(peer_jids, list) and len(peer_jids) == 1 and "@" not in peer_jids[0]:
            return self.request_info_of_username(peer_username=peer_jids[0])
        else:
            return self._send_xmpp_element(roster.PeersInfoRequest(peer_jids))

    def request_info_of_username(self, peer_username: str):
        """
        Requests basic information (username, JID, display name, picture) of a single user by their username.
        When the information arrives, the callback on_peer_info_received() will fire.

        :param peer_username: The username for which to request the information.
        """
        return self._send_xmpp_element(roster.QueryUserByUsernameRequest(peer_username))

    def add_friend(self, peer_jid: str):
        """
        Add a user to your friends list. Doing this allows the user to add you to groups.

        :param peer_jid: The JID of the user to remove from friends list
        """
        return self._send_xmpp_element(roster.AddFriendRequest(peer_jid))

    def remove_friend(self, peer_jid: str):
        """
        Removes a user from your friends list. Doing this prevents the user from adding you to groups,
        and you will stop receiving roster updates containing profile information for this user.

        :param peer_jid: The JID of the user to remove from friends list
        """
        return self._send_xmpp_element(roster.RemoveFriendRequest(peer_jid))

    def block_user(self, peer_jid: str):
        """
        Blocks a user. Doing this prevents the user from adding you to groups (same as remove_friend),
        and mobile clients hide the messages received.

        :param peer_jid: The JID of the user to block
        """
        return self._send_xmpp_element(roster.BlockUserRequest(peer_jid))

    def unblock_user(self, peer_jid: str):
        """
        Unblocks a user. Doing this puts the user back in your friends list and allows the user to add you to groups.

        :param peer_jid: The JID of the user to unblock
        """
        return self._send_xmpp_element(roster.UnblockUserRequest(peer_jid))

    def get_muted_users(self):
        """
        Retrieves a list of muted users.

        Clients will receive the muted user list as a callback to on_muted_convos_received().
        """
        return self._send_xmpp_element(roster.GetMutedUsersRequest())

    def mute_user(self, peer_jid: str, expires: Union[float, int, None] = None):
        """
        Mutes a user, this prevents push notifications from being sent to mobile clients.

        :param peer_jid: The JID of the user to mute
        :param expires: The time at which the mute status is automatically removed.
                        The time must be in the future and no more than 30 days in the future.
        """
        return self._send_xmpp_element(roster.MuteUserRequest(peer_jid, expires))

    def unmute_user(self, peer_jid: str):
        """
        Unmutes a user.

        :param peer_jid: The JID of the user to unmute
        """
        return self._send_xmpp_element(roster.UnmuteUserRequest(peer_jid))

    def send_link(self, peer_jid: str, link: str, title: str, text: str = "", app_name: str = "Webpage", preview_jpg_bytes: Union[bytes, None] = None):
        return self._send_xmpp_element(chatting.OutgoingLinkShareEvent(peer_jid, link, title, text, app_name, preview_jpg_bytes))

    def xiphias_get_users(self, peer_jids: Union[str, List[str]]):
        """
        Calls the new format xiphias message to request user data such as profile creation date
        and background picture URL.

        :param peer_jids: one jid, or a list of jids
        """
        return self._send_xmpp_element(xiphias.UsersRequest(peer_jids))

    def xiphias_get_users_by_alias(self, alias_jids: Union[str, List[str]]):
        """
        Like xiphias_get_users, but for aliases instead of jids.

        :param alias_jids: one jid, or a list of jids
        """
        return self._send_xmpp_element(xiphias.UsersByAliasRequest(alias_jids))

    # --------------------------
    #  Group Admin Operations
    # -------------------------

    def change_group_name(self, group_jid: str, new_name: str):
        """
        Changes the name of the group.
        The caller must be a current owner or admin of the group for this request to succeed.

        :param group_jid: The JID of the group whose name should be changed
        :param new_name: The new name to give to the group.
                         Note: if you pass in an empty string, the group name is removed.
        """
        self.log.info(f"Requesting a group name change for JID {group_jid} to '{new_name}'")
        return self._send_xmpp_element(group_adminship.ChangeGroupNameRequest(group_jid, new_name))

    def add_peer_to_group(self, group_jid: str, peer_jid: str):
        """
        Adds someone to a group.
        The caller must be a current member the group for this request to succeed.

        :param group_jid: The JID of the group into which to add a user
        :param peer_jid: The JID of the user to add
        """
        self.log.info(f"Requesting to add user {peer_jid} into the group {group_jid}")
        return self._send_xmpp_element(group_adminship.AddToGroupRequest(group_jid, peer_jid))

    def remove_peer_from_group(self, group_jid: str, peer_jid: str):
        """
        Kicks someone out of a group.
        The caller must be a current owner or admin of the group for this request to succeed.

        :param group_jid: The group JID from which to remove the user
        :param peer_jid: The JID of the user to remove
        """
        self.log.info(f"Requesting removal of user {peer_jid} from group {group_jid}")
        return self._send_xmpp_element(group_adminship.RemoveFromGroupRequest(group_jid, peer_jid))

    def ban_member_from_group(self, group_jid: str, peer_jid: str):
        """
        Bans a member from the group.
        The caller must be a current owner or admin of the group for this request to succeed.
        The user that is being banned must have joined the group at least once.

        :param group_jid: The JID of the relevant group
        :param peer_jid: The JID of the user to ban
        """
        self.log.info(f"Requesting ban of user {peer_jid} from group {group_jid}")
        return self._send_xmpp_element(group_adminship.BanMemberRequest(group_jid, peer_jid))

    def unban_member_from_group(self, group_jid: str, peer_jid: str):
        """
        Unbans a currently banned member of a group.
        The caller must be a current owner or admin of the group for this request to succeed.
        The user that is being banned must have joined the group at least once.

        :param group_jid: The JID of the relevant group
        :param peer_jid: The JID of the user to unban from the group
        """
        self.log.info(f"Requesting un-banning of user {peer_jid} from the group {group_jid}")
        return self._send_xmpp_element(group_adminship.UnbanRequest(group_jid, peer_jid))

    def join_group_with_token(self, group_hashtag: str, group_jid: str, join_token):
        """
        Tries to join into a specific group, using a cryptographic token that was received earlier from a search

        :param group_hashtag: The public hashtag of the group into which to join (like '#Music')
        :param group_jid: The JID of the same group
        :param join_token: a token that can be extracted in the callback on_group_search_response, after calling
                           search_group()
        """
        self.log.info(f"Trying to join the group '{group_hashtag}' with JID {group_jid}")
        return self._send_xmpp_element(roster.GroupJoinRequest(group_hashtag, join_token, group_jid))

    def leave_group(self, group_jid: str):
        """
        Leaves a specific group

        :param group_jid: The JID of the group to leave
        """
        self.log.info(f"Leaving group {group_jid}")
        return self._send_xmpp_element(group_adminship.LeaveGroupRequest(group_jid))

    def promote_to_admin(self, group_jid: str, peer_jid: str):
        """
        Promotes a group member to admin.
        The caller must be a current owner or admin of the group for this request to succeed.

        :param group_jid: The group JID for which the member will become an admin
        :param peer_jid: The JID of user to turn into an admin
        """
        self.log.info(f"Promoting user {peer_jid} to admin in group {group_jid}")
        return self._send_xmpp_element(group_adminship.PromoteToAdminRequest(group_jid, peer_jid))

    def demote_admin(self, group_jid: str, peer_jid: str):
        """
        Removes admin status from a group member.
        The caller must be a current owner of the group for this request to succeed.

        :param group_jid: The group JID in which the rights apply
        :param peer_jid: The admin user to demote
        :return:
        """
        self.log.info(f"Demoting user {peer_jid} to a regular member in group {group_jid}")
        return self._send_xmpp_element(group_adminship.DemoteAdminRequest(group_jid, peer_jid))

    def add_members(self, group_jid: str, peer_jids: Union[str, List[str]]):
        """
        Adds multiple users to a specific group at once
        The caller must be a current member of the group for this request to succeed.

        :param group_jid: The group into which to join the users
        :param peer_jids: a list (or a single string) of JIDs to add to the group
        """
        self.log.info(f"Adding some members to the group {group_jid}")
        return self._send_xmpp_element(group_adminship.AddMembersRequest(group_jid, peer_jids))

    def set_dm_disabled_status(self, group_jid: str, is_dm_disabled: bool):
        """
        Enables or disables direct messaging for a public group.
        The caller must be a current member of the group for this request to succeed.
        Note: this only works for public groups. Private groups have no effect.

        :param group_jid: The group to change the DM disabled status of.
        :param is_dm_disabled: the new DM disabled status.
                               True to close DMs in the group, False to open DMs in the group
        """
        self.log.info(f"Setting DM disabled status to {is_dm_disabled} for group {group_jid}")
        client_jid = f"{self.kik_node}@talk.kik.com"  # Caller can only change their own dmd status
        return self._send_xmpp_element(group_adminship.ChangeDmDisabledRequest(group_jid, client_jid, is_dm_disabled))

    # ----------------------
    # Other Operations
    # ----------------------

    def send_ack(self, messages: Union[list[XMPPResponse], XMPPResponse, None], request_history: bool = False):
        """
        Sends an acknowledgement for a list of messages.
        """
        if isinstance(messages, list) and len(messages) == 0 and not request_history:
            self.log.debug("Skipping acknowledgement request (no messages and not requesting history)")
        elif messages is None and not request_history:
            self.log.debug("Skipping acknowledgement request (message is None and not requesting history)")
        else:
            return self._send_xmpp_element(history.OutgoingAcknowledgement(messages=messages, request_history=request_history))

    def request_messaging_history(self):
        """
        Requests the account's messaging history.
        Results will be returned using the on_message_history_response() callback
        """
        self.log.info("Requesting messaging history")
        return self._send_xmpp_element(history.OutgoingHistoryRequest())

    def search_group(self, search_query):
        """
        Searches for public groups using a query
        Results will be returned using the on_group_search_response() callback

        :param search_query: The query that contains some of the desired groups' name.
        """
        self.log.info(f"Initiating a search for groups using the query '{search_query}'")
        return self._send_xmpp_element(xiphias.GroupSearchRequest(search_query))

    def check_username_uniqueness(self, username):
        """
        Checks if the given username is available for registration.
        Results are returned in the on_username_uniqueness_received() callback

        :param username: The username to check for its existence
        """
        self.log.info(f"Checking for Uniqueness of username '{username}'")
        return self._send_xmpp_element(sign_up.CheckUsernameUniquenessRequest(username))

    def set_profile_picture(self, file: str or bytes or pathlib.Path or io.IOBase):
        """
        Sets the profile picture of the current user

        :param file: The path to the file OR its bytes OR an IOBase object to set
        """
        self.log.info(f"Changing profile picture for {self.username}")
        profile_pictures.set_profile_picture(file, f"{self.kik_node}@talk.kik.com", self.username, self.password)

    def set_background_picture(self, file: str or bytes or pathlib.Path or io.IOBase):
        """
        Sets the background picture of the current user

        :param file: The path to the image file OR its bytes OR an IOBase object to set
        """
        self.log.info(f"Changing background picture for {self.username}")
        profile_pictures.set_background_picture(file, f"{self.kik_node}@talk.kik.com", self.username, self.password)

    def set_group_picture(self, file: str or bytes or pathlib.Path or io.IOBase, group_jid: str, silent: bool = False):
        """
        Sets the profile picture for a group JID.

        The authenticated client must be an admin or owner of the group, otherwise this request will fail.

        :param file: The path to the image file OR its bytes OR an IOBase object to set
        :param group_jid: the JID of the group to change the picture for
        :param silent: If true, no status message is generated when the picture is changed
        """
        self.log.info(f"Changing group picture for {self.username} in {group_jid} (silent={silent})")
        profile_pictures.set_group_picture(file, f"{self.kik_node}@talk.kik.com", group_jid, self.username, self.password, silent)

    def send_ping(self):
        """
        Sends a ping stanza.

        Once received, Kik replies with a `<pong/>` and KikClientCallback.on_pong will be called.

        Clients do not require authentication to send pings.
        """
        self.log.debug("Sending ping")
        self._send_xmpp_element(chatting.KikPingRequest())
        self._last_ping_sent_time = KikServerClock.get_system_time()

    def send_captcha_result(self, stc_id, captcha_result):
        """
        In case a captcha was encountered, solves it using an element ID and a response parameter.
        The stc_id can be extracted from a CaptchaElement, and the captcha result needs to be extracted manually with
        a browser. Please see solve_captcha_wizard() for the steps needed to solve the captcha

        :param stc_id: The stc_id from the CaptchaElement that was encountered
        :param captcha_result: The answer to the captcha (which was generated after solved by a human)
        """
        self.log.info(f"Trying to solve a captcha with result: '{captcha_result}'")
        return self._send_xmpp_element(login.CaptchaSolveRequest(stc_id, captcha_result))

    def get_my_profile(self):
        """
        Fetches your own profile details
        """
        self.log.info("Requesting self profile")
        return self._send_xmpp_element(account.GetMyProfileRequest())

    def change_display_name(self, first_name, last_name):
        """
        Changes the display name

        :param first_name: The first name
        :param last_name: The last name
        """
        self.log.info(f"Changing the display name to '{first_name} {last_name}'")
        return self._send_xmpp_element(account.ChangeNameRequest(first_name, last_name))

    def change_password(self, new_password, email):
        """
        Changes the login password

        :param new_password: The new login password to set for the account
        :param email: The current email of the account
        """
        self.log.info("Changing the password of the account")
        return self._send_xmpp_element(account.ChangePasswordRequest(self.password, new_password, email, self.username))

    def change_email(self, new_email):
        """
        Changes the email of the current account

        :param new_email: The new email to set
        """
        self.log.info(f"Changing account email to '{new_email}'")
        return self._send_xmpp_element(account.ChangeEmailRequest(self.password, new_email))

    def disconnect(self, permanent: bool = True):
        """
        Closes the connection to Kik.

        If the current connection is already closed or closing, this is a no-op.

        :permanent: if True, the client will not reconnect and future attempts to reconnect will fail.
        """
        self.is_permanent_disconnection = True if self.is_permanent_disconnection else permanent
        if self.connection:
            self.log.info("Disconnecting.")
            self.connection.close()
        else:
            self.log.error("Can't disconnect, no connection")

    # -----------------
    # Internal methods
    # -----------------

    def _send_xmpp_element(self, message: XMPPElement):
        """
        Serializes and sends the given XMPP element to kik servers
        :param message: The XMPP element to send
        :return: The UUID of the element that was sent
        """
        while not self.connected:
            self.log.debug("Waiting for connection.")
            time.sleep(0.5)  # Reduces console spam

        packet = message.serialize()
        if not isinstance(packet, bytes):
            # This is a dom tree
            packet = xml_utilities.encode_etree(packet)

        self.loop.call_soon_threadsafe(self.connection.send_raw_data, packet)

        return message.message_id

    @run_in_new_thread
    def _on_new_stanza_received(self, xml_element: BeautifulSoup):
        """
        Gets called when the client receives a new XMPP stanza from Kik.
        :param xml_element: The stanza received (Tag)
        """
        # choose the handler based on the XML tag name

        if xml_element.name == "iq":
            self._handle_received_iq_element(xml_element)
        elif xml_element.name == "message":
            self._handle_xmpp_message(xml_element)
        elif xml_element.name == "stc":
            if xml_element.stp["type"] == "ca":
                self.callback.on_captcha_received(login.CaptchaElement(xml_element))
            elif xml_element.stp["type"] == "bn":
                self.callback.on_temp_ban_received(login.TempBanElement(xml_element))
            else:
                self.log.warning(f'Unknown stc element type: {xml_element["type"]}')
        elif xml_element.name == "ack":
            pass
        elif xml_element.name == "pong":
            latency = KikServerClock.get_system_time() - self._last_ping_sent_time
            self.callback.on_pong(chatting.KikPongResponse(latency))
        else:
            self.log.warning(f"Unknown element type: {xml_element.name}")

    def _handle_received_k_element(self, k_element: BeautifulSoup) -> bool:
        """
        The 'k' element appears to be kik's connection-related stanza.
        It lets us know if a connection or a login was successful or not.

        :param k_element: The XML element we just received from kik.
        :return: true if connection succeeded
        """
        connected = k_element["ok"] == "1"

        if connected:
            self.connected = True

            if "ts" in k_element.attrs:
                # authenticated!
                KikServerClock.recalculate_offset(int(k_element["ts"]))

                self.log.info("Authenticated successfully.")
                self.authenticated = True
                if not self.disable_auth_cert:
                    self.authenticator.send_stanza()
                self.callback.on_authenticated()
            elif self.should_login_on_connection:
                self.login(self.username, self.password)
                self.should_login_on_connection = False
        else:
            error = login.ConnectionFailedResponse(k_element)
            if error.is_auth_revoked:
                # Force a login attempt
                self.kik_node = None
            self.callback.on_connection_failed(error)
        return connected

    def _handle_received_iq_element(self, iq_element: BeautifulSoup):
        """
        The 'iq' (info/query) stanzas in XMPP represents the request/ response elements.
        We send an iq stanza to request for information, and we receive an iq stanza in response to this request,
        with the same ID attached to it.
        For a great explanation of this stanza: http://slixmpp.readthedocs.io/api/stanza/iq.html

        :param iq_element: The iq XML element we just received from kik.
        """
        result_type = iq_element["type"]
        if result_type == "error":
            error = iq_element.find("error", recursive=False)
            if error:
                if error.find("bad-request", recursive=False):
                    raise Exception(f'Received a Bad Request error for stanza with ID {iq_element.attrs["id"]}')
                elif error.find("service-unavailable", recursive=False):
                    raise Exception(f'Received a service Unavailable error for stanza with ID {iq_element.attrs["id"]}')

        # Some successful IQ responses don't have a query element
        query = iq_element.find("query", recursive=False)
        if query:
            xml_namespace = iq_element.query["xmlns"]
            self._handle_response(xml_namespace, iq_element)

    def _handle_response(self, xmlns, iq_element):
        """
        Handles a response that we receive from kik after our initiated request.
        Examples: response to a group search, response to fetching roster, etc.

        :param xmlns: The XML namespace that helps us understand what type of response this is
        :param iq_element: The actual XML element that contains the response
        """
        if xmlns == "kik:iq:check-unique":
            xmlns_handlers.CheckUsernameUniqueResponseHandler(self.callback, self).handle(iq_element)
        elif xmlns == "jabber:iq:register":
            xmlns_handlers.RegisterOrLoginResponseHandler(self.callback, self).handle(iq_element)
        elif xmlns == "jabber:iq:roster":
            xmlns_handlers.RosterResponseHandler(self.callback, self).handle(iq_element)
        elif xmlns in ["kik:iq:friend", "kik:iq:friend:batch"]:
            xmlns_handlers.PeersInfoResponseHandler(self.callback, self).handle(iq_element)
        elif xmlns == "kik:iq:xiphias:bridge":
            xmlns_handlers.XiphiasHandler(self.callback, self).handle(iq_element)
        elif xmlns == "kik:auth:cert":
            self.authenticator.handle(iq_element)
        elif xmlns == "kik:iq:QoS":
            xmlns_handlers.HistoryHandler(self.callback, self).handle(iq_element)
        elif xmlns == "kik:iq:user-profile":
            xmlns_handlers.UserProfileHandler(self.callback, self).handle(iq_element)
        elif xmlns == "kik:iq:convos":
            xmlns_handlers.MutedConvosHandler(self.callback, self).handle(iq_element)

    def _handle_xmpp_message(self, data: BeautifulSoup):
        """
        an XMPP 'message' in the case of Kik is the actual stanza we receive when someone sends us a message
        (weather groupchat or not), starts typing, stops typing, reads our message, etc.
        Examples: http://slixmpp.readthedocs.io/api/stanza/message.html

        :param data: The XMPP 'message' element we received, or 'msg' if from QoS history
        """
        # The XML namespace is different for iOS and Android, handle the messages with their actual type
        message = XMPPResponse(data)
        message_type = message.type

        if message_type == "chat":
            xmlns_handlers.XMPPChatMessageHandler(self.callback, self).handle(data)
        elif message_type == "groupchat":
            xmlns_handlers.XMPPGroupChatMessageHandler(self.callback, self).handle(data)
        elif message_type == "receipt" and data.find("receipt", recursive=False):
            receipt_type = data.find("receipt", recursive=False)["type"]
            if message.is_group:
                self.callback.on_group_receipts_received(chatting.IncomingGroupReceiptsEvent(data))
            elif receipt_type == "delivered":
                self.callback.on_message_delivered(chatting.IncomingMessageDeliveredEvent(data))
            elif receipt_type == "read":
                self.callback.on_message_read(chatting.IncomingMessageReadEvent(data))
        elif message_type == "is-typing":
            self.callback.on_is_typing_event_received(chatting.IncomingIsTypingEvent(data))
        elif message_type == "error":
            self.callback.on_error_message_received(chatting.IncomingErrorMessage(data))
        else:
            self.log.warning(f"Received unknown XMPP element type: {data}")

    def _kik_connection_thread_function(self):
        """
        The Kik Connection thread main function.
        Initiates the asyncio loop and actually connects.
        """
        # If there is already a connection going, then wait for it to stop
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            self.log.debug("Waiting for the previous connection to stop.")
            while not self.connection.is_closed:
                self.log.debug("Still waiting for the previous connection to stop.")
                time.sleep(1)

        self.log.info("Initiating the Kik Connection thread and connecting to kik server...")

        # create the connection and launch the asyncio loop
        self.connection = KikConnection(self)
        task = self.loop.create_task(self.connection.read_loop())

        self.loop.run_until_complete(task)
        self.log.debug("Main loop ended.")
        self.callback.on_disconnected()
        self._connect()

    def get_jid(self, username_or_jid):
        if jid_utilities.is_pm_jid(username_or_jid):
            # this is already a JID.
            return username_or_jid
        elif jid_utilities.is_group_jid(username_or_jid):
            # this is already a group JID.
            return username_or_jid

        username = username_or_jid

        # first search if we already have it
        if self.get_jid_from_cache(username) is None:
            # go request for it

            self._new_user_added_event.clear()
            self.request_info_of_username(username)
            if not self._new_user_added_event.wait(5.0):
                raise TimeoutError(f"Could not get the JID for username {username} in time")

        return self.get_jid_from_cache(username)

    def get_jid_from_cache(self, username):
        for user in self._known_users_information:
            if user.username.lower() == username.lower():
                return user.jid

        return None

    @staticmethod
    def is_group_jid(jid: str) -> bool:
        return jid_utilities.is_group_jid(jid)


class KikConnection:
    def __init__(self, api: KikClient):
        self.api = api
        self.log = api.log
        self.reader: Union[StreamReader, None] = None
        self.writer: Union[StreamWriter, None] = None
        self.is_closed = False

    # noinspection PyProtectedMember
    async def read_loop(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(host=HOST, port=PORT, ssl=ssl.create_default_context())
            parser = KikXmlParser(self.reader, self.log)

            self.log.info("Connected.")
            self.api._on_connection_made()

            k = await parser.read_initial_k()
            self.log.debug("%s bind: %s", self.api.username, k)

            if not self.api._handle_received_k_element(k):
                self.close()
                return

            while not self.is_closed:
                stanza = await parser.read_next_stanza()
                self.log.debug("Received: %s", stanza)
                self.api.loop.call_soon_threadsafe(self.api._on_new_stanza_received, stanza)
        except Exception:
            self.log.warning("Received error in main loop: %s", traceback.format_exc())
        finally:
            self.api.connected = False
            if not self.is_closed:
                self.log.warning("Connection unexpectedly lost")
            self.close()

    def send_raw_data(self, data: bytes):
        if not self.writer:
            self.log.error("Can't send raw data, writer not instantiated: %s", data)
        elif self.writer.is_closing():
            self.log.error("Can't send raw data, stream is closed or closing: %s", data)
        else:
            self.log.debug("Sending raw data: %s", data)
            self.writer.write(data)

    def close(self):
        if not self.is_closed:
            self.is_closed = True
            if self.writer and not self.writer.is_closing():
                self.writer.write(b"</k>")
                self.writer.close()
