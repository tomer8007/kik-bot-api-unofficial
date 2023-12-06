import logging

from bs4 import BeautifulSoup

from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.account import GetMyProfileResponse, GetMutedConvosResponse
from kik_unofficial.datatypes.xmpp.chatting import IncomingChatMessage, \
    IncomingGroupChatMessage, IncomingFriendAttribution, IncomingGroupStatus, IncomingGroupIsTypingEvent, \
    IncomingStatusResponse, IncomingGroupSticker, IncomingGroupSysmsg, IncomingImageMessage, IncomingGifMessage, \
    IncomingVideoMessage, IncomingCardMessage
from kik_unofficial.datatypes.xmpp.errors import SignUpError, LoginError
from kik_unofficial.datatypes.xmpp.history import HistoryResponse
from kik_unofficial.datatypes.xmpp.login import LoginResponse
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse, FriendBatchResponse, QueryUserByUsernameResponse
from kik_unofficial.datatypes.xmpp.sign_up import RegisterResponse, UsernameUniquenessResponse
from kik_unofficial.datatypes.xmpp.xiphias import UsersResponse, UsersByAliasResponse, GroupSearchResponse
from kik_unofficial.utilities.parsing_utilities import get_text_safe

log = logging.getLogger('kik_unofficial')


class XmppHandler:
    def __init__(self, callback: KikClientCallback, client):
        self.callback = callback
        self.client = client

    def handle(self, data: BeautifulSoup):
        raise NotImplementedError


class XMPPChatMessageHandler(XmppHandler):
    def handle(self, data: BeautifulSoup):
        # We received a chat message.
        if data.find('content', recursive=False):
            self.handle_content(data)
        elif get_text_safe(data, 'body'):
            # regular text message
            self.callback.on_chat_message_received(IncomingChatMessage(data))
        elif data.find('friend-attribution', recursive=False):
            # friend attribution
            self.callback.on_friend_attribution(IncomingFriendAttribution(data))
        elif data.find('status', recursive=False):
            # status
            self.callback.on_status_message_received(IncomingStatusResponse(data))
        elif data.find('xiphias-mobileremote-call', recursive=False):
            # this is usually a Play Integrity request
            mobile_remote_call = data.find('xiphias-mobileremote-call', recursive=False)
            log.warning(
               f"[!] Received mobile-remote-call with method '{mobile_remote_call['method']}' of service '{mobile_remote_call['service']}'"
            )
        else:
            log.debug(f"[-] Received unknown chat message. contents: {str(data)}")

    def handle_content(self, data: BeautifulSoup):
        content = data.content
        app_id = content['app-id']
        if app_id == 'com.kik.cards':
            self.callback.on_card_received(IncomingCardMessage(data))
        elif app_id in ['com.kik.ext.gallery', 'com.kik.ext.camera']:
            self.callback.on_image_received(IncomingImageMessage(data))
        elif app_id == 'com.kik.ext.gif':
            self.callback.on_gif_received(IncomingGifMessage(data))
        elif app_id == 'com.kik.ext.stickers':
            self.callback.on_group_sticker(IncomingGroupSticker(data))
        elif app_id in ['com.kik.ext.video-camera', 'com.kik.ext.video-gallery']:
            self.callback.on_video_received(IncomingVideoMessage(data))
        else:
            log.debug(f"[-] Received unknown content message. contents: {str(data)}")


class XMPPGroupChatMessageHandler(XMPPChatMessageHandler):
    def handle(self, data: BeautifulSoup):
        if data.find('content', recursive=False):
            self.handle_content(data)
        elif get_text_safe(data, 'body'):
            self.callback.on_group_message_received(IncomingGroupChatMessage(data))
        elif data.find('is-typing', recursive=False):
            self.callback.on_group_is_typing_event_received(IncomingGroupIsTypingEvent(data))
        elif data.find('status', recursive=False):
            self.callback.on_group_status_received(IncomingGroupStatus(data))
        elif data.find('sysmsg', recursive=False):
            self.callback.on_group_sysmsg_received(IncomingGroupSysmsg(data))
        else:
            log.debug(f"[-] Received unknown group message. contents: {str(data)}")


