"""
The echo bot sends back whatever messages he gets.
"""

import sys
import time
import logging

from kik_unofficial.client import KikClient


def main():
    username, password = "shlomo991", "123456"
    kik_client = KikClient(username, password)

    print("[+] Listening for incoming events.")

    # main events loop
    while True:

        info = kik_client.get_next_event()
        if "type" not in info:
            continue

        if info["type"] == "message_read":
            print("[+] Human has read the message (user " + info["from"] + ", message id: " + info["message_id"] + ")")

        elif info["type"] == "is_typing":
            if info["is_typing"]:
                print("[+] Human is typing (user " + info["from"] + ")")
            else:
                print("[+] Human is not typing (user " + info["from"] + ")")

        elif info["type"] == "message":
            partner = info["from"]
            print("[+] Human says: \"" + info["body"] + "\" (user " + partner + ")")

            kik_client.send_read_confirmation(partner, info["message_id"])
            replay = "You said '" + info["body"] + "'!"
            kik_client.send_is_typing(partner, "true")
            time.sleep(0.2 * len(replay))
            kik_client.send_is_typing(partner, "false")
            kik_client.send_message(partner, replay)

        elif info["type"] == "end":
            print("[!] Server ended communication.")
            break

    print("[+] Done!")
    kik_client.close()


if __name__ == '__main__':
    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3!!")
    try:
        main()
    except KeyboardInterrupt:
        print("[!] User stopped execution.")
