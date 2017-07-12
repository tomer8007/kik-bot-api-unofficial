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
    run(kik)


def run(kik):
    while True:
        try:
            info = kik.get_next_event()
            if 'type' not in info:
                print("[-] type not in info")
                print(info)
            elif info["type"] == "message_read":
                message_read(info)
            elif info["type"] == "is_typing":
                is_typing(info)
            elif info["type"] == "message":
                message(info, kik)
            elif info['type'] == 'group_message':
                group_message(info, kik)
            elif info['type'] == 'group_typing':
                group_typing(info)
            elif info["type"] == "end":
                print("[!] Server ended communication.")
                break
        except TypeError as e:
            print(e)


def message_read(info):
    print("[+] <{0}> message read: {1}".format(info["from"], info["message_id"]))


def is_typing(info):
    if info["is_typing"]:
        print("[+] <{}> typing...".format(info['from']))
    else:
        print("[+] <{}> stopped typing...".format(info['from']))


def message(info, kik):
    partner = info["from"]
    print("[+] <{0}> {1}".format(partner, info['body']))

    kik.send_read_confirmation(partner, info["message_id"])
    reply = "You said '{}'!".format(info['body'])
    kik.send_is_typing(partner, "true")
    time.sleep(0.2 * len(reply))
    kik.send_is_typing(partner, "false")
    kik.send_message(partner, reply)


def group_message(info, kik):
    group = info['group_id']
    print("[+] <{0}> {1}: {2}".format(info['group_id'], info['from'], info['body']))
    if 'ping' in info['body'].lower():
        kik.send_message(group, 'pong', groupchat=True)
        return


def group_typing(info):
    if info['is_typing']:
        print("[+] <{0}> {1} is typing...".format(info['group_id'], info['from']))
    else:
        print("[+] <{0}> {1} stopped typing...".format(info['group_id'], info['from']))
