from argparse import ArgumentParser

import sys

import time

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
        info = kik.get_next_event()
        if 'type' not in info:
            print("[-] type not in info")
            print(info)
        elif info["type"] == "message_read":
            print("[+] Human has read the message (user " + info["from"] + ", message id: " + info["message_id"] + ")")

        elif info["type"] == "is_typing":
            if info["is_typing"]:
                print("[+] Human is typing (user " + info["from"] + ")")
            else:
                print("[+] Human is not typing (user " + info["from"] + ")")

        elif info["type"] == "message":
            partner = info["from"]
            print("[+] Human says: \"" + info["body"] + "\" (user " + partner + ")")

            kik.send_read_confirmation(partner, info["message_id"])
            replay = "You said '" + info["body"] + "'!"
            kik.send_is_typing(partner, "true")
            time.sleep(0.2 * len(replay))
            kik.send_is_typing(partner, "false")
            kik.send_message(partner, replay)

        elif info['type'] == 'group_message':
            print("[+] Human says {0} (user {1}, chat {2})".format(info['body'], info['from'], info['group_id']))

        elif info['type'] == 'group_typing':
            if info['is_typing']:
                print("[+] Human is typing (user {0}, chat {1})".format(info['from'], info['group_id']))
            else:
                print("[+] Human is not typing (user {0}, chat {1})".format(info['from'], info['group_id']))

        elif info["type"] == "end":
            print("[!] Server ended communication.")
            break
