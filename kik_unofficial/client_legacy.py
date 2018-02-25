import base64
import binascii
import hashlib
import hmac
import socket
import ssl
import time
from enum import IntEnum

import rsa
from bs4 import BeautifulSoup

from kik_unofficial.datatypes.exceptions import *
from kik_unofficial.utilities import Utilities
from kik_unofficial.utilities.cryptographics import CryptographicUtils

from kik_unofficial.protobuf import group_search_service_pb2

HOST, PORT = "talk1110an.kik.com", 5223


class DebugLevel(IntEnum):
    VERBOSE = 0,
    WARNING = 1,
    ERROR = 2,


class KikClient:
    debug_level = DebugLevel.VERBOSE
    user_info = None
    jid_cache_list = []  # shared for all instances

    # hardcoded by default
    device_id = "167da12427ee4dc4a36b40e8debafc25"
    kik_version = "11.1.1.12218"
    android_id = "c10d47ba7ee17193"

    def __init__(self, username=None, password=None, debug_level=DebugLevel.VERBOSE):
        self.user_info = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.wrappedSocket = ssl.wrap_socket(self.sock)
        self.debug_level = debug_level
        self.connect_to_kik_server()
        if username is not None and password is not None:
            self.login(username, password)

    def get_user_info(self):
        return self.user_info

    def connect_to_kik_server(self):
        initial_connection_payload = '<k anon="">'.encode('UTF-8')

        self._log("[+] Connecting to kik server...")
        self.wrappedSocket.connect((HOST, PORT))
        self.wrappedSocket.send(initial_connection_payload)
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        if "ok" not in response:
            raise KikErrorException(response, "[-] Could not connect to kik server: " + response)

        self._log("[+] Connected.")

    def login(self, username, password, establish_session_on_success=True):
        self._log("[+] Logging in (username: " + username + ", password: " + password + ")...")

        device_id = self.device_id
        password_key = CryptographicUtils.key_from_password(username, password)
        data = ('<iq type="set" id="{}">'
                '<query xmlns="jabber:iq:register">'
                '<username>{}</username>'
                '<passkey-u>{}</passkey-u>'
                '<device-id>{}</device-id>'
                '<install-referrer>utm_source=google-play&amp;utm_medium=organic</install-referrer>'
                '<operator>310260</operator>'
                '<install-date>1494078709023</install-date>'
                '<device-type>android</device-type>'
                '<brand>generic</brand>'
                '<logins-since-install>1</logins-since-install>'
                '<version>{}</version>'
                '<lang>en_US</lang>'
                '<android-sdk>19</android-sdk>'
                '<registrations-since-install>0</registrations-since-install>'
                '<prefix>CAN</prefix>'
                '<android-id>c10d47ba7ee17193</android-id>'
                '<model>Samsung Galaxy S5 - 4.4.4 - API 19 - 1080x1920</model>'
                '</query>'
                '</iq>').format(CryptographicUtils.make_kik_uuid(), username, password_key, device_id,
                                self.kik_version)
        self._make_request(data)
        response = self._get_response()

        if response.error:
            if response.find('password-mismatch'):
                self._log("[-] Password mismatch, can't login", DebugLevel.ERROR)
                raise KikLoginException(response.error, "Password mismatch")
            elif response.error.find('not-registered'):
                self._log("[-] User not registered, can't login", DebugLevel.ERROR)
                raise KikLoginException(response.error, "Not registered")
            else:
                captcha = response.find('captcha-url')
                if captcha:
                    self._log("[-} Encountered a captcha. URL: " + captcha.string, DebugLevel.ERROR)
                    raise KikCaptchaException(response.error, "Captcha when trying to log in! URL: " + captcha.string,
                                              captcha.string)
                else:
                    self._log("[-] Kik error code: {}".format(response.error['code']), DebugLevel.ERROR)
                    self._log(response.error.prettify(), DebugLevel.ERROR)
                    raise KikLoginException(response.error, "Kik error code: {}".format(response.error['code']))

        if response.find("kik:error"):
            captcha = response.find('captcha-type')
            if captcha:
                self._log("[-} Encountered a captcha. URL: " + captcha.string, DebugLevel.ERROR)
                raise KikLoginException(response, "Captcha! URL:" + captcha.string)

        user_info = dict()
        user_info["node"] = response.find('node').text
        user_info["username"] = response.find('username').text
        user_info["email"] = response.find('email').text
        user_info["first"] = response.find('first').text
        user_info["last"] = response.find('last').text
        pubkey = response.find('record', {'pk': 'messaging_pub_key'})
        if pubkey:
            user_info["public_key"] = pubkey.text
            user_info["private_key"] = response.find('record', {'pk': 'enc_messaging_priv_key'}).text
            if response.find('record', {'pk': 'chat_list_bins'}):
                user_info["chat_list"] = self._parse_chat_list_bin(
                    Utilities.decode_base64(response.find('record', {'pk': 'chat_list_bins'}).text.encode('UTF-8')))

        self._log("[+] Logged in.")
        if self.debug_level == DebugLevel.VERBOSE:
            Utilities.print_dictionary(user_info)

        self.user_info = user_info
        if establish_session_on_success:
            self.establish_session(self.user_info["username"], self.user_info["node"], password)

        return self.user_info

    def establish_session(self, username, node, password):
        self._log("[+] Establishing session...")
        # reset the socket
        self.wrappedSocket.send("</k>".encode('UTF-8'))
        self.wrappedSocket.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.wrappedSocket = ssl.wrap_socket(self.sock)
        self.wrappedSocket.connect((HOST, PORT))

        jid = node + "@talk.kik.com"
        jid_with_resource = jid + "/CAN" + self.device_id
        timestamp = "1496333389122"
        sid = CryptographicUtils.make_kik_uuid()
        version = "11.1.1.12218"

        # some super secret cryptographic stuff
        private_key_pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIBPAIBAAJBANEWUEINqV1KNG7Yie9GSM8t75ZvdTeqT7kOF40kvDHIp" \
                          "/C3tX2bcNgLTnGFs8yA2m2p7hKoFLoxh64vZx5fZykCAwEAAQJAT" \
                          "/hC1iC3iHDbQRIdH6E4M9WT72vN326Kc3MKWveT603sUAWFlaEa5T80GBiP/qXt9PaDoJWcdKHr7RqDq" \
                          "+8noQIhAPh5haTSGu0MFs0YiLRLqirJWXa4QPm4W5nz5VGKXaKtAiEA12tpUlkyxJBuuKCykIQbiUXHEwzFYbMHK5E" \
                          "/uGkFoe0CIQC6uYgHPqVhcm5IHqHM6/erQ7jpkLmzcCnWXgT87ABF2QIhAIzrfyKXp1ZfBY9R0H4pbboHI4uatySKc" \
                          "Q5XHlAMo9qhAiEA43zuIMknJSGwa2zLt/3FmVnuCInD6Oun5dbcYnqraJo=\n-----END RSA PRIVATE KEY----- "
        private_key = rsa.PrivateKey.load_pkcs1(private_key_pem, format='PEM')
        signature = rsa.sign("{}:{}:{}:{}".format(jid, version, timestamp, sid).encode('UTF-8'), private_key, 'SHA-256')
        signature = base64.b64encode(signature, '-_'.encode('UTF-8')).decode('UTF-8')[:-2]
        hmac_data = timestamp + ":" + jid
        hmac_secret_key = CryptographicUtils.build_hmac_key()
        cv = binascii.hexlify(hmac.new(hmac_secret_key, hmac_data.encode('UTF-8'), hashlib.sha1).digest()).decode(
            'UTF-8')

        password_key = CryptographicUtils.key_from_password(username, password)

        the_map = {'from': jid_with_resource, 'to': 'talk.kik.com', 'p': password_key, 'cv': cv, 'v': version,
                   'sid': sid, 'n': '1', 'conn': 'WIFI', 'ts': timestamp, 'lang': 'en_US', 'signed': signature}
        packet = CryptographicUtils.make_connection_payload(CryptographicUtils.sort_kik_map(the_map)).encode(
            'UTF-8')

        # send session request
        self.wrappedSocket.send(packet)
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        if "ok" not in response:
            raise KikErrorException(response, "Could not init session: " + response)
        self._log("[+] Session established.")

    def get_chat_partners(self):
        self._log("[+] Getting roster (chat partners list)...")
        data = ('<iq type="get" id="{}">'
                '<query p="8" xmlns="jabber:iq:roster" />'
                '</iq>').format(CryptographicUtils.make_kik_uuid())
        self._make_request(data)
        response = self._get_full_response()

        chat_partners = list(map(self._parse_chat_partner, list(response.query.children)))
        chat_partner_dict = {user['jid']: user for user in chat_partners}
        self._log("[+] Fine.")

        return chat_partner_dict

    def get_info_for_node(self, node):
        jid = node if "@" in node else node + "@talk.kik.com"
        data = ('<iq type="get" id="{}">'
                '<query xmlns="kik:iq:friend:batch">'
                '<item jid="{}" />'
                '</query>'
                '</iq>').format(CryptographicUtils.make_kik_uuid(), jid)
        self._make_request(data)
        response = self._get_response()
        return self._parse_user_jid_element(response.query.success.item)

    def get_info_for_username(self, username):
        self._log("[+] Getting info for username '" + username + "'...")
        data = ('<iq type="get" id="{}">'
                '<query xmlns="kik:iq:friend">'
                '<item username="{}" />'
                '</query>'
                '</iq>').format(CryptographicUtils.make_kik_uuid(), username)
        self._make_request(data)
        response = self._get_response()

        if response.error:
            if response.error.text == "User not found":
                self._log("[-] No users were found for username '" + username + "'")
                return None
            else:
                self._log("[-] Failed to get user info: " + response.error.text, DebugLevel.WARNING)
                raise KikErrorException(response.error.text)

        jid_info = dict()
        jid_info["jid"] = response.contents[0].contents[0]['jid']
        jid_info["display_name"] = response.find('display-name').text
        jid_info["username"] = response.find('username').text
        jid_info["picture_url"] = response.find('pic').text if response.find('pic') is not None else None

        self._log("[+] Okay")

        return jid_info

    def get_info_for_group(self, group_hashtag):
        # essentially doing a group search
        if not group_hashtag.startswith("#"):
            group_hashtag = "#" + group_hashtag

        self._log("[+] Getting info for group (code: " + str(group_hashtag) + ")...")
        data = ('<iq type="get" id="{}">'
                '<query xmlns="kik:groups:admin">'
                '<g action="search">'
                '<code>{}</code>'
                '</g>'
                '</query>'
                '</iq>').format(CryptographicUtils.make_kik_uuid(), group_hashtag)
        self._make_request(data)
        response = self._get_response()
        if response.error:
            self._log("[-] Error when trying to get group info:", DebugLevel.ERROR)
            self._log(response.error.prettify(), DebugLevel.ERROR)
            raise KikErrorException(response.error, "Unable to get info for group, code: " + str(group_hashtag))

        if response.find("g") is None:
            self._log("[-] No groups found for hashtag " + group_hashtag)
            return None

        groups_info = []
        for group in response.findAll("g"):
            groups_info.append(self._parse_group_element(group))

        self._log("[+] Okay")

        return groups_info

    def find_groups_suggestions(self, search_query):
        if search_query.startswith("#"):
            search_query = search_query[1:]
        self._log("[+] Searching groups with query '{}'...".format(search_query))

        encoded_search_query = base64.b64encode(("\x0a" + chr(len(search_query)) + search_query).encode(), b"-_").decode()
        if encoded_search_query.endswith("="):
            encoded_search_query = encoded_search_query[:encoded_search_query.index("=")]

        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:iq:xiphias:bridge" service="mobile.groups.v1.GroupSearch" method="FindGroups">'
                '<body>{}</body></query></iq>') \
            .format(KikCryptographicUtils.make_kik_uuid(), encoded_search_query)
        self._make_request(data)

        response = self._get_response()
        if response.error:
            self._log("[-] Error when trying to get groups suggestions:", DebugLevel.ERROR)
            self._log(response.error.prettify(), DebugLevel.ERROR)
            raise KikErrorException(response.error, "Unable to get group suggestions. query: " + str(search_query))

        if response.find("body") is None:
            self._log("[-] Can't find results")
            return None

        encoded_results = base64.b64decode(response.find("body").text.encode(), b"-_")
        results = group_search_service_pb2.FindGroupsResponse()
        results.ParseFromString(encoded_results)

        if len(results.match) == 0:
            self._log("[!] Found no matching groups")
        else:
            self._log("[+] Okay")

        return results

    # -- IMPORTANT NOTE --
    # This method was found to always produce
    # <error type="modify" code="400">
    #    <bad-request xmlns="urn:ietf:params:xml:ns:xmpp-stanzas"/>
    # </error>
    # for an unknown reason
    # -- IMPORTANT NOTE --
    def join_group(self, group_hashtag):
        if not group_hashtag.startswith("#"):
            group_hashtag = "#" + group_hashtag

        groups_suggestions = self.find_groups_suggestions(group_hashtag)
        if groups_suggestions is None or len(groups_suggestions.match) == 0:
            return None

        group_to_join = groups_suggestions.match[0]
        group_to_join_name = group_to_join.display_data.hashtag

        if group_to_join_name.lower() != group_hashtag.lower():
            self._log("[!] The group '{}' does not match exactly to the requested group '{}', so not joining."
                      .format(group_to_join_name, group_hashtag))
            return None

        self._log("[+] Joining group '{}' with {} members...".format(group_to_join_name, group_to_join.member_count))

        join_token = group_to_join.group_join_token.token
        join_token = base64.b64encode(join_token, b"-_").decode()
        if join_token.endswith("="):
            join_token = join_token[:join_token.index("=")]

        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:groups:admin">'
                '<g jid="{}" action="join">'
                '<code>{}</code>'
                '<token>{}</token>'
                '</g></query></iq>') \
            .format(KikCryptographicUtils.make_kik_uuid(),
                    self._resolve_group(group_to_join.jid.local_part),
                    group_hashtag,
                    join_token)
        self._make_request(data)

        response = self._get_response()
        if response.error:
            self._log("[-] Error when trying to join group:", DebugLevel.ERROR)
            self._log(response.error.prettify(), DebugLevel.ERROR)
            raise KikErrorException(response.error, "Unable to join group '{}'".format(group_hashtag))

        if response.find("type") is None:
            self._log("[-] Can't find results")
            return None

        self._log("[+] Joined to group '{}'".format(group_hashtag))

        return group_to_join

    def send_message(self, username, body, groupchat=False):
        self._log('[+] Sending message "{}" to {}...'.format(body, username))

        jid = username if groupchat else self._resolve_username(username)
        group_type = "groupchat" if groupchat else "chat"
        unix_timestamp = str(int(round(time.time() * 1000)))
        cts = "1494428808185"
        uuid = CryptographicUtils.make_kik_uuid()

        packet = ('<message type="{0}" to="{1}" id="{2}" cts="{3}">'
                  '<body>{4}</body>'
                  '{5}'
                  '<preview>{6}</preview>'
                  '<kik push="true" qos="true" timestamp="{7}" />'
                  '<request xmlns="kik:message:receipt" r="true" d="true" />'
                  '<ri></ri>'
                  '</message>'
                  ).format(group_type, jid, uuid, cts, body,
                           ("<pb></pb>" if groupchat else ""), body, unix_timestamp).encode('UTF-8')
        self._send_packet(packet)

        is_acked, is_delivered, receipt_id = False, False, ""

        while True:
            info = self.get_next_event(1)
            if info is None:
                break
            if info["type"] == "acknowledgement":
                is_acked = info["id"] == uuid
            elif info["type"] == "message_delivered":
                is_delivered = info["message_id"] == uuid
                receipt_id = info["xml_element"]["id"]
            if is_acked and is_delivered and receipt_id != "":
                break

        if not is_acked:
            self._log("[-] Failed, message was not acknowledged", DebugLevel.ERROR)
            return False
        elif not is_delivered or receipt_id == "":
            self._log("[+] Message '" + uuid + "' seems to be sent but not delivered", DebugLevel.WARNING)
        else:
            self._log("[+] Message receipt id: " + receipt_id)

            data = ('<iq type="set" id="{}" cts="1494351900281">'
                    '<query xmlns="kik:iq:QoS">'
                    '<msg-acks>'
                    '<sender jid="{}">'
                    '<ack-id receipt="false">{}</ack-id>'
                    '</sender>'
                    '</msg-acks>'
                    '<history attach="false" />'
                    '</query>'
                    '</iq>').format(CryptographicUtils.make_kik_uuid(), jid, receipt_id)
            self._make_request(data)
            self._log("[+] Sent")
        return True

    def send_is_typing(self, username, is_typing, groupchat=False):
        self._log('[+] Sending is_typing = {}...'.format(is_typing))

        jid = username if groupchat else self._resolve_username(username)
        unix_timestamp = str(int(time.time() * 1000))
        uuid = CryptographicUtils.make_kik_uuid()
        group_type = "groupchat" if groupchat else "is-typing"

        data = '<message type="{}" to="{}" id="{}">' \
               '{}' \
               '<kik push="false" qos="false" timestamp="{}" />' \
               '<is-typing ' \
               'val="{}" />' \
               '</message>'.format(group_type, jid, uuid, "<pb></pb>" if groupchat else "", unix_timestamp, is_typing)
        self._make_request(data)
        self._log("[+] Okay")

    def add_friend(self, username):
        self._log("[+] Adding {} as a friend...".format(username))
        jid = self._resolve_username(username)

        uuid = CryptographicUtils.make_kik_uuid()
        data = '<iq type="set" id="{}">' \
               '<query xmlns="kik:iq:friend">' \
               '<add jid="{}" />' \
               '</query>' \
               '</iq>'.format(uuid, jid)

        self._make_request(data)
        response = self._get_response()

        if response.find('error'):
            self._log("[-] Could not add '" + username + "' as a friend.", DebugLevel.ERROR)
            self._log(response.prettify(), DebugLevel.ERROR)
            return False

        jid_info = dict()
        jid_info["node"] = username[username.find("@")] if "@" in username else username
        jid_info["display_name"] = response.find('display-name').text
        jid_info["username"] = response.find('username').text
        self._log("[+] Okay")
        return jid_info

    def send_read_confirmation(self, username, message_id):
        self._log("[+] Sending read confirmation for message " + message_id + "...")

        jid = self._resolve_username(username)
        uuid = CryptographicUtils.make_kik_uuid()
        unix_timestamp = str(int(time.time() * 1000))

        data = ('<message type="receipt" id="{}" to="{}" cts="{}">'
                '<kik push="false" qos="true" timestamp="{}" />'
                '<receipt xmlns="kik:message:receipt" type="read">'
                '<msgid id="{}" />'
                '</receipt>'
                '</message>').format(uuid, jid, unix_timestamp, unix_timestamp, message_id)
        self._make_request(data)
        self._log("[+] Okay")

    def sign_up(self, email, username, password, first_name, last_name, birthday="1974-11-20", captcha_result=None):
        uuid = CryptographicUtils.make_kik_uuid()
        passkey_e = CryptographicUtils.key_from_password(email, password)
        passkey_u = CryptographicUtils.key_from_password(username, password)
        data = ('<iq type="set" id="{}">'
                '<query xmlns="jabber:iq:register">'
                '<email>{}</email>'
                '<passkey-e>{}</passkey-e>'
                '<passkey-u>{}</passkey-u>'
                '<device-id>{}</device-id>'
                '<username>{}</username>'
                '<first>{}</first>'
                '<last>{}</last>'
                '<birthday>{}</birthday>'
                '{}'
                '<version>{}</version>'
                '<device-type>android</device-type>'
                '<model>Nexus 7</model>'
                '<android-sdk>25</android-sdk>'
                '<registrations-since-install>1</registrations-since-install>'
                '<install-date>unknown</install-date>'
                '<logins-since-install>0</logins-since-install>'
                '<prefix>CAN</prefix>'
                '<lang>en_US</lang>'
                '<brand>google</brand>'
                '<android-id>{}</android-id>'
                '</query>'
                '</iq>').format(uuid, email, passkey_e, passkey_u, self.device_id, username, first_name, last_name,
                                birthday, '<challenge><response>{}</response></challenge>'
                                .format(captcha_result) if captcha_result else '', self.kik_version, self.android_id)

        self._log("[+] Registering...")
        self._make_request(data)
        response = self._get_response()
        if response.error:
            captcha = response.find('captcha-url')
            if captcha:
                self._log("[-} Encountered a captcha. URL: " + captcha.string, DebugLevel.ERROR)
                raise KikCaptchaException(response.error, "Captcha when trying to sign up! URL: " + captcha.string,
                                          captcha.string)
            else:
                self._log("[-] Kik error code: {}".format(response.error['code']), DebugLevel.ERROR)
                self._log(response.error.prettify(), DebugLevel.ERROR)
                raise KikLoginException(response.error, "Kik error code: {}".format(response.error['code']))

        if not response.find('node'):
            raise KikErrorException(response, "No node in registration response")
        node = response.find('node').text
        self._log("[+] Registration seems successful, node: {}".format(node))

    def validate_username_for_registration(self, username):
        uuid = CryptographicUtils.make_kik_uuid()

        data = ('<iq type="get" id="{}">'
                '<query xmlns="kik:iq:check-unique">'
                ' <username>{}</username>'
                '</query>'
                '</iq>').format(uuid, username)
        self._make_request(data)
        element = self._get_response()
        is_unique = element.find("username")["is-unique"] == "true"

        return is_unique

    def validate_name_for_registration(self, first_name, last_name):
        uuid = CryptographicUtils.make_kik_uuid()

        data = ('<iq type="get" id="{}">'
                '<query xmlns="kik:iq:check-unique">'
                '<first>{}</first>'
                '<last>{}</last>'
                '</query>'
                '</iq>').format(uuid, first_name, last_name)
        self._make_request(data)
        element = self._get_response()
        is_first_name_valid = element.find("first")["is-valid"] == "true"
        is_last_name_valid = element.find("last")["is-valid"] == "true"

        return is_first_name_valid and is_last_name_valid

    def get_history(self):
        uuid = CryptographicUtils.make_kik_uuid()

        data = ('<iq type="set" id="af0811f1-446f-4103-ba04-2eedf8397008" cts="1513349802685">'
                '<query xmlns="kik:iq:QoS">'
                '<msg-acks />'
                '<history attach="true" />'
                '</query>'
                '</iq>'
                ).format(uuid)
        self._make_request(data)
        element = self._get_response()
        print(element.prettify())

    def get_next_event(self, timeout=None):
        response = ""
        while response == "" or response[-1:] != ">":
            self.wrappedSocket.settimeout(timeout)
            try:
                response = response + self.wrappedSocket.recv(16384).decode('UTF-8').strip()
            except socket.timeout:
                return None

        info = dict()
        info["raw_response"] = response
        try:
            super_element = BeautifulSoup(response, features="xml")
            element = next(iter(super_element.children))
            info["xml_element"] = element
        except StopIteration:
            if response == "</k>":
                info["type"] = "end"
                return info
            else:
                self._log("[-] XML parsing of event failed:", DebugLevel.WARNING)
                self._log(response, DebugLevel.WARNING)
                return None

        if element.name == 'iq':
            info["type"] = "qos"
        elif element.name == 'ack':
            info["type"] = "acknowledgement"
            info["id"] = element["id"]
        elif element.name == 'message':
            message_type = element['type']
            info["from"] = element['from']

            if message_type == "receipt":
                if element.receipt['type'] == 'read':
                    info["type"] = "message_read"
                    info["message_id"] = element.receipt.msgid['id']
                elif element.receipt['type'] == 'delivered':
                    info["type"] = "message_delivered"
                    info["message_id"] = element.receipt.msgid['id']
                else:
                    info["type"] = message_type
                    self._log("[-] Receipt received but not type 'read' or 'delivered': {0}".format(response),
                              DebugLevel.WARNING)
            elif message_type == "is-typing":
                info["type"] = "is_typing"
                is_typing_value = element.find('is-typing')['val']
                info["is_typing"] = is_typing_value == "true"
            elif message_type == "chat":
                info["type"] = "message"
                if element.body:
                    info["body"] = element.body.text
                elif element.find('content'):
                    self.parse_content_message(info, element, False)
                else:
                    self._log("[-] Unknown chat message: ", DebugLevel.WARNING)
                    self._log(element.prettify(), DebugLevel.WARNING)
                info["message_id"] = element['id']
            elif message_type == "groupchat":
                if element.g:
                    info['group_id'] = element.g['jid']
                else:
                    self._log("[-] No group_id in groupchat message:", DebugLevel.WARNING)
                info["message_id"] = element['id']
                if element.body:
                    info["type"] = "group_message"
                    info["body"] = element.body.text
                elif element.sysmsg:
                    info["type"] = "system_message"
                    info["message"] = element.sysmsg.text
                elif element.find('is-typing'):
                    info["type"] = "group_typing"
                    is_typing_value = element.find('is-typing')['val']
                    info["is_typing"] = is_typing_value == "true"
                elif element.find('content'):
                    self.parse_content_message(info, element, True)
                else:
                    self._log("[-] Unknown groupchat message: ", DebugLevel.WARNING)
                    self._log(element.prettify(), DebugLevel.WARNING)
            else:
                self._log("[-] Unknown message type received: " + message_type, DebugLevel.WARNING)
                self._log(element.prettify(), DebugLevel.WARNING)
        else:
            self._log("[!] Received unknown event:", DebugLevel.WARNING)
            self._log(element.prettify(), DebugLevel.WARNING)

        return info

    def parse_content_message(self, info, element, groupchat=False):
        info["type"] = "content"
        info["app_id"] = element.find("content")["app-id"]
        items = element.findAll("item")
        if items:
            for item in items:
                if item.key and item.val:
                    info[item.key.text] = item.val.text
        if info["app_id"] == "com.kik.ext.stickers":
            info["type"] = "sticker"
        elif info["app_id"] == "com.kik.ext.gallery":
            info["type"] = "gallery"
            info['file_url'] = element.find('file-url').text
            info['file_name'] = element.find('file-name').text
        elif info["app_id"] == "com.kik.ext.camera":
            info["type"] = "camera"
            info['file_url'] = element.find('file-url').text
            info['file_name'] = element.find('file-name').text
        elif info["app_id"] == "com.kik.ext.gif":
            info["type"] = "gif"
            info['uris'] = {}
            uris = element.find('uris')
            for uri in uris:
                info['uris'][uri['file-content-type']] = uri.text
        elif info["app_id"] == "com.kik.cards":
            info["type"] = "card"
            info['app_name'] = element.find('app-name').text
            url_element = element.find('uri', {'platform': 'cards'})
            if info['app_name'] == 'ScribbleChat':
                info['video_url'] = element.find('uri', {'type': 'video'}).text
            elif url_element:
                info['url'] = url_element.text
        else:
            self._log("[-] Unknown content type: {}".format(info["app_id"]))
            self._log(element.prettify())
        if groupchat:
            info["type"] = "group_" + info["type"]

    def set_device_identifiers(self, device_id, android_id):
        self.device_id = device_id
        self.android_id = android_id

    def _parse_chat_partner(self, element):
        if element.name == 'g':
            return KikClient._parse_group_element(element)
        elif element.name == 'item':
            return KikClient._parse_user_jid_element(element)
        else:
            self._log("[-] Unknown peer type: {}".format(element), DebugLevel.WARNING)

    @staticmethod
    def _parse_user_jid_element(element):
        jid_info = dict()
        jid_info["type"] = 'user'
        jid_info["jid"] = element['jid']
        jid_info["node"] = KikClient.jid_to_node(element['jid'])
        if element.find('display-name'):
            jid_info["display_name"] = element.find('display-name').text
        if element.find("username"):
            jid_info["username"] = element.find('username').text
        if element.find('pic'):
            jid_info["picture_url"] = element.find('pic').text
        return jid_info

    @staticmethod
    def _parse_group_element(element):
        jid_info = dict()
        is_public = element.has_attr('is-public') and element['is-public'] == 'true'
        jid_info["jid"] = element['jid']
        jid_info['is_public'] = is_public

        if element.pic:
            jid_info['picture_url'] = element.pic.text

        users = element.findAll('m')
        jid_info["display_name"] = element.n.text if element.n else None
        jid_info["picture_url"] = element.find('pic').text if element.pic else None
        jid_info["code"] = element.code.text if element.find('code') else None
        jid_info['users'] = list(map(KikClient._parse_user_element, users))
        if is_public:
            jid_info['type'] = 'group'

        return jid_info

    @staticmethod
    def _parse_user_element(user):
        info = {}
        if user.find('first-name'):
            info['first_name'] = user.find('first-name').text
        if user.find("pic"):
            info['picture_url'] = user.find("pic").text
        if user.a or "a" in user:
            info['is_admin'] = user.a == "1" or user["a"] == "1"
        if user.s or "s" in user:
            info['is_owner'] = user.s == "1" or user["s"] == "1"
        if not user.find("pic") and not user.find('first-name'):
            info['jid'] = user.text
        return info

    @staticmethod
    def jid_to_node(jid):
        return jid.replace('@talk.kik.com', '')

    def _send_packet(self, packet):
        self.wrappedSocket.send(packet)

    def _make_request(self, data, uuid=None):
        packet = data.encode('UTF-8')
        self._send_packet(packet)
        response = self._get_response()
        self._verify_ack(response, uuid)

    def _get_response(self):
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        if response == '':
            raise KikEmptyResponseException(response, "Kik server returned empty response")
        soup = BeautifulSoup(response, features='xml')
        return next(iter(soup.children))

    def _get_full_response(self):
        response = ""
        while response == "" or response[-1:] != ">":
            try:
                response = response + self.wrappedSocket.recv(16384).decode('UTF-8').strip()
            except socket.timeout:
                self._log("[-] Timeout in waiting for response")
                raise KikEmptyResponseException(response, "Kik server returned empty response")
        soup = BeautifulSoup(response, features='xml')
        return next(iter(soup.children))

    def _verify_ack(self, response, uuid):
        ack_id = response['id']
        is_valid = ack_id == uuid if uuid is not None else len(ack_id) > 10
        if not is_valid:
            self._log("[-] Ack id was not found:")
            self._log(response)
            raise KikInvalidAckException(response)
        return True

    def _resolve_username(self, username):
        jid_domain = "@talk.kik.com"

        if username.endswith(jid_domain):
            return username

        if self.user_info is not None:
            for node in self.user_info["chat_list"]:
                if node[:node.rfind('_')] == username:
                    return node + jid_domain

        for jid in self.jid_cache_list:
            if jid[:jid.rfind('_')] == username:
                return jid

        jid_info = self.get_info_for_username(username)
        if jid_info is None:
            raise Exception("Failed to convert username to kik node")
        jid = jid_info["jid"]
        self.jid_cache_list.append(jid)
        return jid

    def _resolve_group(self, group_jid):
        jid_domain = "groups.kik.com"

        if group_jid.endswith(jid_domain):
            return group_jid

        return group_jid + "@" + jid_domain

    def _log(self, message, message_level=DebugLevel.VERBOSE):
        if self.debug_level == DebugLevel.VERBOSE:
            print(message)
        elif self.debug_level == DebugLevel.WARNING and int(message_level) >= int(DebugLevel.WARNING):
            print(message)
        elif self.debug_level == DebugLevel.ERROR and int(message_level) >= int(DebugLevel.ERROR):
            print(message)

    def close(self):
        self.wrappedSocket.close()

    @staticmethod
    def _parse_chat_list_bin(chat_list_bin):
        # chat_list_bin is a binary that contains the JIDs (names) of the user's chat participants
        # before each name there are 6 bytes of information that is not decoded it.
        # TODO: see classes1/kik/core/a/a/a.java (function "b") and parse it this way
        names = []
        current_index = 0
        while current_index < len(chat_list_bin):
            name_length = chat_list_bin[current_index + 5]
            name = chat_list_bin[current_index + 6:current_index + 6 + name_length]
            names.append(name.decode('UTF-8'))
            current_index = current_index + 6 + name_length
        return names
