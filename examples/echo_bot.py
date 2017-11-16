import sys
import time

from kik_unofficial.kikclient import KikClient
from kik_unofficial.kikclient import KikCryptographicUtils


def main():
    username, password = "shlomo91", "123456"
    kik_client = KikClient(username, password)

    uuid = KikCryptographicUtils.make_kik_uuid()

    packet = "<iq type=\"set\" id=\"f5956f8e-ba4e-4fc6-8348-48dffd73c39a\"><query xmlns=\"kik:groups:admin\"><g jid=\"1099909556061_g@groups.kik.com\" action=\"join\"><code>#music</code><token>Q0FFU21nRUtsd0VCQVFNQWVJQ2NxQ0NoNjZKdktzMU45aHhEN0ZmSXowdWR4cUZpZWhlWjYzc2UzV3AxQUFBQWJqQnNCZ2txaGtpRzl3MEJCd2FnWHpCZEFnRUFNRmdHQ1NxR1NJYjNEUUVIQVRBZUJnbGdoa2dCWlFNRUFTNHdFUVFNYm1PZHhyMnRHUk5jU3hWcEFnRVFnQ3NuU1pFZEJhT2FWWUQ4MlZPQXRDaWctazFvWnJod3gxNmpOMmdLMHBFUlpFbUJvOEJIUkN1N09ISEZHaEFrb3IxbUdiV2tsZmNKVVJSd1huTHdJalNJMW5hZ2NPbnBZUl9GaGxQUWhwaU9aZVdBUWdaa0dXbVc1WUxuUGU3aWVDOWI1cVdXUk9sZGcwTWU1ZHc0NUhLdFRoT0I</token></g></query></iq>"
    kik_client._make_request(packet)
    print(kik_client._get_response())

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
