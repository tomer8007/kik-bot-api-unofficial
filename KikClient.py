import socket
import ssl
import hashlib
import binascii
import xml.etree.ElementTree as ET
import base64
import time
import rsa
import hmac
from KikCryptographicUtils import KikCryptographicUtils
from Utilities import Utilities

HOST, PORT = "talk1110an.kik.com", 5223


class KikClient():
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

    def connect_to_kik_server(self):
        version = "11.1.1.12218"
        timestamp = "1496333366683"
        sid = KikCryptographicUtils.make_kik_uuid()
        device_id = "167da12427ee4dc4a36b40e8debafc25"

        # some super secret cryptographic stuff - computing 'cv' and 'signed'
        private_key_pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIBPAIBAAJBANEWUEINqV1KNG7Yie9GSM8t75ZvdTeqT7kOF40kvDHIp/C3tX2bcNgLTnGFs8yA2m2p7hKoFLoxh64vZx5fZykCAwEAAQJAT/hC1iC3iHDbQRIdH6E4M9WT72vN326Kc3MKWveT603sUAWFlaEa5T80GBiP/qXt9PaDoJWcdKHr7RqDq+8noQIhAPh5haTSGu0MFs0YiLRLqirJWXa4QPm4W5nz5VGKXaKtAiEA12tpUlkyxJBuuKCykIQbiUXHEwzFYbMHK5E/uGkFoe0CIQC6uYgHPqVhcm5IHqHM6/erQ7jpkLmzcCnWXgT87ABF2QIhAIzrfyKXp1ZfBY9R0H4pbboHI4uatySKcQ5XHlAMo9qhAiEA43zuIMknJSGwa2zLt/3FmVnuCInD6Oun5dbcYnqraJo=\n-----END RSA PRIVATE KEY-----"
        private_key = rsa.PrivateKey.load_pkcs1(private_key_pem, format='PEM')
        signature = rsa.sign((device_id + ":" + version + ":" + timestamp + ":" + sid).encode('UTF-8'), private_key, 'SHA-256')
        signature = base64.b64encode(signature, '-_'.encode('UTF-8')).decode('UTF-8')[:-2]
        hmac_data = timestamp + ":" + "CAN" + device_id
        hmac_secret_key = KikCryptographicUtils.build_hmac_key()
        cv = binascii.hexlify(hmac.new(hmac_secret_key, hmac_data.encode('UTF-8'), hashlib.sha1).digest()).decode('UTF-8')

        mapp = {'cv': cv, 'v': version, 'anon': "1", 'sid': sid, 'n': '1', 'conn': 'WIFI', 'ts': timestamp, 'lang': 'en_US', 'dev': 'CAN' + device_id, 'signed': signature}
        initial_connection_payload = KikCryptographicUtils.make_connection_payload(KikCryptographicUtils.sort_kik_map(mapp)).encode('UTF-8')

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
        self.wrappedSocket.send(("<iq type=\"set\" id=\""+KikCryptographicUtils.make_kik_uuid()+"\"><query xmlns=\"jabber:iq:register\"><username>"+username+"</username><passkey-u>"+password_key+"</passkey-u><device-id>"+device_id+"</device-id><install-referrer>utm_source=google-play&amp;utm_medium=organic</install-referrer><operator>310260</operator><install-date>1494078709023</install-date><device-type>android</device-type><brand>generic</brand><logins-since-install>1</logins-since-install><version>11.1.1.12218</version><lang>en_US</lang><android-sdk>19</android-sdk><registrations-since-install>0</registrations-since-install><prefix>CAN</prefix><android-id>c10d47ba7ee17193</android-id><model>Samsung Galaxy S5 - 4.4.4 - API 19 - 1080x1920</model></query></iq>").encode('UTF-8'))
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        ack_id = Utilities.string_between_strings(response, 'ack id="', '"/>')
        if len(ack_id) < 10:
            print("[-] Ack id too short: ")
            print(response)
            return False
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        if "<captcha-type>" in response:
            print("[-] Captcha! URL:" + response[response.index("<captcha-type>"):])
            return False
        if "<password-mismatch" in response:
            print("[-] Password mismatch")
            return False
        if "kik:error" in response:
            print("[-] Could not log in. response:")
            Utilities.pretty_print_xml(response)
            return False

        user_info = dict()
        user_info["node"] = Utilities.extract_tag_from_xml(response, "node")
        user_info["username"] = Utilities.extract_tag_from_xml(response, "username")
        user_info["email"] = Utilities.extract_tag_from_xml(response, "email")
        user_info["first"] = Utilities.extract_tag_from_xml(response, "first")
        user_info["last"] = Utilities.extract_tag_from_xml(response, "last")
        user_info["public_key"] = Utilities.extract_tag_from_xml(response, "record pk=\"messaging_pub_key\"")
        user_info["private_key"] = Utilities.extract_tag_from_xml(response, "record pk=\"enc_messaging_priv_key\"")
        user_info["chat_list"] = self._parse_chat_list_bin(Utilities.decode_base64(Utilities.extract_tag_from_xml(response, "record pk=\"chat_list_bins\"").encode('UTF-8')))

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
        private_key_pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIBPAIBAAJBANEWUEINqV1KNG7Yie9GSM8t75ZvdTeqT7kOF40kvDHIp/C3tX2bcNgLTnGFs8yA2m2p7hKoFLoxh64vZx5fZykCAwEAAQJAT/hC1iC3iHDbQRIdH6E4M9WT72vN326Kc3MKWveT603sUAWFlaEa5T80GBiP/qXt9PaDoJWcdKHr7RqDq+8noQIhAPh5haTSGu0MFs0YiLRLqirJWXa4QPm4W5nz5VGKXaKtAiEA12tpUlkyxJBuuKCykIQbiUXHEwzFYbMHK5E/uGkFoe0CIQC6uYgHPqVhcm5IHqHM6/erQ7jpkLmzcCnWXgT87ABF2QIhAIzrfyKXp1ZfBY9R0H4pbboHI4uatySKcQ5XHlAMo9qhAiEA43zuIMknJSGwa2zLt/3FmVnuCInD6Oun5dbcYnqraJo=\n-----END RSA PRIVATE KEY-----"
        private_key = rsa.PrivateKey.load_pkcs1(private_key_pem, format='PEM')
        signature = rsa.sign((jid + ":" + version + ":" + timestamp + ":" + sid).encode('UTF-8'), private_key, 'SHA-256')
        signature = base64.b64encode(signature, '-_'.encode('UTF-8')).decode('UTF-8')[:-2]
        hmac_data = timestamp + ":" + jid
        hmac_secret_key = KikCryptographicUtils.build_hmac_key()
        cv = binascii.hexlify(hmac.new(hmac_secret_key, hmac_data.encode('UTF-8'), hashlib.sha1).digest()).decode('UTF-8')

        password_key = KikCryptographicUtils.key_from_password(username, password)

        the_map = {'from': jid_with_resource, 'to': 'talk.kik.com', 'p': password_key, 'cv': cv, 'v': version, 'sid': sid, 'n': '1', 'conn': 'WIFI', 'ts': timestamp, 'lang': 'en_US', 'signed': signature}
        packet = KikCryptographicUtils.make_connection_payload(KikCryptographicUtils.sort_kik_map(the_map)).encode('UTF-8')

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
        uuid = KikCryptographicUtils.make_kik_uuid()
        packet = ("<iq type=\"get\" id=\"" + uuid + "\"><query p=\"8\" xmlns=\"jabber:iq:roster\" /></iq>").encode('UTF-8')
        self.wrappedSocket.send(packet)
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        ack_id = Utilities.string_between_strings(response, 'ack id="', '"/>')
        if ack_id != uuid:
            print("[-] Ack id not found:")
            print(response)
            return False
        response = self.wrappedSocket.recv(16384).decode('UTF-8')

        # parse roster
        root = ET.fromstring(response)
        chat_partners = []
        for wht in root[0]:
            user_info = dict()
            user_info['jid'] = wht.attrib['jid']
            for child in wht:
                user_info[child.tag[child.tag.find('}')+1:]] = child.text
            user_info['node'] = user_info['jid'][:user_info['jid'].find('@')]
            chat_partners.append(user_info)
        print("[+] Fine.")

        return chat_partners

    def get_info_for_node(self, node):
        jid = node + "@talk.kik.com"
        uuid = KikCryptographicUtils.make_kik_uuid()
        packet = ("<iq type=\"get\" id=\"" + uuid + "\"><query xmlns=\"kik:iq:friend:batch\"><item jid=\""+jid+"\" /></query></iq>").encode('UTF-8')
        self.wrappedSocket.send(packet)
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        ack_id = Utilities.string_between_strings(response, 'ack id="', '"/>')
        if ack_id != uuid:
            print("[-] Ack id not found: ")
            print(response)
            return False
        response = self.wrappedSocket.recv(16384).decode('UTF-8')

        jid_info = dict()
        jid_info["node"] = node
        jid_info["display_name"] = Utilities.extract_tag_from_xml(response, "display-name")
        jid_info["username"] = Utilities.extract_tag_from_xml(response, "username")
        jid_info["picture_url"] = Utilities.extract_tag_from_xml(response, "pic")
        return jid_info

    def get_info_for_username(self, username):
        packet = ("<iq type=\"get\" id=\""+KikCryptographicUtils.make_kik_uuid()+"\"><query xmlns=\"kik:iq:friend\"><item username=\""+username+"\" /></query></iq>").encode('UTF-8')
        self.wrappedSocket.send(packet)
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        ack_id = Utilities.string_between_strings(response, 'ack id="', '"/>')
        if len(ack_id) < 10:
            print("[-] Failed to fetch info for username '"+username+"' . Ack id not found: ")
            print(response)
            return False
        response = self.wrappedSocket.recv(16384).decode('UTF-8')

        jid_info = dict()
        jid_info["node"] = Utilities.string_between_strings(response, "jid=\"", "@")
        jid_info["display_name"] = Utilities.extract_tag_from_xml(response, "display-name")
        jid_info["username"] = Utilities.extract_tag_from_xml(response, "username")
        jid_info["picture_url"] = Utilities.extract_tag_from_xml(response, "pic")
        return jid_info

    def send_message(self, username, body):
        if "@" in username:
            jid = username
        else:
            jid = self._username_to_node(username) + "@talk.kik.com"

        print("[+] Sending message \"" + body + "\" to " + username + "...")
        unix_timestamp = str(int(round(time.time() * 1000)))
        uuid = KikCryptographicUtils.make_kik_uuid()
        packet = ("<message type=\"chat\" to=\""+jid+"\" id=\""+uuid+"\" cts=\"1494428808185\"><body>"+body+"</body><preview>"+body+"</preview><kik push=\"true\" qos=\"true\" timestamp=\""+unix_timestamp+"\" /><request xmlns=\"kik:message:receipt\" r=\"true\" d=\"true\" /><ri></ri></message>").encode('UTF-8')
        self.wrappedSocket.send(packet)
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        ack_id = Utilities.string_between_strings(response, 'ack id="', '"/>')
        if "kik:iq:QoS" in response:
            response = self.wrappedSocket.recv(16384).decode('UTF-8')
            ack_id = Utilities.string_between_strings(response, 'ack id="', '"/>')
        if ack_id != uuid:
            print("[-] Ack id not found: ")
            print(response)
            return False

        self.wrappedSocket.settimeout(1)
        try:
            response = self.wrappedSocket.recv(16384).decode('UTF-8')
        except socket.timeout:
            print("[+] Message seems to be sent but not delivered.")
            self.wrappedSocket.settimeout(10)
            return True
        if "delivered" not in response:
            print("[-] Couldn't deliver message.")
            Utilities.pretty_print_xml(response)
            return False

        receipt_id = Utilities.string_between_strings(response, "type=\"receipt\" id=\"", "\"")
        if receipt_id != "":
            print("[+] Message receipt id: " + receipt_id)

        uuid = KikCryptographicUtils.make_kik_uuid()
        packet = ("<iq type=\"set\" id=\""+uuid+"\" cts=\"1494351900281\"><query xmlns=\"kik:iq:QoS\"><msg-acks><sender jid=\""+jid+"\"><ack-id receipt=\"false\">"+receipt_id+"</ack-id></sender></msg-acks><history attach=\"false\" /></query></iq>").encode('UTF-8')
        self.wrappedSocket.send(packet)
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        ack_id = Utilities.string_between_strings(response, 'ack id="', '"/>')
        if ack_id != uuid:
            print("[-] Ack id not found: ")
            Utilities.pretty_print_xml(response)
            return False

        self.wrappedSocket.settimeout(10)
        print("[+] Sent")
        return True

    def send_is_typing(self, username, is_typing):
        print("[+] Sending is_typing = "+is_typing+"...")
        if "@" in username:
            jid = username
        else:
            jid = self._username_to_node(username) + "@talk.kik.com"

        unix_timestamp = str(int(time.time() * 1000))
        uuid = KikCryptographicUtils.make_kik_uuid()
        packet = ("<message type=\"is-typing\" to=\""+jid+"\" id=\""+uuid+"\"><kik push=\"false\" qos=\"false\" timestamp=\""+unix_timestamp+"\" /><is-typing val=\""+is_typing+"\" /></message>").encode('UTF-8')
        self.wrappedSocket.send(packet)
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        ack_id = Utilities.string_between_strings(response, 'ack id="', '"/>')
        if ack_id != uuid:
            print("[-] Ack id not found:")
            Utilities.pretty_print_xml(response)
            return False
        print("[+] Okay")

    def add_friend(self, username):
        print("[+] Adding " + username + " as a friend...")
        if "@" in username:
            jid = username
        else:
            jid = self._username_to_node(username) + "@talk.kik.com"

        uuid = KikCryptographicUtils.make_kik_uuid()
        packet = ("<iq type=\"set\" id=\""+uuid+"\"><query xmlns=\"kik:iq:friend\"><add jid=\""+jid+"\" /></query></iq>").encode('UTF-8')

        self.wrappedSocket.send(packet)
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        ack_id = Utilities.string_between_strings(response, 'ack id="', '"/>')
        if ack_id != uuid:
            print("[-] Ack id not found")
            print(response)
            return False

        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        if "<error" in response:
            print("[-] Could not add '" + username + "' as a friend.")
            Utilities.pretty_print_xml(response)
            return False

        jid_info = dict()
        jid_info["node"] = username[username.find("@")] if "@" in username else username
        jid_info["display_name"] = Utilities.extract_tag_from_xml(response, "display-name")
        jid_info["username"] = Utilities.extract_tag_from_xml(response, "username")
        print("[+] Okay")
        return jid_info

    def send_read_confirmation(self, username, message_id):
        print("[+] Sending read confirmation for message " + message_id + "...")
        if "@" in username:
            jid = username
        else:
            jid = self._username_to_node(username) + "@talk.kik.com"
        uuid = KikCryptographicUtils.make_kik_uuid()
        unix_timestamp = str(int(time.time() * 1000))
        packet = ("<message type=\"receipt\" id=\""+uuid+"\" to=\""+jid+"\" cts=\""+unix_timestamp+"\"><kik push=\"false\" qos=\"true\" timestamp=\""+unix_timestamp+"\" /><receipt xmlns=\"kik:message:receipt\" type=\"read\"><msgid id=\""+message_id+"\" /></receipt></message>").encode('UTF-8')
        self.wrappedSocket.send(packet)
        response = self.wrappedSocket.recv(16384).decode('UTF-8')
        ack_id = Utilities.string_between_strings(response, 'ack id="', '"/>')
        if ack_id != uuid:
            print("[-] Ack id not found:")
            return False
        print("[+] Okay")

    def get_next_event(self):
        response = ""
        while response == "":
            self.wrappedSocket.settimeout(None)
            response = self.wrappedSocket.recv(16384).decode('UTF-8').strip()

        info = {}

        try:
            xml_element = ET.fromstring(response)
        except:
            print("[-] XML parsing of message event failed:")
            print(response)
            xml_element = None

        if "</k>" in response:
            info["type"] = "end"
        elif "<message" in response:
            # looks like we got a message-related thing
            if xml_element is None:
                return None

            message_type = xml_element.attrib['type']
            info["from"] = xml_element.attrib['from']

            if message_type == "receipt":
                if "<receipt type=\"read\"":
                    # assume the human read our message
                    info["type"] = "message_read"
                    info["message_id"] = Utilities.string_between_strings(response, "msgid id=\"", "\"")
            elif message_type == "is-typing":
                    info["type"] = "is_typing"
                    is_typing_value = Utilities.string_between_strings(response, "<is-typing val=\"", "\"")
                    info["is_typing"] = True if is_typing_value == "true" else False
            elif message_type == "chat":
                    info["type"] = "message"
                    info["body"] = Utilities.extract_tag_from_xml(response, "body")
                    info["message_id"] = xml_element.attrib['id']
            else:
                print("[-] Unknown message type received: " + message_type)
                Utilities.pretty_print_xml(response)
        elif "<ack id=" in response:
            # acknowledgement event
            if xml_element is None:
                return None
            info["type"] = "acknowledgement"
            info["id"] = xml_element.attrib['id']
        elif "kik:iq:QoS" in response:
            # quality of service thing, do nothing
            pass
        else:
            print("[!] Received unknown event:")
            Utilities.pretty_print_xml(response)

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

    def _parse_chat_list_bin(self, chat_list_bin):
        # chat_list_bin is a binary that contains the JIDs (names) of the user's chat participants
        # before each name there are 6 bytes of information that is not decoded it.
        # TODO: see classes1/kik/core/a/a/a.java (function "b") and parse it this way
        names = []
        current_index = 0
        while current_index < len(chat_list_bin):
            name_length = chat_list_bin[current_index+5]
            name = chat_list_bin[current_index+6:current_index+6+name_length]
            names.append(name.decode('UTF-8'))
            current_index = current_index+6+name_length
        return names

