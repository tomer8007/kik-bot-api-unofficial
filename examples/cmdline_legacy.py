import sys
import time
from argparse import ArgumentParser

from kik_unofficial.client_legacy import KikClient


def execute(cmd=sys.argv[1:]):
    parser = ArgumentParser(description="Unofficial Kik api")
    parser.add_argument('-u', '--username', help="Kik username", required=True)
    parser.add_argument('-p', '--password', help="Kik password", required=True)

    args = parser.parse_args(cmd)
    kik = KikClient(args.username, args.password)
    CmdLine(kik).run()


class CmdLine:
    def __init__(self, kik):
        self.kik = kik
        self.partners = {}

    def run(self):
        self.partners = self.kik.get_chat_partners()
        self.list_chats()
        while True:
            try:
                info = self.kik.get_next_event()
                if not info:
                    print("[-] failed to parse info")
                elif 'type' not in info:
                    print("[-] type not in info")
                    print(info)
                elif info["type"] == "message_read":
                    self.message_read(info)
                elif info["type"] == "is_typing":
                    self.is_typing(info)
                elif info["type"] == "message":
                    self.message(info)
                elif info['type'] == 'group_message':
                    self.group_message(info)
                elif info['type'] == 'group_typing':
                    self.group_typing(info)
                elif info['type'] == 'group_content':
                    self.group_content(info)
                elif info['type'] == 'group_sticker':
                    self.group_sticker(info)
                elif info['type'] == 'group_gallery':
                    self.group_gallery(info)
                elif info['type'] == 'group_camera':
                    self.group_camera(info)
                elif info['type'] == 'group_gif':
                    self.group_gif(info)
                elif info['type'] == 'group_card':
                    self.group_card(info)
                elif info['type'] == 'message':
                    self.message(info)
                elif info['type'] == 'content':
                    self.content(info)
                elif info['type'] == 'sticker':
                    self.sticker(info)
                elif info['type'] == 'gallery':
                    self.gallery(info)
                elif info['type'] == 'camera':
                    self.camera(info)
                elif info['type'] == 'gif':
                    self.gif(info)
                elif info['type'] == 'card':
                    self.card(info)
                elif info['type'] == 'qos' or info['type'] == 'acknowledgement':
                    pass
                elif info["type"] == "end":
                    print("[!] Server ended communication.")
                    break
                else:
                    print("[-] Unknown message: {}".format(info))
            except TypeError as e:
                print(e)

    def content(self, info):
        print("[+] Unknown content received of type {}".format(info["app_id"]))

    def sticker(self, info):
        print("[+] Sticker received in pack {}: {}".format(info["sticker_pack_id"], info["sticker_url"]))

    def gallery(self, info):
        print("[+] Gallery image received '{}': {}".format(info['file_name'], info['file_url']))

    def camera(self, info):
        print("[+] Camera image received '{}': {}".format(info['file_name'], info['file_url']))

    def gif(self, info):
        print("[+] Gif received: {}".format(info['uris']))

    def card(self, info):
        if 'jsonData' in info:
            print("[+] Card received: {}: {}".format(info['app_name'], info['jsonData']))
        elif info['app_name'] == 'ScribbleChat':
            print("[+] Card received: {}: {}".format(info['app_name'], info['video_url']))
        elif 'url' in info:
            print("[+] Card received: '{}': {}".format(info['app_name'], info['url']))
        else:
            print("[-] Unknown card received: {}".format(info['app_name']))

    def group_content(self, info):
        print("[+] Unknown content received of type {}".format(info["app_id"]))

    def group_sticker(self, info):
        print("[+] Sticker received in pack {}: {}".format(info["sticker_pack_id"], info["sticker_url"]))

    def group_gallery(self, info):
        print("[+] Gallery image received '{}': {}".format(info['file_name'], info['file_url']))

    def group_camera(self, info):
        print("[+] Camera image received '{}': {}".format(info['file_name'], info['file_url']))

    def group_gif(self, info):
        print("[+] Gif received: {}".format(info['uris']))

    def group_card(self, info):
        if 'jsonData' in info:
            print("[+] Card received: {}: {}".format(info['app_name'], info['jsonData']))
        elif info['app_name'] == 'ScribbleChat':
            print("[+] Card received: {}: {}".format(info['app_name'], info['video_url']))
        elif 'url' in info:
            print("[+] Card received: '{}': {}".format(info['app_name'], info['url']))
        else:
            print("[-] Unknown card received: {}".format(info['app_name']))

    def list_chats(self):
        print("[+] Chats\n{}".format("\n".join([self.full_name(peer['jid']) for peer in self.partners.values()])))

    def display_name(self, name):
        if name not in self.partners:
            peer_info = self.kik.get_info_for_node(name)
            print(peer_info)
            self.partners[peer_info['jid']] = peer_info
        peer = self.partners[name]
        return peer['display_name'].strip()

    def full_name(self, name):
        peer = self.partners[name]
        if peer['type'] == 'group':
            if peer['public']:
                return "{} ({})".format(peer['display_name'], peer['code'])
            else:
                return "{}".format(peer['display_name'])
        else:
            return "{} ({})".format(peer['display_name'], peer['username'])

    def message_read(self, info):
        print("[+] <{0}> message read: {1}".format(self.display_name(info['from']), info["message_id"]))

    def is_typing(self, info):
        if info["is_typing"]:
            print("[+] <{}> typing...".format(self.display_name(info['from'])))
        else:
            print("[+] <{}> stopped typing...".format(self.display_name(info['from'])))

    def message(self, info):
        partner = info['from']
        print("[+] <{0}> {1}".format(partner, info['body']))

        self.kik.send_read_confirmation(partner, info["message_id"])
        reply = "You said '{}'!".format(info['body'])
        self.kik.send_is_typing(partner, "true")
        time.sleep(0.2 * len(reply))
        self.kik.send_is_typing(partner, "false")
        self.kik.send_message(partner, reply)

    def group_message(self, info):
        group = info['group_id']
        print("[+] <{0}> {1}: {2}".format(self.display_name(info['group_id']), self.display_name(info['from']),
                                          info['body']))
        if 'ping' in info['body'].lower():
            self.kik.send_message(group, 'pong', groupchat=True)
            return

    def group_typing(self, info):
        if info['is_typing']:
            print("[+] <{0}> {1} is typing...".format(self.display_name(info['group_id']),
                                                      self.display_name(info['from'])))
        else:
            print("[+] <{0}> {1} stopped typing...".format(self.display_name(info['group_id']),
                                                           self.display_name(info['from'])))