class HistoryHandler(XmppHandler):
    def handle(self, data: BeautifulSoup):
        if data.find('query', recursive=False).find('history', recursive=False) is not None:
            self.callback.on_message_history_response(HistoryResponse(data))


class UserProfileHandler(XmppHandler):
    def handle(self, data: BeautifulSoup):
        # this will ignore results for other requests
        # like email change that also use the kik:iq:user-profile namespace
        if data.find('query', recursive=False).find('username', recursive=False):
            self.callback.on_get_my_profile_response(GetMyProfileResponse(data))


class MutedConvosHandler(XmppHandler):
    def handle(self, data: BeautifulSoup):
        convo_elements = data.find('query', recursive=False).find_all('convo', recursive=False)
        if convo_elements and len(convo_elements) > 0:
            convos = []
            for convo in convo_elements:
                jid = convo['jid']
                muted = convo.find('muted', recursive=False)
                muted_until = int(muted['expires']) if convo and 'expires' in convo.attrs else None
                convos.append(GetMutedConvosResponse.MutedConvo(jid, muted_until))

            self.callback.on_muted_convos_received(GetMutedConvosResponse(data, convos))


class CheckUsernameUniqueResponseHandler(XmppHandler):
    def handle(self, data: BeautifulSoup):
        self.callback.on_username_uniqueness_received(UsernameUniquenessResponse(data))


class RegisterOrLoginResponseHandler(XmppHandler):
    def handle(self, data: BeautifulSoup):
        message_type = data['type']

        if message_type == "error":
            if data.find('email'):
                # sign up
                sign_up_error = SignUpError(data)
                log.info(f"[-] Register error: {sign_up_error}")
                self.callback.on_register_error(sign_up_error)

            else:
                login_error = LoginError(data)
                log.info(f"[-] Login error: {login_error}")
                self.callback.on_login_error(login_error)

        elif message_type == "result":
            if data.find('email'):
                # login successful
                response = LoginResponse(data)
                self.client.username = response.username
                self.client.kik_node = response.kik_node
                self.client.kik_email = response.email
                log.info(f"[+] Logged in as {response.username}")
                self.callback.on_login_ended(response)
            else:
                # sign up successful
                response = RegisterResponse(data)
                log.info("[+] Registered.")
                self.callback.on_sign_up_ended(response)
                
            self.client._establish_authenticated_session(response.kik_node)


class RosterResponseHandler(XmppHandler):
    def handle(self, data: BeautifulSoup):
        self.callback.on_roster_received(FetchRosterResponse(data))


class PeersInfoResponseHandler(XmppHandler):
    def handle(self, data: BeautifulSoup):
        query = data.find('query', recursive=False)
        xmlns = query['xmlns']
        if xmlns == 'kik:iq:friend' and query.find('item', recursive=False):
            peers_info = QueryUserByUsernameResponse(data)
        elif xmlns == 'kik:iq:friend:batch':
            peers_info = FriendBatchResponse(data)
        else:
            return

        # add this user to the list of known users if it wasn't encountered before
        for peer_info in peers_info.users:
            self.client._known_users_information.add(peer_info)
        self.client._new_user_added_event.set()

        self.callback.on_peer_info_received(peers_info)


class XiphiasHandler(XmppHandler):
    def handle(self, data: BeautifulSoup):
        method = data.query['method']
        if method == 'GetUsers':
            self.callback.on_xiphias_get_users_response(UsersResponse(data))
        elif method == 'GetUsersByAlias':
            self.callback.on_xiphias_get_users_response(UsersByAliasResponse(data))
        elif method == 'FindGroups':
            self.callback.on_group_search_response(GroupSearchResponse(data))
        else:
            # TODO handle other methods when they are added to the client
            pass
