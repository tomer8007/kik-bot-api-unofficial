import sys
import time

from kik_unofficial.client_legacy import KikClient


def main():
    username, password = "your_username", "password"
    kik_client = KikClient(username, password)

    chat_partners = kik_client.get_chat_partners()
    print("[+] Chats\n{}".format("\n".join([peer['jid'] for peer in chat_partners.values()])))

    # let's talk
    username = "other_username"
    kik_client.send_is_typing(username, "true")
    time.sleep(0.5)
    kik_client.send_is_typing(username, "false")
    kik_client.send_message(username, "hi from bot!")

    print("[+] Done!")
    kik_client.close()


if __name__ == '__main__':
    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3!!")
    try:
        main()
    except KeyboardInterrupt:
        print("[!] User stopped execution.")
