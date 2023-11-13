import asyncio
import re
import time
import xml.etree.ElementTree as element_tree
from threading import Thread, Event
from typing import Union, List, Tuple
from asyncio import Transport, Protocol
from bs4 import BeautifulSoup

import kik_unofficial.callbacks as callbacks
import kik_unofficial.datatypes.exceptions as exceptions
import kik_unofficial.datatypes.xmpp.chatting as chatting
import kik_unofficial.datatypes.xmpp.group_adminship as group_adminship
import kik_unofficial.datatypes.xmpp.login as login
import kik_unofficial.datatypes.xmpp.roster as roster
import kik_unofficial.datatypes.xmpp.history as history
import kik_unofficial.datatypes.xmpp.sign_up as sign_up
import kik_unofficial.xmlns_handlers as xmlns_handlers
from kik_unofficial.datatypes.xmpp.auth_stanza import AuthStanza
from kik_unofficial.datatypes.xmpp import account, xiphias
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils
from kik_unofficial.utilities.threading_utils import run_in_new_thread
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement
from kik_unofficial.http import profile_pictures, content
from kik_unofficial.utilities.credential_utilities import random_device_id, random_android_id
from kik_unofficial.utilities.logging_utils import set_up_basic_logging

HOST, PORT = CryptographicUtils.get_kik_host_name(), 5223


