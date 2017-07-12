import socket
import ssl
import hashlib
import binascii
import base64
import time
import rsa
import hmac

from bs4 import BeautifulSoup

from kik_unofficial.cryptographicutils import KikCryptographicUtils
from kik_unofficial.utilities import Utilities

HOST, PORT = "talk1110an.kik.com", 5223


class InvalidAckException(Exception):
    pass


class KikClient:
    user_info = None
    node_cache_list = []

    def __init__(self, username, password):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.wrappedSocket = ssl.wrap_socket(self.sock)
        connection_success = self.connect_to_kik_server()
        if not connection_success:
            raise Exception("Could not connect to kik server")
        login_success = self.login(username, password)
        if not login_success:
            raise Exception("Could not log in")
        session_success = self.establish_session(self.user_info["username"], self.user_info["node"], password)
        if not session_success:
            raise Exception("Could not establish session")

    def get_user_info(self):
        return self.user_info

    def request(self, data):
        packet = data.encode('UTF-8')
        self.wrappedSocket.send(packet)
        response = self.get_response()
        self.verify_ack(response)

    def get_response(self):
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        soup = BeautifulSoup(response, features='xml')
        return next(iter(soup.children))

    @staticmethod
    def verify_ack(response):
        ack_id = response['id']
        if len(ack_id) < 10:
            print("[-] Ack id too short: ")
            print(response)
            raise InvalidAckException
        return True

    def connect_to_kik_server(self):
        version = "11.1.1.12218"
        timestamp = "1496333366683"
        sid = KikCryptographicUtils.make_kik_uuid()
        device_id = "167da12427ee4dc4a36b40e8debafc25"

        # some super secret cryptographic stuff - computing 'cv' and 'signed'
        private_key_pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIBPAIBAAJBANEWUEINqV1KNG7Yie9GSM8t75ZvdTeqT7kOF40kvDHIp" \
                          "/C3tX2bcNgLTnGFs8yA2m2p7hKoFLoxh64vZx5fZykCAwEAAQJAT" \
                          "/hC1iC3iHDbQRIdH6E4M9WT72vN326Kc3MKWveT603sUAWFlaEa5T80GBiP/qXt9PaDoJWcdKHr7RqDq" \
                          "+8noQIhAPh5haTSGu0MFs0YiLRLqirJWXa4QPm4W5nz5VGKXaKtAiEA12tpUlkyxJBuuKCykIQbiUXHEwzFYbMHK5E" \
                          "/uGkFoe0CIQC6uYgHPqVhcm5IHqHM6/erQ7jpkLmzcCnWXgT87ABF2QIhAIzrfyKXp1ZfBY9R0H4pbboHI4uatySKc" \
                          "Q5XHlAMo9qhAiEA43zuIMknJSGwa2zLt/3FmVnuCInD6Oun5dbcYnqraJo=\n-----END RSA PRIVATE KEY----- "
        private_key = rsa.PrivateKey.load_pkcs1(private_key_pem, format='PEM')
        signature = rsa.sign((device_id + ":" + version + ":" + timestamp + ":" + sid).encode('UTF-8'), private_key,
                             'SHA-256')
        signature = base64.b64encode(signature, '-_'.encode('UTF-8')).decode('UTF-8')[:-2]
        hmac_data = timestamp + ":" + "CAN" + device_id
        hmac_secret_key = KikCryptographicUtils.build_hmac_key()
        cv = binascii.hexlify(hmac.new(hmac_secret_key, hmac_data.encode('UTF-8'), hashlib.sha1).digest()).decode(
            'UTF-8')

        mapp = {'cv': cv, 'v': version, 'anon': "1", 'sid': sid, 'n': '1', 'conn': 'WIFI', 'ts': timestamp,
                'lang': 'en_US', 'dev': 'CAN' + device_id, 'signed': signature}
        initial_connection_payload = KikCryptographicUtils.make_connection_payload(
            KikCryptographicUtils.sort_kik_map(mapp)).encode('UTF-8')

        print("[+] Connecting to kik server...")
        self.wrappedSocket.connect((HOST, PORT))
        self.wrappedSocket.send(initial_connection_payload)
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        if "ok" not in response:
            print("[-] Could not connect: " + response)
            return False

        print("[+] Connected.")
        return True

    def login(self, username, password):
        print("[+] Logging in (username: " + username + ", password: " + password + ")...")

        device_id = "167da12427ee4dc4a36b40e8debafc25"
        password_key = KikCryptographicUtils.key_from_password(username, password)
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
                '<version>11.1.1.12218</version>'
                '<lang>en_US</lang>'
                '<android-sdk>19</android-sdk>'
                '<registrations-since-install>0</registrations-since-install>'
                '<prefix>CAN</prefix>'
                '<android-id>c10d47ba7ee17193</android-id>'
                '<model>Samsung Galaxy S5 - 4.4.4 - API 19 - 1080x1920</model>'
                '</query>'
                '</iq>').format(KikCryptographicUtils.make_kik_uuid(), username, password_key, device_id)
        self.request(data)
        response = self.get_response()

        if response.error:
            print("[-] Error! Code: {}".format(response.error['code']))
            print(response.error.prettify())
            return False
        captcha = response.find('captcha-type')
        if captcha:
            print("[-] Captcha! URL:" + captcha)
            return False
        if response.find('password-mismatch'):
            print("[-] Password mismatch")
            return False
        if response.find("kik:error"):
            print("[-] Could not log in. response:")
            print(response.prettify())
            return False

        user_info = dict()
        user_info["node"] = response.find('node').text
        user_info["username"] = response.find('username').text
        user_info["email"] = response.find('email').text
        user_info["first"] = response.find('first').text
        user_info["last"] = response.find('last').text
        user_info["public_key"] = response.find('record', {'pk': 'messaging_pub_key'}).text
        user_info["private_key"] = response.find('record', {'pk': 'enc_messaging_priv_key'}).text
        user_info["chat_list"] = self._parse_chat_list_bin(
            Utilities.decode_base64(response.find('record', {'pk': 'chat_list_bins'}).text.encode('UTF-8')))

        print("[+] Logged in.")
        Utilities.print_dictionary(user_info)
        self.user_info = user_info
        return user_info

    def establish_session(self, username, node, password):
        print("[+] Establishing session...")
        # reset the socket
        self.wrappedSocket.send("</k>".encode('UTF-8'))
        self.wrappedSocket.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.wrappedSocket = ssl.wrap_socket(self.sock)
        self.wrappedSocket.connect((HOST, PORT))

        jid = node + "@talk.kik.com"
        jid_with_resource = jid + "/CAN167da12427ee4dc4a36b40e8debafc25"
        timestamp = "1496333389122"
        sid = KikCryptographicUtils.make_kik_uuid()
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
        hmac_secret_key = KikCryptographicUtils.build_hmac_key()
        cv = binascii.hexlify(hmac.new(hmac_secret_key, hmac_data.encode('UTF-8'), hashlib.sha1).digest()).decode(
            'UTF-8')

        password_key = KikCryptographicUtils.key_from_password(username, password)

        the_map = {'from': jid_with_resource, 'to': 'talk.kik.com', 'p': password_key, 'cv': cv, 'v': version,
                   'sid': sid, 'n': '1', 'conn': 'WIFI', 'ts': timestamp, 'lang': 'en_US', 'signed': signature}
        packet = KikCryptographicUtils.make_connection_payload(KikCryptographicUtils.sort_kik_map(the_map)).encode(
            'UTF-8')

        # send session request
        self.wrappedSocket.send(packet)
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        if "ok" not in response:
            print("[-] Could not init session: " + response)
            return False
        print("[+] Session established.")

        return True

    def get_chat_partners(self):
        print("[+] Getting roster (chat partners list)...")
        data = ('<iq type="get" id="{}">'
                '<query p="8" xmlns="jabber:iq:roster" />'
                '</iq>').format(KikCryptographicUtils.make_kik_uuid())
        self.request(data)
        response = self.get_response()

        # parse roster
        chat_partners = []
        for wht in response[0]:
            user_info = dict()
            user_info['jid'] = wht.attrib['jid']
            for child in wht:
                user_info[child.tag[child.tag.find('}') + 1:]] = child.text
            user_info['node'] = user_info['jid'][:user_info['jid'].find('@')]
            chat_partners.append(user_info)
        print("[+] Fine.")

        return chat_partners

    def get_info_for_node(self, node):
        jid = node + "@talk.kik.com"
        data = ('<iq type="get" id="{}">'
                '<query xmlns="kik:iq:friend:batch">'
                '<item jid="{}" />'
                '</query>'
                '</iq>').format(KikCryptographicUtils.make_kik_uuid(), jid)
        self.request(data)
        response = self.get_response()

        jid_info = dict()
        jid_info["node"] = node
        jid_info["display_name"] = response.find('display-name').text
        jid_info["username"] = response.find('username').text
        jid_info["picture_url"] = response.find('pic').text
        return jid_info

    def get_info_for_username(self, username):
        data = ('<iq type="get" id="{}">'
                '<query xmlns="kik:iq:friend">'
                '<item username="{}" />'
                '</query>'
                '</iq>').format(KikCryptographicUtils.make_kik_uuid(), username)
        self.request(data)
        response = self.get_response()

        jid_info = dict()
        # jid_info["node"] = Utilities.string_between_strings(response, "jid=\"", "@")
        jid_info["node"] = response['jid']
        jid_info["display_name"] = response.find('display-name').text
        jid_info["username"] = response.find('username').text
        jid_info["picture_url"] = response.find('pic').text
        return jid_info

    def send_message(self, username, body, groupchat=False):
        print('[+] Sending message "{}" to {}...'.format(body, username))

        jid = self.resolve_user(username)
        group_type = "groupchat" if groupchat else "chat"
        unix_timestamp = str(int(round(time.time() * 1000)))
        cts = "1494428808185"

        data = ('<message type="{0}" to="{1}" id="{2}" cts="{3}">'
                '<body>{4}</body>'
                '{5}'
                '<preview>{6}</preview>'
                '<kik push="true" qos="true" timestamp="{7}" />'
                '<request xmlns="kik:message:receipt" r="true" d="true" />'
                '<ri></ri>'
                '</message>'
                ).format(group_type, jid, KikCryptographicUtils.make_kik_uuid(), cts, body,
                         ("<pb></pb>" if groupchat else ""), body, unix_timestamp)

        self.request(data)
        response = self.get_response()

        # receipt_id = Utilities.string_between_strings(response, "type=\"receipt\" id=\"", "\"")
        receipt_id = response['id']

        if receipt_id != "":
            print("[+] Message receipt id: " + receipt_id)

        data = ('<iq type="set" id="{}" cts="1494351900281">'
                '<query xmlns="kik:iq:QoS">'
                '<msg-acks>'
                '<sender jid="{}">'
                '<ack-id receipt="false">{}</ack-id>'
                '</sender>'
                '</msg-acks>'
                '<history attach="false" />'
                '</query>'
                '</iq>').format(KikCryptographicUtils.make_kik_uuid(), jid, receipt_id)
        self.request(data)
        print("[+] Sent")
        return True

    def send_is_typing(self, username, is_typing, groupchat=False):
        print('[+] Sending is_typing = {}...'.format(is_typing))

        jid = self.resolve_user(username)
        unix_timestamp = str(int(time.time() * 1000))
        uuid = KikCryptographicUtils.make_kik_uuid()
        group_type = "groupchat" if groupchat else "is-typing"

        data = '<message type="{}" to="{}" id="{}">' \
               '{}' \
               '<kik push="false" qos="false" timestamp="{}" />' \
               '<is-typing ' \
               'val="{}" />' \
               '</message>'.format(group_type, jid, uuid, "<pb></pb>" if groupchat else "", unix_timestamp, is_typing)
        self.request(data)
        print("[+] Okay")

    def add_friend(self, username):
        print("[+] Adding {} as a friend...".format(username))
        jid = self.resolve_user(username)

        uuid = KikCryptographicUtils.make_kik_uuid()
        data = '<iq type="set" id="{}">' \
               '<query xmlns="kik:iq:friend">' \
               '<add jid="{}" />' \
               '</query>' \
               '</iq>'.format(uuid, jid)

        self.request(data)
        response = self.get_response()

        if response.find('error'):
            print("[-] Could not add '" + username + "' as a friend.")
            print(response.prettify())
            return False

        jid_info = dict()
        jid_info["node"] = username[username.find("@")] if "@" in username else username
        jid_info["display_name"] = response.find('display-name').text
        jid_info["username"] = response.find('username').text
        print("[+] Okay")
        return jid_info

    def resolve_user(self, username):
        if "@" in username:
            return username
        else:
            return self._username_to_node(username) + "@talk.kik.com"

    def send_read_confirmation(self, username, message_id):
        print("[+] Sending read confirmation for message " + message_id + "...")

        jid = self.resolve_user(username)
        uuid = KikCryptographicUtils.make_kik_uuid()
        unix_timestamp = str(int(time.time() * 1000))

        data = ('<message type="receipt" id="{}" to="{}" cts="{}">'
                '<kik push="false" qos="true" timestamp="{}" />'
                '<receipt xmlns="kik:message:receipt" type="read">'
                '<msgid id="{}" />'
                '</receipt>'
                '</message>').format(uuid, jid, unix_timestamp, unix_timestamp, message_id)
        self.request(data)
        print("[+] Okay")

    def get_next_event(self):
        response = ""
        while response == "":
            self.wrappedSocket.settimeout(None)
            response = self.wrappedSocket.recv(16384).decode('UTF-8').strip()

        info = {}
        super_element = BeautifulSoup(response, features="xml")
        element = next(iter(super_element.children))
        # print('\n', super_element.prettify())

        if element.name == 'k':
            info["type"] = "end"
        elif element.name == 'iq':
            info["type"] = "qos"
        elif element.name == 'ack':
            info["type"] = "ack"
        elif element.name == 'message':
            message_type = element['type']
            info["from"] = element['from']

            if message_type == "receipt":
                if element.receipt['type'] == 'read':
                    info["type"] = "message_read"
                    info["message_id"] = element.receipt.msgid['id']
                else:
                    print("[-] Receipt received but not type 'read': {0}".format(response))
            elif message_type == "is-typing":
                info["type"] = "is_typing"
                is_typing_value = element.find('is-typing')['val']
                info["is_typing"] = is_typing_value == "true"
            elif message_type == "chat":
                info["type"] = "message"
                info["body"] = element.body.text
                info["message_id"] = element['id']
            elif message_type == "groupchat":
                info['group_id'] = element.g['jid']
                info["message_id"] = element['id']
                if element.body:
                    info["type"] = "group_message"
                    info["body"] = element.body.text
                elif element.find('is-typing'):
                    info["type"] = "group_typing"
                    is_typing_value = element.find('is-typing')['val']
                    info["is_typing"] = is_typing_value == "true"
                else:
                    print("Groupchat message doesn't contain body or is-typing")
            else:
                print("[-] Unknown message type received: " + message_type)
                print(response.prettify())
        else:
            print("[!] Received non-message event:")
            print(response.prettify())

        return info

    def _username_to_node(self, username):
        if self.user_info is not None:
            for node in self.user_info["chat_list"]:
                if node[:node.rfind('_')] == username:
                    return node

        for node in self.node_cache_list:
            if node[:node.rfind('_')] == username:
                return node

        jid_info = self.get_info_for_username(username)
        if jid_info is False:
            raise Exception("Failed to convert username to kik node")
        node = jid_info["node"]
        self.node_cache_list.append(node)
        return node

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
