import logging

from bs4 import BeautifulSoup

from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.chatting import IncomingMessageDeliveredEvent, IncomingMessageReadEvent, IncomingChatMessage, \
    IncomingGroupChatMessage, IncomingFriendAttribution, IncomingGroupStatus, IncomingIsTypingEvent, IncomingGroupIsTypingEvent, \
    IncomingStatusResponse, IncomingGroupSticker, IncomingGroupSysmsg, IncomingImageMessage, IncomingGroupReceiptsEvent, IncomingGifMessage, \
    IncomingVideoMessage, IncomingCardMessage
from kik_unofficial.datatypes.xmpp.errors import SignUpError, LoginError
from kik_unofficial.datatypes.xmpp.login import LoginResponse
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse, PeersInfoResponse, GroupSearchResponse
from kik_unofficial.datatypes.xmpp.sign_up import RegisterResponse, UsernameUniquenessResponse
from kik_unofficial.datatypes.xmpp.xiphias import UsersResponse, UsersByAliasResponse

log = logging.getLogger('kik_unofficial')


class XmppHandler:
    def __init__(self, callback: KikClientCallback, client):
        self.callback = callback
        self.client = client

    def handle(self, data: BeautifulSoup):
        raise NotImplementedError


class XMPPMessageHandler(XmppHandler):
    def handle(self, data: BeautifulSoup):
        if data['type'] == 'chat':

            #
            # We received some sort of a chat message.
            #

            if data.body and data.body.text:
                # regular text message
                self.callback.on_chat_message_received(IncomingChatMessage(data))
            elif data.find('friend-attribution'):
                # friend attribution
                self.callback.on_friend_attribution(IncomingFriendAttribution(data))
            elif data.find('status'):
                # status
                self.callback.on_status_message_received(IncomingStatusResponse(data))
            elif data.find('xiphias-mobileremote-call'):
                # usually SafetyNet-related (?)
                mobile_remote_call = data.find('xiphias-mobileremote-call')
                log.warning("[!] Received mobile-remote-call with method '{}' of service '{}'".format(
                    mobile_remote_call['method'], mobile_remote_call['service']))
            elif data.find('images'):
                # images
                self.callback.on_image_received(IncomingImageMessage(data))
            else:
                # what else? GIFs?
                log.debug("[-] Received unknown chat message. contents: {}".format(str(data)))

        elif data['type'] == 'receipt':
            #
            # We received some sort of a receipt.
            #

            if data.g:
                self.callback.on_group_receipts_received(IncomingGroupReceiptsEvent(data))
            elif data.receipt['type'] == 'delivered':
                self.callback.on_message_delivered(IncomingMessageDeliveredEvent(data))
            else:
                self.callback.on_message_read(IncomingMessageReadEvent(data))

        elif data['type'] == 'is-typing':
            #
            # Some user started to type or stopped to type
            #

            self.callback.on_is_typing_event_received(IncomingIsTypingEvent(data))


        elif data['type'] == 'groupchat':
            #
            # We received some sort of a group chat message.
            #

            if data.body:
                self.callback.on_group_message_received(IncomingGroupChatMessage(data))
            elif data.find('is-typing'):
                self.callback.on_group_is_typing_event_received(IncomingGroupIsTypingEvent(data))
            elif data.find('status'):
                self.callback.on_group_status_received(IncomingGroupStatus(data))
            elif data.find('sysmsg'):
                self.callback.on_group_sysmsg_received(IncomingGroupSysmsg(data))
            else:
                log.debug("[-] Received unknown groupchat message. contents: {}".format(str(data)))
        else:
            log.debug("[-] Received unknown message type. contents: {}".format(str(data)))


class GroupXMPPMessageHandler(XmppHandler):
    def handle(self, data: BeautifulSoup):
        if data.body:
            self.callback.on_group_message_received(IncomingGroupChatMessage(data))
        elif data.find('is-typing'):
            self.callback.on_group_is_typing_event_received(IncomingGroupIsTypingEvent(data))
        elif data.content and 'app-id' in data.content.attrs:
            app_id = data.content['app-id']
            if app_id == 'com.kik.ext.stickers':
                self.callback.on_group_sticker(IncomingGroupSticker(data))
            elif app_id == 'com.kik.ext.gallery':
                self.callback.on_image_received(IncomingImageMessage(data))
            elif app_id == 'com.kik.ext.camera':
                self.callback.on_image_received(IncomingImageMessage(data))
            elif app_id == 'com.kik.ext.gif':
                self.callback.on_gif_received(IncomingGifMessage(data))
            elif app_id == 'com.kik.ext.video-camera':
                self.callback.on_video_received(IncomingVideoMessage(data))
            elif app_id == 'com.kik.ext.video-gallery':
                self.callback.on_video_received(IncomingVideoMessage(data))
            elif app_id == 'com.kik.cards':
                self.callback.on_card_received(IncomingCardMessage(data))

        else:
            log.debug("[-] Received unknown group message. contents: {}".format(str(data)))


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
                log.info("[-] Register error: {}".format(sign_up_error))
                self.callback.on_register_error(sign_up_error)

            else:
                login_error = LoginError(data)
                log.info("[-] Login error: {}".format(login_error))
                self.callback.on_login_error(login_error)

        elif message_type == "result":
            if data.find('email'):
                # login successful
                response = LoginResponse(data)
                self.client.username = response.username
                self.client.kik_node = response.kik_node
                self.client.kik_email = response.email
                log.info("[+] Logged in as {}".format(response.username))
                self.callback.on_login_ended(response)
                self.client._establish_authenticated_session(response.kik_node)
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
        peers_info = PeersInfoResponse(data)

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
        else:  # TODO
            self.callback.on_group_search_response(GroupSearchResponse(data))
