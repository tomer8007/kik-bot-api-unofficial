import sys
import time
from argparse import ArgumentParser

from kik_unofficial.kikclient import KikClient


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
                if 'type' not in info:
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
                elif info['type'] == 'content':
                    self.content(info)
                elif info['type'] == 'sticker':
                    self.sticker(info)
                elif info["type"] == "end":
                    print("[!] Server ended communication.")
                    break
            except TypeError as e:
                print(e)

    def content(self, info):
        print("[+] Unknown content received of type {}".format(info["app_id"]))

    def sticker(self, info):
        print("[+] Sticker received in pack {}: {}".format(info["sticker_pack_id"], info["sticker_url"]))

    def list_chats(self):
        print("[+] Chats\n{}".format("\n".join([self.full_name(peer['jid']) for peer in self.partners.values()])))

    def display_name(self, name):
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
