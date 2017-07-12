import random
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


def message_read(info):
    print("[+] Human has read the message (user " + info["from"] + ", message id: " + info["message_id"] + ")")


def is_typing(info):
    if info["is_typing"]:
        print("[+] Human is typing (user " + info["from"] + ")")
    else:
        print("[+] Human is not typing (user " + info["from"] + ")")


def message(info, kik):
    partner = info["from"]
    print("[+] Human says: \"" + info["body"] + "\" (user " + partner + ")")

    kik.send_read_confirmation(partner, info["message_id"])
    reply = "You said '" + info["body"] + "'!"
    kik.send_is_typing(partner, "true")
    time.sleep(0.2 * len(reply))
    kik.send_is_typing(partner, "false")
    kik.send_message(partner, reply)


def group_message(info, kik):
    group = info['group_id']
    if 'ping' in info['body'].lower():
        kik.send_message(group, 'pong', groupchat=True)
        return
    if random.randint(0, 99) > 15:
        return
    reply = get_reply(info['from'].split('_')[0], info['body'])
    print("[+] Human says {0} (user {1}, chat {2})".format(info['body'], info['from'], info['group_id']))
    kik.send_is_typing(group, "true", groupchat=True)
    time.sleep(0.2 * len(reply))
    kik.send_is_typing(group, "false", groupchat=True)
    kik.send_message(group, reply, groupchat=True)


def get_reply(name, message):
    start = random.choice([
        "Wow!",
        "Sweet Jesus",
        "uh,",
        "HAHAHAH",
        "What.",
        'Hehe,',
        "Yeah"
    ])
    mid = random.choice([
        "I'm",
        "you're",
        "your",
        "this crap is",
        "this is",
        "stopped reading cuz this is",
        "i've never been this"
    ])
    end = random.choice([
        "retarded",
        "pure garbage",
        "epic",
        "huge",
        "insightful",
        "incredible",
        "spiritual",
        "sarcastic",
        "ironic",
        "grand",
        "the best i've ever seen"
    ])
    return '> {}: "{}"\n {} {} {}'.format(name, message, start, mid, end)


def group_typing(info):
    if info['is_typing']:
        print("[+] Human is typing (user {0}, chat {1})".format(info['from'], info['group_id']))
    else:
        print("[+] Human is not typing (user {0}, chat {1})".format(info['from'], info['group_id']))