class KikClient:
    """
    The main kik class with which you're managing a kik connection and sending commands
    """

    def __init__(self, callback: callbacks.KikClientCallback, kik_username: str, kik_password: str,
                 kik_node: str = None, device_id: str = None, android_id: str = random_android_id(), log_level: int = 1,
                 log_file_path: str = None) -> None:

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
        :param device_id: a unique device ID. If you don't supply one, a random one will be generated. (generated in __init__ if None)
        :param android_id: a unique android ID. If you don't supply one, a random one will be generated.
        ;param log_level: Level of logging 1 debug, 2 info, 3 warn, 4 error, 5 critical.
        ;param logger_name; Name to use for the logger.
        ;param log_file_path: If set will create a daily rotated log file and archive for 7 days.

        """

        self.logger = set_up_basic_logging(log_level=log_level, logger_name="kik_unofficial",
                                           log_file_path=log_file_path)

        self.username = kik_username
        self.password = kik_password
        self.kik_node = kik_node
        self.kik_email = None
        self.device_id = device_id or random_device_id()
        self.android_id = android_id

        self.callback = callback
        self.authenticator = AuthStanza(self)

        self.connected = False
        self.authenticated = False
        self.connection = None
        self.is_exiting = False
        self.is_expecting_connection_reset = False
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self._known_users_information = set()
        self._new_user_added_event = Event()
        self.friend_request_mapping = {}

        self.should_login_on_connection = kik_username is not None and kik_password is not None
        self._connect()

    def _connect(self):
        """
        Runs the kik connection thread, which creates an encrypted (SSL based) TCP connection
        to the kik servers.
        """
        self.kik_connection_thread = Thread(target=self._kik_connection_thread_function, name="Kik Connection")
        self.kik_connection_thread.start()

    def wait_for_messages(self):
        for i in range(5):
            self.kik_connection_thread.join()
            if i == 0 and not self.is_exiting:
                self.logger.warning("Connection has <<disconnected>>, trying again...")

            if self.is_exiting:
                break
            time.sleep(1)

        self.logger.critical("<<Exiting...>>")

    def _on_connection_made(self):
        """
        Gets called when the TCP connection to kik's servers is done and we are connected.
        Now we might initiate a login request or an auth request.
        """
        if self.username and self.password and self.kik_node and self.device_id:
            # we have all required credentials, we can authenticate
            self.logger.info(
                f"Establishing authenticated connection using kik node '{self.kik_node}', device id '{self.device_id}' and android id '{self.android_id}'...")

            message = login.EstablishAuthenticatedSessionRequest(self.kik_node, self.username, self.password,
                                                                 self.device_id)
        else:
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
        self.logger.info("Closing current connection and creating a new authenticated one.")

        self.disconnect()
        self._connect()

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
        login_type = "email" if '@' in self.username else "username"
        self.logger.info(f"Logging in with {login_type} '{username}' and a given password {'*' * len(password)}...")
        return self._send_xmpp_element(login_request)

    def register(self, email, username, password, first_name, last_name, birthday="1974-11-20",
                 captcha_result: str = None):
        """
        Sends a register request to sign up a new user to kik with the given details.
        """
        self.username = username
        self.password = password
        register_message = sign_up.RegisterRequest(email, username, password, first_name, last_name, birthday,
                                                   captcha_result,
                                                   self.device_id, self.android_id)
        self.logger.info(f"Sending sign up request (name: {first_name} {last_name}, email: {email})...")
        return self._send_xmpp_element(register_message)

    def request_roster(self, is_big=True, timestamp=None):
        """
        Requests the list of chat partners (people and groups). This is called roster in XMPP terms.
        """
        self.logger.info("Requesting roster (list of chat partners)...")
        return self._send_xmpp_element(roster.FetchRosterRequest(is_big=is_big, timestamp=timestamp))

    # -------------------------------
    # Common Messaging Operations
    # -------------------------------

    def send_chat_message(self, peer_jid: str, message: str, bot_mention_jid=None):
        """
        Sends a text chat message to another person or a group with the given JID/username.

        :param peer_jid: The Jabber ID for which to send the message (looks like username_ejs@talk.kik.com)
                         If you don't know the JID of someone, you can also specify a kik username here.
        :param message: The actual message body
        :param bot_mention_jid: If an official bot is referenced, their jid must be embedded as mention for them
        to respond.
        """
        peer_jid = self.get_jid(peer_jid)

        if self.is_group_jid(peer_jid):
            self.logger.info(f"Sending chat message '{message}' to group '{peer_jid}'...")
            return self._send_xmpp_element(chatting.OutgoingGroupChatMessage(peer_jid, message, bot_mention_jid))
        else:
            self.logger.info(f"Sending chat message '{message}' to user '{peer_jid}'...")
            return self._send_xmpp_element(chatting.OutgoingChatMessage(peer_jid, message, False, bot_mention_jid))

    def send_chat_image(self, peer_jid: str, image_file, allow_forward=False, allow_save=False):
        """
        Sends an image chat message to another person or a group with the given JID/username.
        :param peer_jid: The Jabber ID for which to send the message (looks like username_ejs@talk.kik.com)
                         If you don't know the JID of someone, you can also specify a kik username here.
        :param image_file: The path to the image file OR its bytes OR an IOBase object to send.
        :param allow_save: Allow Saving of the image. bool
        :param allow_forward: Allow Forwarding of the Image. bool
        """
        peer_jid = self.get_jid(peer_jid)
        is_group = self.is_group_jid(peer_jid)

        self.logger.info(f'Sending chat image to {"group" if is_group else "user"} \'{peer_jid}\'')

        image_request = chatting.OutgoingChatImage(peer_jid, image_file, allow_forward, allow_save, is_group)

        content.upload_gallery_image(image_request, self.kik_node + '@talk.kik.com', self.username, self.password)
        return self._send_xmpp_element(image_request)

    def send_video_message(self, peer_jid: str, video_file, allow_forward=True, allow_save=True,
                           auto_play=False, muted=False, looping=False):
        """
        Sends a video message to another person or a group with the given JID/username.
        WARNING: videos above 15 MB (15728640 bytes) will be rejected by Kik's upload server.

        :param allow_forward: Allow forwarding of the video. bool
        :param allow_save: Allow saving of the video. bool
        :param auto_play: Causes the video to auto-play when it is on the screen. bool
        :param muted: Mutes the video when played. bool
        :param looping: Loops the video when played. bool
        :param peer_jid: The Jabber ID for which to send the message (looks like username_ejs@talk.kik.com)
                         If you don't know the JID of someone, you can also specify a kik username here.
        :param video_file: The path to the video file OR its bytes OR an IOBase object to send.
        """
        peer_jid = self.get_jid(peer_jid)
        is_group = self.is_group_jid(peer_jid)

        self.logger.info(f' Sending chat video to {"group" if is_group else "user"} \'{peer_jid}\'')

        video_request = chatting.OutgoingVideoMessage(peer_jid, video_file, allow_forward, allow_save, auto_play, muted,
                                                      looping, is_group)

        # Do not send the video stanza until the video is successfully uploaded to the Kik platform server
        # This prevents "failed to load" errors
        content.upload_gallery_video(video_request, self.kik_node + '@talk.kik.com', self.username, self.password)

        return self._send_xmpp_element(video_request)

    def send_read_receipt(self, peer_jid: str, receipt_message_id: str, group_jid=None):
        """
        Sends a read receipt for a previously sent message, to a specific user or group.

        :param peer_jid: The JID of the user to which to send the receipt.
        :param receipt_message_id: The message ID that the receipt is sent for
        :param group_jid If the receipt is sent for a message that was sent in a group,
                         this parameter should contain the group's JID
        """
        self.logger.info(f"Sending read receipt to JID {peer_jid} for message ID {receipt_message_id}")
        return self._send_xmpp_element(chatting.OutgoingReadReceipt(peer_jid, receipt_message_id, group_jid))

    def send_delivered_receipt(self, peer_jid: str, receipt_message_id: str, group_jid: str = None):
        """
        Sends a receipt indicating that a specific message was received, to another person.

        :param peer_jid: The other peer's JID to send to receipt to
        :param receipt_message_id: The message ID for which to generate the receipt
        :param group_jid: The group's JID, in case the receipt is sent in a group (None otherwise)
        """
        self.logger.info(f"Sending delivered receipt to JID {peer_jid} for message ID {receipt_message_id}")
        return self._send_xmpp_element(chatting.OutgoingDeliveredReceipt(peer_jid, receipt_message_id, group_jid))

    def send_is_typing(self, peer_jid: str, is_typing: bool):
        """
        Updates the 'is typing' status of the bot during a conversation.

        :param peer_jid: The JID that the notification will be sent to
        :param is_typing: If true, indicates that we're currently typing, or False otherwise.
        """
        if self.is_group_jid(peer_jid):
            return self._send_xmpp_element(chatting.OutgoingGroupIsTypingEvent(peer_jid, is_typing))
        else:
            return self._send_xmpp_element(chatting.OutgoingIsTypingEvent(peer_jid, is_typing))

    # Uncomment if you want to set your api key here
    # def send_gif_image(self, peer_jid, search_term, API_key = "YOUR_API_KEY"):
    def send_gif_image(self, peer_jid: str, search_term: str, API_key: str, random_gif=False):
        """
        Sends a GIF image to another person or a group with the given JID/username.
        The GIF is taken from tenor.com, based on search keywords.
        :param peer_jid: The Jabber ID for which to send the message (looks like username_ejs@talk.kik.com
        :param search_term: The search term to use when searching GIF images on tendor.com
        :param API_key: The API key for tenor (Get one from https://developers.google.com/tenor/)
        :param random_gif: Pick a GIF at random from tenor gif result.
        """
        if self.is_group_jid(peer_jid):
            self.logger.info(f"Sending a GIF message to group '{peer_jid}'...")
            return self._send_xmpp_element(
                chatting.OutgoingGIFMessage(peer_jid, search_term, API_key, random_gif=random_gif, is_group=True))
        else:
            self.logger.info(f"Sending a GIF message to user '{peer_jid}'...")
            return self._send_xmpp_element(
                chatting.OutgoingGIFMessage(peer_jid, search_term, API_key, random_gif=random_gif, is_group=False))

    def send_saved_gif_image(self, peer_jid: str, gif_path):
        """
        Sends a GIF image to another person or a group with the given JID/username.
        The GIF is stored in json format when setting a gif as a substitution or trigger.
        :param peer_jid: The Jabber ID for which to send the message (looks like username_ejs@talk.kik.com
        :param gif_path: The path to the file that contains gif information
        """
        if self.is_group_jid(peer_jid):
            self.logger.info(f'Sending a GIF message to group \'{peer_jid}\'...')
            return self._send_xmpp_element(chatting.OutgoingSavedGIFMessage(peer_jid, gif_path, True))
        else:
            self.logger.info(f'Sending a GIF message to user \'{peer_jid}\'...')
            return self._send_xmpp_element(chatting.OutgoingSavedGIFMessage(peer_jid, gif_path, False))

    def request_info_of_users(self, peer_jids: Union[str, List[str]]):
        """
        Requests basic information (username, JID, display name, picture) of some users.
        When the information arrives, the callback on_peer_info_received() will fire.

        :param peer_jids: The JID(s) or the username(s) for which to request the information.
                          If you want to request information for more than one user, supply a list of strings.
                          Otherwise, supply a string
        """

        return self._send_xmpp_element(roster.QueryUsersInfoRequest(peer_jids))

    def add_friend(self, peer_jid):
        message = roster.AddFriendRequest(peer_jid)
        if "_a@talk" in peer_jid:
            self.friend_request_mapping[message.message_id] = peer_jid

        return self._send_xmpp_element(message)

    def remove_friend(self, peer_jid):
        return self._send_xmpp_element(roster.RemoveFriendRequest(peer_jid))

    def send_link(self, peer_jid, link, title, text='', app_name='Webpage', thumbnail=None, allow_forward=True):
        return self._send_xmpp_element(
            chatting.OutgoingLinkShareEvent(peer_jid, link, title, text, app_name, thumbnail, allow_forward))

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
        Changes the a group's name to something new

        :param group_jid: The JID of the group whose name should be changed
        :param new_name: The new name to give to the group
        """
        self.logger.info(f"Requesting a group name change for JID {group_jid} to '{new_name}'")
        return self._send_xmpp_element(group_adminship.ChangeGroupNameRequest(group_jid, new_name))

    def add_peer_to_group(self, group_jid, peer_jid):
        """
        Adds someone to a group

        :param group_jid: The JID of the group into which to add a user
        :param peer_jid: The JID of the user to add
        """
        self.logger.info(f"Requesting to add user {peer_jid} into the group {group_jid}")
        return self._send_xmpp_element(group_adminship.AddToGroupRequest(group_jid, peer_jid))

    def remove_peer_from_group(self, group_jid, peer_jid):
        """
        Kicks someone out of a group

        :param group_jid: The group JID from which to remove the user
        :param peer_jid: The JID of the user to remove
        """
        self.logger.info(f"Requesting removal of user {peer_jid} from group {group_jid}")
        return self._send_xmpp_element(group_adminship.RemoveFromGroupRequest(group_jid, peer_jid))

    def ban_member_from_group(self, group_jid, peer_jid):
        """
        Bans a member from the group

        :param group_jid: The JID of the relevant group
        :param peer_jid: The JID of the user to ban
        """
        self.logger.info(f"Requesting ban of user {peer_jid} from group {group_jid}")
        return self._send_xmpp_element(group_adminship.BanMemberRequest(group_jid, peer_jid))

    def unban_member_from_group(self, group_jid, peer_jid):
        """
        Undos a ban of someone from a group

        :param group_jid: The JID of the relevant group
        :param peer_jid: The JID of the user to un-ban from the gorup
        """
        self.logger.info(f"Requesting un-banning of user {peer_jid} from the group {group_jid}")
        return self._send_xmpp_element(group_adminship.UnbanRequest(group_jid, peer_jid))

    def join_group_with_token(self, group_hashtag, group_jid, join_token):
        """
        Tries to join into a specific group, using a cryptographic token that was received earlier from a search

        :param group_hashtag: The public hashtag of the group into which to join (like '#Music')
        :param group_jid: The JID of the same group
        :param join_token: a token that can be extracted in the callback on_group_search_response, after calling
                           search_group()
        """
        self.logger.info(f"Trying to join the group '{group_hashtag}' with JID {group_jid}")
        return self._send_xmpp_element(roster.GroupJoinRequest(group_hashtag, join_token, group_jid))

    def leave_group(self, group_jid):
        """
        Leaves a specific group

        :param group_jid: The JID of the group to leave
        """
        self.logger.info(f"Leaving group {group_jid}")
        return self._send_xmpp_element(group_adminship.LeaveGroupRequest(group_jid))

    def promote_to_admin(self, group_jid, peer_jid):
        """
        Turns some group member into an admin

        :param group_jid: The group JID for which the member will become an admin
        :param peer_jid: The JID of user to turn into an admin
        """
        self.logger.info(f"Promoting user {peer_jid} to admin in group {group_jid}")
        return self._send_xmpp_element(group_adminship.PromoteToAdminRequest(group_jid, peer_jid))

    def demote_admin(self, group_jid, peer_jid):
        """
        Turns an admin of a group into a regular user with no amidships capabilities.

        :param group_jid: The group JID in which the rights apply
        :param peer_jid: The admin user to demote
        :return:
        """
        self.logger.info(f"Demoting user {peer_jid} to a regular member in group {group_jid}")
        return self._send_xmpp_element(group_adminship.DemoteAdminRequest(group_jid, peer_jid))

    def add_members(self, group_jid, peer_jids: Union[str, List[str]]):
        """
        Adds multiple users to a specific group at once

        :param group_jid: The group into which to join the users
        :param peer_jids: a list (or a single string) of JIDs to add to the group
        """
        self.logger.info(f"Adding some members to the group {group_jid}")
        return self._send_xmpp_element(group_adminship.AddMembersRequest(group_jid, peer_jids))

    # ----------------------
    # Other Operations
    # ----------------------

    def send_ack(self, sender_jid, is_receipt: bool, message_id, group_jid=None):
        """
        Sends an acknowledgement for a provided message ID
        """
        self.logger.info(f"Sending acknowledgement for message ID {message_id}")
        return self._send_xmpp_element(history.OutgoingAcknowledgement(sender_jid, is_receipt, message_id, group_jid))

    def request_messaging_history(self):
        """
        Requests the account's messaging history.
        Results will be returned using the on_message_history_response() callback
        """
        self.logger.info("Requesting messaging history")
        return self._send_xmpp_element(history.OutgoingHistoryRequest())

    def search_group(self, search_query):
        """
        Searches for public groups using a query
        Results will be returned using the on_group_search_response() callback

        :param search_query: The query that contains some of the desired groups' name.
        """
        self.logger.info(f"Initiating a search for groups using the query '{search_query}'")
        return self._send_xmpp_element(roster.GroupSearchRequest(search_query))

    def check_username_uniqueness(self, username):
        """
        Checks if the given username is available for registration.
        Results are returned in the on_username_uniqueness_received() callback

        :param username: The username to check for its existence
        """
        self.logger.info(f"Checking for Uniqueness of username '{username}'")
        return self._send_xmpp_element(sign_up.CheckUsernameUniquenessRequest(username))

    def set_profile_picture(self, filename):
        """
        Sets the profile picture of the current user

        :param filename: The path to the file OR its bytes OR an IOBase object to set
        """
        self.logger.info(f"Setting the profile picture to file '{filename}'")
        profile_pictures.set_profile_picture(
            filename, f'{self.kik_node}@talk.kik.com', self.username, self.password
        )

    def set_background_picture(self, filename):
        """
        Sets the background picture of the current user

        :param filename: The path to the image file OR its bytes OR an IOBase object to set
        """
        self.logger.info(f"Setting the background picture to filename '{filename}'")
        profile_pictures.set_background_picture(
            filename, f'{self.kik_node}@talk.kik.com', self.username, self.password
        )

    def send_ping(self):
        """
               Sends Ping Stanza A response Pong Should return from the server
               Pong Object will include round trip time
        """
        self.logger.info(f'Sending KIK servers a ping.')
        return self._send_xmpp_element(chatting.KikPingRequest())

    def send_captcha_result(self, stc_id, captcha_result):
        """
        In case a captcha was encountered, solves it using an element ID and a response parameter.
        The stc_id can be extracted from a CaptchaElement, and the captcha result needs to be extracted manually with
        a browser. Please see solve_captcha_wizard() for the steps needed to solve the captcha

        :param stc_id: The stc_id from the CaptchaElement that was encountered
        :param captcha_result: The answer to the captcha (which was generated after solved by a human)
        """
        self.logger.info(f"Trying to solve a captcha with result: '{captcha_result}'")
        return self._send_xmpp_element(login.CaptchaSolveRequest(stc_id, captcha_result))

    def get_my_profile(self):
        """
        Fetches your own profile details
        """
        self.logger.info("Requesting self profile")
        return self._send_xmpp_element(account.GetMyProfileRequest())

    def change_display_name(self, first_name, last_name):
        """
        Changes the display name

        :param first_name: The first name
        :param last_name: The last name
        """
        self.logger.info(f"Changing the display name to '{first_name} {last_name}'")
        return self._send_xmpp_element(account.ChangeNameRequest(first_name, last_name))

    def change_password(self, new_password, email):
        """
        Changes the login password

        :param new_password: The new login password to set for the account
        :param email: The current email of the account
        """
        self.logger.info("Changing the password of the account")
        return self._send_xmpp_element(account.ChangePasswordRequest(self.password, new_password, email, self.username))

    def change_email(self, old_email, new_email):
        """
        Changes the email of the current account

        :param old_email: The current email
        :param new_email: The new email to set
        """
        self.logger.info(f"Changing account email to '{new_email}'")
        return self._send_xmpp_element(account.ChangeEmailRequest(self.password, old_email, new_email))

    def disconnect(self, is_exiting=False):
        """
        Closes the connection to kik's servers.
        param is_exiting: If True will stop the connection loop
        """
        self.logger.warning("Disconnecting.")
        self.connection.close()
        self.is_expecting_connection_reset = True

        # if is_exiting is True we stop the main loop and exit
        # in some cases we don't want to do this because we want to restart a connection.
        if is_exiting:
            self.is_exiting = True
            self.loop.stop()

    # -----------------
    # Internal methods
    # -----------------

    def _send_xmpp_element(self, message: XMPPElement):
        """
        Serializes and sends the given XMPP element to kik servers
        :param xmpp_element: The XMPP element to send
        :return: The UUID of the element that was sent
        """
        if message is None:
            self.logger.critical("Got NoneType XMPP Element when trying to send to KIK.")
            return 0
        while not self.connected:
            self.logger.debug("Waiting for connection.")
            time.sleep(0.1)
        if type(message.serialize()) is list:
            self.logger.debug("Sending multi packet data.")
            packets = message.serialize()
            for p in packets:
                self.loop.call_soon_threadsafe(self.connection.send_raw_data, p)
        else:
            self.loop.call_soon_threadsafe(self.connection.send_raw_data, message.serialize())

        return message.message_id

    @run_in_new_thread
    def _on_new_data_received(self, data: bytes):
        """
        Gets called whenever we get a whole new XML element from kik's servers.
        :param data: The data received (bytes)
        """
        if data == b' ':
            # Happens every half hour. Disconnect after 10th time. Some kind of keep-alive? Let's send it back.
            self.loop.call_soon_threadsafe(self.connection.send_raw_data, b' ')
            return

        xml_element = BeautifulSoup(data.decode('utf-8'), features='xml')
        xml_element = next(iter(xml_element)) if len(xml_element) > 0 else xml_element

        # choose the handler based on the XML tag name

        if xml_element.name == "k":
            self._handle_received_k_element(xml_element)
        elif xml_element.name == "iq":
            self._handle_received_iq_element(xml_element)
        elif xml_element.name == "message":
            self._handle_xmpp_message(xml_element)
        elif xml_element.name == 'stc':
            if xml_element.stp['type'] == 'ca':
                self.callback.on_captcha_received(login.CaptchaElement(xml_element))
            elif xml_element.stp['type'] == 'bn':
                self.callback.on_temp_ban_received(login.TempBanElement(xml_element))
            else:
                self.logger.warning(f'Unknown stc element type: {xml_element["type"]}')
        elif xml_element.name == 'ack':
            pass
        elif xml_element.name == 'pong':
            self.callback.on_pong(chatting.KikPongResponse(xml_element))
        else:
            self.logger.warning(f'Unknown element type: {xml_element.name}')

    def _handle_received_k_element(self, k_element: BeautifulSoup):
        """
        The 'k' element appears to be kik's connection-related stanza.
        It lets us know if a connection or a login was successful or not.

        :param k_element: The XML element we just received from kik.
        """

        if k_element['ok'] == "1":
            self.connected = True

            if 'ts' in k_element.attrs:
                # authenticated!
                self.logger.info("Authenticated successfully.")
                self.authenticated = True
                self.authenticator.send_stanza()
                self.callback.on_authenticated()
            elif self.should_login_on_connection:
                self.login(self.username, self.password)
                self.should_login_on_connection = False
        else:
            conn_failed = login.ConnectionFailedResponse(k_element)
            if self.kik_node is not None:
                self.logger.error(
                    f" Authentication failed {conn_failed.message}, trying to logger in with user/password.")
                self.kik_node = None
                self._connect()
            else:
                self.callback.on_connection_failed(conn_failed)

    def _handle_received_iq_element(self, iq_element: BeautifulSoup):
        """
        The 'iq' (info/query) stanzas in XMPP represents the request/ response elements.
        We send an iq stanza to request for information, and we receive an iq stanza in response to this request,
        with the same ID attached to it.
        For a great explanation of this stanza: http://slixmpp.readthedocs.io/api/stanza/iq.html

        :param iq_element: The iq XML element we just received from kik.
        """
        if iq_element.error and "bad-request" in dir(iq_element.error):
            if "bad-request" in dir(iq_element.error):
                raise Exception(f'Received a Bad Request error for stanza with ID {iq_element.attrs["id"]}')
            if iq_element.error.find("service-unavailable"):
                # Service unavailable 5xx error.
                xmlns_handlers.ServiceRequestErrorHandler(self.callback, self).handle(iq_element)
                return

        query = iq_element.query
        if query is not None and hasattr(query, 'attrs'):
            xml_namespace = query['xmlns'] if 'xmlns' in query.attrs else query['xmlns:']
            self._handle_response(xml_namespace, iq_element)

    def _handle_response(self, xmlns, iq_element):
        """
        Handles a response that we receive from kik after our initiated request.
        Examples: response to a group search, response to fetching roster, etc.

        :param xmlns: The XML namespace that helps us understand what type of response this is
        :param iq_element: The actual XML element that contains the response
        """
        if xmlns == 'kik:iq:check-unique':
            xmlns_handlers.CheckUsernameUniqueResponseHandler(self.callback, self).handle(iq_element)
        elif xmlns == 'jabber:iq:register':
            xmlns_handlers.RegisterOrLoginResponseHandler(self.callback, self).handle(iq_element)
        elif xmlns == 'jabber:iq:roster':
            xmlns_handlers.RosterResponseHandler(self.callback, self).handle(iq_element)
        elif xmlns in ['kik:iq:friend', 'kik:iq:friend:batch']:
            xmlns_handlers.PeersInfoResponseHandler(self.callback, self).handle(iq_element)
        elif xmlns == 'kik:iq:xiphias:bridge':
            xmlns_handlers.XiphiasHandler(self.callback, self).handle(iq_element)
        elif xmlns == 'kik:auth:cert':
            self.authenticator.handle(iq_element)
        elif xmlns == 'kik:iq:QoS':
            xmlns_handlers.HistoryHandler(self.callback, self).handle(iq_element)
        elif xmlns == 'kik:iq:user-profile':
            xmlns_handlers.UserProfileHandler(self.callback, self).handle(iq_element)

    def _handle_xmpp_message(self, xmpp_message: BeautifulSoup):
        """
        an XMPP 'message' in the case of Kik is the actual stanza we receive when someone sends us a message
        (weather groupchat or not), starts typing, stops typing, reads our message, etc.
        Examples: http://slixmpp.readthedocs.io/api/stanza/message.html

        :param xmpp_message: The XMPP 'message' element we received
        """
        self._handle_kik_event(xmpp_message)

    def _handle_kik_event(self, xmpp_element):
        """
        Handles kik "push" events, like a new message that arrives.

        :param xmpp_element: The XML element that we received with the information about the event
        """
        if "xmlns" in xmpp_element.attrs:
            # The XML namespace is different for iOS and Android, handle the messages with their actual type
            if xmpp_element['type'] == "chat":
                xmlns_handlers.XMPPMessageHandler(self.callback, self).handle(xmpp_element)
            elif xmpp_element['type'] == "groupchat":
                xmlns_handlers.GroupXMPPMessageHandler(self.callback, self).handle(xmpp_element)
            elif xmpp_element['type'] == "receipt":
                if xmpp_element.g:
                    self.callback.on_group_receipts_received(chatting.IncomingGroupReceiptsEvent(xmpp_element))
                else:
                    xmlns_handlers.XMPPMessageHandler(self.callback, self).handle(xmpp_element)
            elif xmpp_element['type'] == "is-typing":
                # some clients send is-typing this way?
                xmlns_handlers.XMPPMessageHandler(self.callback, self).handle(xmpp_element)
            elif xmpp_element['type'] == "error":
                # error type happens on KIK jail (Restricted Group Access)
                pass
            else:
                self.logger.warning(f'Received unknown XMPP element type: {xmpp_element}')
        else:
            # iPads send messages without xmlns, try to handle it as jabber:client
            xmlns_handlers.XMPPMessageHandler(self.callback, self).handle(xmpp_element)

    def _on_connection_lost(self):
        """
        Gets called when the connection to kik's servers is (unexpectedly) lost.
        It could be that we received a connection reset packet for example.
        :return:
        """
        self.connected = False
        if not self.is_expecting_connection_reset:
            self.logger.warning("The connection was unexpectedly lost")

        self.is_expecting_connection_reset = False

    def _kik_connection_thread_function(self):
        """
        The Kik Connection thread main function.
        Initiates the asyncio loop and actually connects.
        """

        # If there is already a connection going, than wait for it to stop
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.connection.close)
            self.logger.debug("Waiting for the previous connection to stop.")
            while self.loop.is_running():
                self.logger.warning("Still Waiting for the previous connection to stop.")
                time.sleep(1)

        self.logger.info("Initiating the Kik Connection thread and connecting to kik server...")

        # create the connection and launch the asyncio loop
        self.connection = KikConnection(self.loop, self)
        connection_coroutine = self.loop.create_connection(lambda: self.connection, HOST, PORT, ssl=True)
        self.loop.run_until_complete(connection_coroutine)

        self.logger.debug("Running main loop")
        self.loop.run_forever()
        self.logger.debug("Main loop ended.")
        self.callback.on_disconnected()

    def get_jid(self, username_or_jid):
        if '@' in username_or_jid:
            # this is already a JID.
            return username_or_jid
        username = username_or_jid

        # first search if we already have it
        if self.get_jid_from_cache(username) is None:
            # go request for it

            self._new_user_added_event.clear()
            self.request_info_of_users(username)
            if not self._new_user_added_event.wait(5.0):
                raise TimeoutError(f"Could not get the JID for username {username} in time")

        return self.get_jid_from_cache(username)

    def get_jid_from_cache(self, username):
        for user in self._known_users_information:
            if user.username.lower() == username.lower():
                return user.jid

        return None

    @staticmethod
    def is_group_jid(jid):
        if '@talk.kik.com' in jid:
            return False
        elif '@groups.kik.com' in jid:
            return True
        else:
            raise exceptions.KikApiException('Not a valid jid')


class KikConnection(Protocol):
    def __init__(self, loop, api: KikClient):
        self.api = api
        self.loop = loop
        self.data_array = []
        self.partial_data_start_tag = None  # type: str
        self.transport = None  # type: Transport
        self.logger = api.logger
        self.cleanup_interval = 60  # Timeout in seconds for cleaning up the buffer
        self.cleanup_task = None

    def connection_made(self, transport: Transport):
        self.transport = transport
        self.logger.info("Connected.")
        self.api._on_connection_made()

    def data_received(self, data: bytes):
        """
        Handles the reception of new data packets and orchestrates the appropriate actions based on their contents.
        """

        self.logger.debug("Received raw data: %s", data)

        # Handle empty packets
        if data == b" ":
            self.loop.call_soon_threadsafe(self.api._on_new_data_received, data)
            return

        is_multipacket, is_start, tag = self.analyze_and_parse_packet(data)

        if not is_multipacket:
            # split elements if there is more than one
            # send each elements through
            elements = self.split_elements(data)
            for el in elements:
                self.loop.call_soon_threadsafe(self.api._on_new_data_received, el)
        else:
            # Add incoming data to buffer for further processing
            self.data_array.append((time.time(), tag, is_start, data))

            self.process_partial_data()

        if not self.cleanup_task:
            self.cleanup_task = self.loop.call_later(self.cleanup_interval, self.cleanup_buffer)

    @staticmethod
    def split_elements(data_bytes):
        """split data packet in to groups of elements"""
        # element patterns
        element_patterns = [
            b'<k .*?>',
            b'<pong/>',
            b'<iq .*?>.*?</iq>',
            b'<stc .*?>.*?</stc>',
            b'<ack .*?/>',
            b'<message .*?>.*?</message>'
        ]
        elements = []
        for pattern in element_patterns:
            matches = re.findall(pattern, data_bytes, re.DOTALL)
            elements.extend(matches)
            for match in matches:
                data_bytes = data_bytes.replace(match, b'', 1)

        return elements

    def process_partial_data(self):
        to_remove = set()  # Use a set to avoid duplicate indexes
        i = 0

        while i < len(self.data_array):
            timestamp, tag, is_start, packet_data = self.data_array[i]

            if not is_start:
                if i == 0:  # Handle stray end tags at the beginning
                    to_remove.add(i)
                i += 1
                continue

            # Start tag processing
            combined_data = packet_data
            combined = False  # Flag to check if combination happened

            # Check for the next packet
            if i + 1 < len(self.data_array):
                _, next_tag, next_is_start, next_packet_data = self.data_array[i + 1]

                if not next_is_start and tag == next_tag:
                    combined_data += next_packet_data
                    combined = True

            # Process combined data
            if combined:
                elements = self.split_elements(combined_data)
                for el in elements:
                    if self.is_valid_xml(el):
                        self.loop.call_soon_threadsafe(self.api._on_new_data_received, el)

                # Mark both packets for removal
                to_remove.add(i)
                to_remove.add(i + 1)
                i += 2
            else:
                i += 1

        # Cleanup processed data entries
        for index in sorted(to_remove, reverse=True):
            del self.data_array[index]

    @staticmethod
    def is_valid_xml(data: bytes) -> bool:
        """Checks if the given data forms a valid XML."""
        try:
            element_tree.fromstring(data)
            return True
        except element_tree.ParseError:
            return False

    @staticmethod
    def analyze_and_parse_packet(data: bytes) -> (bool, bool, str):
        """
        Analyzes a data packet to determine if it's multi-packet and if it's a start tag.
        It also parses and returns the tag present in the data packet.

        Returns:
            tuple: A tuple where:
                - The first value is a boolean indicating if it's a multi-packet.
                - The second value is a boolean indicating if it's a start tag.
                - The third value is the tag name present in the data packet.
        """
        is_multi = False
        is_start = False
        tag = ""

        # Check for multi-packet
        if data.startswith(b'<') and not data.endswith(b'>'):
            is_multi = True
            is_start = True
            # Potential end or middle of multi-packet sequence
        elif not data.startswith(b'<') and data.endswith(b'>'):
            is_multi = True

        # Parse tag
        if is_start and is_multi:
            # For start tag
            start_pos = data.find(b'<')
            end_pos_space = data.find(b' ', start_pos)
            end_pos_bracket = data.find(b'>', start_pos)

            if end_pos_space == -1:
                end_pos = end_pos_bracket
            elif end_pos_bracket == -1:
                end_pos = end_pos_space
            else:
                end_pos = min(end_pos_space, end_pos_bracket)

            if start_pos != -1 and end_pos != -1:
                tag = data[start_pos + 1:end_pos].decode('utf-8')

        elif not is_start and is_multi:
            # For end tag
            start_pos = data.rfind(b'</')
            end_pos = data.find(b'>', start_pos)

            if start_pos != -1 and end_pos != -1:
                tag = data[start_pos + 2:end_pos].decode('utf-8')

        return is_multi, is_start, tag

    def cleanup_buffer(self):
        # This method is called after the cleanup_interval to remove outdated data from the buffer
        current_time = time.time()
        cleaned_count = len(self.data_array)  # Initialize a counter for cleaned messages

        self.logger.debug(f"Cleaning up partial data buffer: Total - {cleaned_count}")
        self.data_array = [(ts, data) for (ts, data) in self.data_array if current_time - ts <= self.cleanup_interval]

        # Calculate the number of messages cleaned
        cleaned_count = cleaned_count - len(self.data_array)

        self.cleanup_task = None

        self.logger.debug(f"Cleaned up partial data: Removed {cleaned_count} messages.")

    def connection_lost(self, exception):
        if self.cleanup_task:
            self.cleanup_task.cancel()
        self.logger.debug("KikConnection: Lost Connection")
        self.loop.call_soon_threadsafe(self.api._on_connection_lost)
        self.loop.stop()

    def send_raw_data(self, data: bytes):
        self.logger.debug("Sending raw data: %s", data)
        self.transport.write(data)

    def close(self):
        if self.transport:
            self.transport.write(b'</k>')
