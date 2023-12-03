import asyncio
import ssl
import time
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
from kik_unofficial.utilities.threading_utils import run_in_new_thread
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement
from kik_unofficial.content import profile_pictures, content
from kik_unofficial.utilities.credential_utilities import random_device_id, random_android_id
from kik_unofficial.utilities.logging_utils import set_up_basic_logging

HOST, PORT = "talk1110an.kik.com", 5223


class KikClient:
    """
    The main kik class with which you're managing a kik connection and sending commands
    """

    def __init__(self, callback: callbacks.KikClientCallback, kik_username: str, kik_password: str,
                 kik_node: str = None, device_id: str = None, android_id: str = random_android_id(), log_level: int = 1,
                 enable_logging: bool = False, log_file_path: str = None, disable_auth_cert: bool = False) -> None:
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
        :param enable_logging: If true, turns on logging to stdout (default: False)
        :param log_file_path: If set will create a daily rotated log file and archive for 7 days.
        :param disable_auth_cert: If true, auth certs will not be generated on every connection. This greatly improves startup time.
        """
        # turn on logging with basic configuration
        if enable_logging:
            self.log = set_up_basic_logging(log_level=log_level, logger_name="kik_unofficial", log_file_path=log_file_path)

        self.username = kik_username
        self.password = kik_password
        self.kik_node = kik_node
        self.kik_email = None
        self.device_id = device_id
        self.android_id = android_id

        self.callback = callback
        self.authenticator = AuthStanza(self)

        self.connected = False
        self.authenticated = False
        self.connection = None
        self.is_expecting_connection_reset = False
        self.is_permanent_disconnection = False
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self._known_users_information = set()
        self._new_user_added_event = Event()

        self.should_login_on_connection = kik_username is not None and kik_password is not None
        self.disable_auth_cert = disable_auth_cert
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
                f"Establishing authenticated connection using kik node '{self.kik_node}', device id '{self.device_id}' and android id '{self.android_id}'...")

            message = login.EstablishAuthenticatedSessionRequest(self.kik_node, self.username, self.password,
                                                                 self.device_id)
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
        login_type = "email" if '@' in self.username else "username"
        self.log.info(f"Logging in with {login_type} '{username}' and a given password {'*' * len(password)}...")
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
        self.log.info(f"Sending sign up request (name: {first_name} {last_name}, email: {email})...")
        return self._send_xmpp_element(register_message)

    def request_roster(self, is_big=True, timestamp=None):
        """
        Requests the list of chat partners (people and groups). This is called roster in XMPP terms.
        """
        self.log.info("Requesting roster (list of chat partners)...")
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
            self.log.info(f"Sending chat message '{message}' to group '{peer_jid}'...")
            return self._send_xmpp_element(chatting.OutgoingGroupChatMessage(peer_jid, message, bot_mention_jid))
        else:
            self.log.info(f"Sending chat message '{message}' to user '{peer_jid}'...")
            return self._send_xmpp_element(chatting.OutgoingChatMessage(peer_jid, message, False, bot_mention_jid))

    def send_chat_image(self, peer_jid: str, file, forward=True):
        """
        Sends an image chat message to another person or a group with the given JID/username.
        :param peer_jid: The Jabber ID for which to send the message (looks like username_ejs@talk.kik.com)
                         If you don't know the JID of someone, you can also specify a kik username here.
        :param file: The path to the image file OR its bytes OR an IOBase object to send.
        """
        peer_jid = self.get_jid(peer_jid)

        if self.is_group_jid(peer_jid):
            self.log.info(f"Sending chat image to group '{peer_jid}'...")
            imageRequest = chatting.OutgoingGroupChatImage(peer_jid, file, forward)
        else:
            self.log.info(f"Sending chat image to user '{peer_jid}'...")
            imageRequest = chatting.OutgoingChatImage(peer_jid, file, False, forward)
        content.upload_gallery_image(
            imageRequest,
            f'{self.kik_node}@talk.kik.com',
            self.username,
            self.password,
        )
        return self._send_xmpp_element(imageRequest)

    def send_read_receipt(self, peer_jid: str, receipt_message_id: str, group_jid=None):
        """
        Sends a read receipt for a previously sent message, to a specific user or group.

        :param peer_jid: The JID of the user to which to send the receipt.
        :param receipt_message_id: The message ID that the receipt is sent for
        :param group_jid If the receipt is sent for a message that was sent in a group,
                         this parameter should contain the group's JID
        """
        self.log.info(f"Sending read receipt to JID {peer_jid} for message ID {receipt_message_id}")
        return self._send_xmpp_element(chatting.OutgoingReadReceipt(peer_jid, receipt_message_id, group_jid))

    def send_delivered_receipt(self, peer_jid: str, receipt_message_id: str, group_jid: str = None):
        """
        Sends a receipt indicating that a specific message was received, to another person.

        :param peer_jid: The other peer's JID to send to receipt to
        :param receipt_message_id: The message ID for which to generate the receipt
        :param group_jid: The group's JID, in case the receipt is sent in a group (None otherwise)
        """
        self.log.info(f"Sending delivered receipt to JID {peer_jid} for message ID {receipt_message_id}")
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
    def send_gif_image(self, peer_jid: str, search_term: str, API_key: str):
        """
        Sends a GIF image to another person or a group with the given JID/username.
        The GIF is taken from tendor.com, based on search keywords.
        :param peer_jid: The Jabber ID for which to send the message (looks like username_ejs@talk.kik.com
        :param search_term: The search term to use when searching GIF images on tendor.com
        :param API_key: The API key for tenor (Get one from https://developers.google.com/tenor/)
        """
        if self.is_group_jid(peer_jid):
            self.log.info(f"Sending a GIF message to group '{peer_jid}'...")
            return self._send_xmpp_element(chatting.OutgoingGIFMessage(peer_jid, search_term, API_key, True))
        else:
            self.log.info(f"Sending a GIF message to user '{peer_jid}'...")
            return self._send_xmpp_element(chatting.OutgoingGIFMessage(peer_jid, search_term, API_key, False))

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
        return self._send_xmpp_element(roster.AddFriendRequest(peer_jid))

    def remove_friend(self, peer_jid):
        return self._send_xmpp_element(roster.RemoveFriendRequest(peer_jid))

    def send_link(self, peer_jid, link, title, text='', app_name='Webpage'):
        return self._send_xmpp_element(chatting.OutgoingLinkShareEvent(peer_jid, link, title, text, app_name))

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
        self.log.info(f"Requesting a group name change for JID {group_jid} to '{new_name}'")
        return self._send_xmpp_element(group_adminship.ChangeGroupNameRequest(group_jid, new_name))

    def add_peer_to_group(self, group_jid, peer_jid):
        """
        Adds someone to a group

        :param group_jid: The JID of the group into which to add a user
        :param peer_jid: The JID of the user to add
        """
        self.log.info(f"Requesting to add user {peer_jid} into the group {group_jid}")
        return self._send_xmpp_element(group_adminship.AddToGroupRequest(group_jid, peer_jid))

    def remove_peer_from_group(self, group_jid, peer_jid):
        """
        Kicks someone out of a group

        :param group_jid: The group JID from which to remove the user
        :param peer_jid: The JID of the user to remove
        """
        self.log.info(f"Requesting removal of user {peer_jid} from group {group_jid}")
        return self._send_xmpp_element(group_adminship.RemoveFromGroupRequest(group_jid, peer_jid))

    def ban_member_from_group(self, group_jid, peer_jid):
        """
        Bans a member from the group

        :param group_jid: The JID of the relevant group
        :param peer_jid: The JID of the user to ban
        """
        self.log.info(f"Requesting ban of user {peer_jid} from group {group_jid}")
        return self._send_xmpp_element(group_adminship.BanMemberRequest(group_jid, peer_jid))

    def unban_member_from_group(self, group_jid, peer_jid):
        """
        Undos a ban of someone from a group

        :param group_jid: The JID of the relevant group
        :param peer_jid: The JID of the user to un-ban from the gorup
        """
        self.log.info(f"Requesting un-banning of user {peer_jid} from the group {group_jid}")
        return self._send_xmpp_element(group_adminship.UnbanRequest(group_jid, peer_jid))

    def join_group_with_token(self, group_hashtag, group_jid, join_token):
        """
        Tries to join into a specific group, using a cryptographic token that was received earlier from a search

        :param group_hashtag: The public hashtag of the group into which to join (like '#Music')
        :param group_jid: The JID of the same group
        :param join_token: a token that can be extracted in the callback on_group_search_response, after calling
                           search_group()
        """
        self.log.info(f"Trying to join the group '{group_hashtag}' with JID {group_jid}")
        return self._send_xmpp_element(roster.GroupJoinRequest(group_hashtag, join_token, group_jid))

    def leave_group(self, group_jid):
        """
        Leaves a specific group

        :param group_jid: The JID of the group to leave
        """
        self.log.info(f"Leaving group {group_jid}")
        return self._send_xmpp_element(group_adminship.LeaveGroupRequest(group_jid))

    def promote_to_admin(self, group_jid, peer_jid):
        """
        Turns some group member into an admin

        :param group_jid: The group JID for which the member will become an admin
        :param peer_jid: The JID of user to turn into an admin
        """
        self.log.info(f"Promoting user {peer_jid} to admin in group {group_jid}")
        return self._send_xmpp_element(group_adminship.PromoteToAdminRequest(group_jid, peer_jid))

    def demote_admin(self, group_jid, peer_jid):
        """
        Turns an admin of a group into a regular user with no amidships capabilities.

        :param group_jid: The group JID in which the rights apply
        :param peer_jid: The admin user to demote
        :return:
        """
        self.log.info(f"Demoting user {peer_jid} to a regular member in group {group_jid}")
        return self._send_xmpp_element(group_adminship.DemoteAdminRequest(group_jid, peer_jid))

    def add_members(self, group_jid, peer_jids: Union[str, List[str]]):
        """
        Adds multiple users to a specific group at once

        :param group_jid: The group into which to join the users
        :param peer_jids: a list (or a single string) of JIDs to add to the group
        """
        self.log.info(f"Adding some members to the group {group_jid}")
        return self._send_xmpp_element(group_adminship.AddMembersRequest(group_jid, peer_jids))

    # ----------------------
    # Other Operations
    # ----------------------

    def send_ack(self, sender_jid, is_receipt: bool, message_id, group_jid=None):
        """
        Sends an acknowledgement for a provided message ID
        """
        self.log.info(f"Sending acknowledgement for message ID {message_id}")
        return self._send_xmpp_element(history.OutgoingAcknowledgement(sender_jid, is_receipt, message_id, group_jid))

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
        return self._send_xmpp_element(roster.GroupSearchRequest(search_query))

    def check_username_uniqueness(self, username):
        """
        Checks if the given username is available for registration.
        Results are returned in the on_username_uniqueness_received() callback

        :param username: The username to check for its existence
        """
        self.log.info(f"Checking for Uniqueness of username '{username}'")
        return self._send_xmpp_element(sign_up.CheckUsernameUniquenessRequest(username))

    def set_profile_picture(self, filename):
        """
        Sets the profile picture of the current user

        :param filename: The path to the file OR its bytes OR an IOBase object to set
        """
        self.log.info(f"Setting the profile picture to file '{filename}'")
        profile_pictures.set_profile_picture(
            filename, f'{self.kik_node}@talk.kik.com', self.username, self.password
        )

    def set_background_picture(self, filename):
        """
        Sets the background picture of the current user

        :param filename: The path to the image file OR its bytes OR an IOBase object to set
        """
        self.log.info(f"Setting the background picture to filename '{filename}'")
        profile_pictures.set_background_picture(
            filename, f'{self.kik_node}@talk.kik.com', self.username, self.password
        )

    def send_ping(self):
        """
               Sends Ping Stanza A response Pong Should return from the server
               Pong Object will include round trip time
        """
        self.log.info(f'Sending KIK servers a ping.')
        return self._send_xmpp_element(chatting.KikPingRequest())

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

    def change_email(self, old_email, new_email):
        """
        Changes the email of the current account

        :param old_email: The current email
        :param new_email: The new email to set
        """
        self.log.info(f"Changing account email to '{new_email}'")
        return self._send_xmpp_element(account.ChangeEmailRequest(self.password, old_email, new_email))

    def disconnect(self, permanent: bool = True):
        """
        Closes the connection to Kik.

        If the current connection is already closed or closing, this is a no-op.

        :permanent: if True, the client will not reconnect and future attempts to reconnect will fail.
        """
        if not self.connection or self.connection.is_closed:
            return

        self.log.warning("Disconnecting.")
        self.connection.close()
        self.is_expecting_connection_reset = True
        self.is_permanent_disconnection = True if self.is_permanent_disconnection else permanent

        # self.loop.call_soon(self.loop.stop)

    # -----------------
    # Internal methods
    # -----------------

    def _send_xmpp_element(self, message: XMPPElement):
        """
        Serializes and sends the given XMPP element to kik servers
        :param xmpp_element: The XMPP element to send
        :return: The UUID of the element that was sent
        """
        while not self.connected:
            self.log.debug("Waiting for connection.")
            time.sleep(0.1)
        if type(message.serialize()) is list:
            self.log.debug("Sending multi packet data.")
            packets = message.serialize()
            for p in packets:
                self.loop.call_soon_threadsafe(self.connection.send_raw_data, p)
        else:
            self.loop.call_soon_threadsafe(self.connection.send_raw_data, message.serialize())

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
        elif xml_element.name == 'stc':
            if xml_element.stp['type'] == 'ca':
                self.callback.on_captcha_received(login.CaptchaElement(xml_element))
            elif xml_element.stp['type'] == 'bn':
                self.callback.on_temp_ban_received(login.TempBanElement(xml_element))
            else:
                self.log.warning(f'Unknown stc element type: {xml_element["type"]}')
        elif xml_element.name == 'ack':
            pass
        elif xml_element.name == 'pong':
            self.callback.on_pong(chatting.KikPongResponse(xml_element))
        else:
            self.log.warning(f'Unknown element type: {xml_element.name}')

    def _handle_received_k_element(self, k_element: BeautifulSoup) -> bool:
        """
        The 'k' element appears to be kik's connection-related stanza.
        It lets us know if a connection or a login was successful or not.

        :param k_element: The XML element we just received from kik.
        :return: true if connection succeeded
        """
        connected = k_element['ok'] == "1"

        if connected:
            self.connected = True

            if 'ts' in k_element.attrs:
                # authenticated!
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
        if iq_element.error and "bad-request" in dir(iq_element.error):
            if "bad-request" in dir(iq_element.error):
                raise Exception(f'Received a Bad Request error for stanza with ID {iq_element.attrs["id"]}')
            if iq_element.error.find("service-unavailable"):
                raise Exception(f'Received a service Unavailable error for stanza with ID {iq_element.attrs["id"]}')

        query = iq_element.query
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
                self.log.warning(f'Received unknown XMPP element type: {xmpp_element}')
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
            self.log.warning("The connection was unexpectedly lost")

        self.is_expecting_connection_reset = False

    def _kik_connection_thread_function(self):
        """
        The Kik Connection thread main function.
        Initiates the asyncio loop and actually connects.
        """
        # If there is already a connection going, then wait for it to stop
        if self.connection and not self.connection.is_closed:
            self.loop.call_soon_threadsafe(self.connection.close)
            self.log.debug("Waiting for the previous connection to stop.")
            while not self.connection.is_closed:
                self.log.debug("Still waiting for the previous connection to stop.")
                time.sleep(1)

        self.log.info("Initiating the Kik Connection thread and connecting to kik server...")

        # create the connection and launch the asyncio loop
        self.connection = KikConnection(self)
        task = self.loop.create_task(self.connection.main_loop())

        self.loop.run_until_complete(task)
        self.log.debug("Main loop ended.")
        self.callback.on_disconnected()
        self._connect()

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
    def is_group_jid(jid: str) -> bool:
        if jid is None or len(jid) != 30:
            return False
        if not jid.endswith('_g@groups.kik.com'):
            return False
        group_id = jid[0:13]
        print(group_id)
        if not group_id.isdigit():
            return False

        group_number = int(group_id)
        # See XiGid in protobuf docs for an explanation
        return 1099511627776 <= group_number <= 2199023255551


class KikConnection:
    def __init__(self, api: KikClient):
        self.api = api
        self.loop = self.api.loop
        self.reader = None  # type: StreamReader
        self.writer = None  # type: StreamWriter
        self.log = api.log
        self.is_closed = False

    async def main_loop(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(host=HOST, port=PORT, ssl=ssl.create_default_context())
            self.log.info("Connected.")
            self.api._on_connection_made()

            parser = KikXmlParser(self.reader, self.log)

            k = await parser.read_initial_k()
            self.log.debug("%s bind: %s", self.api.username, k)

            if not self.api._handle_received_k_element(k):
                self.api.is_expecting_connection_reset = True
                return

            while True:
                stanza = await parser.read_next_stanza()
                self.log.debug("Received: %s", stanza)
                self.loop.call_soon_threadsafe(self.api._on_new_stanza_received, stanza)
        except Exception as e:
            self.log.warning("Received error in main loop: %s", e)
        finally:
            self.is_closed = True
            self.api._on_connection_lost()

    def send_raw_data(self, data: bytes):
        if not self.writer:
            self.log.error("Can't send raw data, writer not instantiated: %s", data)
        elif self.writer.is_closing():
            self.log.error("Can't send raw data, stream is closed or closing: %s", data)
        else:
            self.log.debug("Sending raw data: %s", data)
            self.writer.write(data)

    def close(self):
        if self.writer and not self.writer.is_closing():
            self.writer.write(b'</k>')
            self.writer.close()

