from bs4 import BeautifulSoup

from kik_unofficial.datatypes.xmpp.base_elements import XMPPResponse
from kik_unofficial.device_configuration import kik_version_info
from kik_unofficial.utilities.parsing_utilities import get_text_of_tag

CAPTCHA_CALLBACK_PARAMETER = "&callback_url=https://kik.com/captcha-url"


class KikIqError(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.error = data.find('error', recursive=False)
        self.error_code = int(self.error['code'])
        self.error_type = self.error['type']
        self.errors = [e.name for e in self.error.find_all(recursive=False)]
        self.message = str(self.errors)

    def is_dialog(self):
        return hasattr(self, 'dialog')

    def is_captcha(self):
        return hasattr(self, 'captcha_url')

    def __str__(self):
        return f'IqError code={self.error_code} type={self.error_type} errors={",".join(self.errors)}'


class KikDialogError(KikIqError):
    """
    Kik XMPP errors that can return dialogs as part of the error should extend this class.
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        self.dialog = self._parse_error_dialog(self.error.find('dialog', recursive=False))
        if self.dialog:
            self.message = f"Received custom dialog: title={self.dialog.dialog_title}, body={self.dialog.dialog_body}"

    @staticmethod
    def _parse_error_dialog(dialog):
        if dialog is None:
            return None
        else:
            return KikDialogError.Dialog(dialog)

    class Dialog:
        def __init__(self, dialog: BeautifulSoup):
            super().__init__()
            self.dialog_title = get_text_of_tag(dialog, 'dialog-title')
            self.dialog_body = get_text_of_tag(dialog, 'dialog-body')
            self.button_text = get_text_of_tag(dialog, 'button-text')
            self.button_action = get_text_of_tag(dialog, 'button-action')


class KikCaptchaError(KikDialogError):
    """
    Kik XMPP errors that can return captchas as part of the error should extend this class.
    """

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        challenge = self.error.find('challenge', recursive=False)
        if challenge:
            self.captcha_url = challenge.find('captcha-url', recursive=False).text + CAPTCHA_CALLBACK_PARAMETER
            self.message = f"Captcha received: {self.captcha_url}"
        else:
            self.captcha_url = None

    def solve_captcha_wizard(self, kik_client):
        if not self.is_captcha():
            return
        print(f"To continue, complete the captcha in this URL using a browser: {self.captcha_url}")
        captcha_response = input(
            "Next, intercept the request starting with 'https://kik.com/captcha-url' using F12, "
            "and paste the response parameter here: ")

        # Remove the 'response=' part if it exists
        # (if they just copy the response, .find('=') will return -1,
        # we add 1 to that to get 0, which is the start of the string, so it will still work)
        captcha_response = captcha_response[captcha_response.find('=') + 1:]
        self.submit_captcha_solution(kik_client, captcha_response)

    def submit_captcha_solution(self, kik_client, captcha_response: str):
        kik_client.login(kik_client.username, kik_client.password, captcha_response)


class SignUpError(KikCaptchaError):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)

        if self.is_dialog():
            pass
        elif self.is_captcha():
            self.message = f"A Captcha is required to sign up; URL: {self.captcha_url}"
        elif self.error.find('already-registered', recursive=False):
            self.message = "Email already registered"
        elif self.error.find('username-already-exists', recursive=False):
            self.message = "Username already registered"
        elif self.error.find('first-last-name-rejected', recursive=False):
            self.message = "Kik rejected the first or last name when creating the account"
        elif self.error.find('username-rejected', recursive=False):
            self.message = "Kik rejected the username when creating the account"
        elif self.error.find('invalid-birthday', recursive=False):
            self.message = "Kik rejected the birthday when creating the account"
        elif self.error.find('version-no-longer-supported', recursive=False):
            self.message = f"Client version ({kik_version_info["kik_version"]}) no longer supported for use with sign ups"
        elif self.error.find('verify-phone', recursive=False):
            self.message = "Phone verification is required to sign up (not implemented)"
        elif self.error.find('message', recursive=False):
            self.message = f"Custom message: {get_text_of_tag(self.error, 'message')}"
        elif self.error.find('internal-server-error', recursive=False):
            self.message = "Internal server error"
        elif self.error.find('bad-request', recursive=False):
            self.message = "Bad request"
        else:
            self.message = f"Unknown sign up error: {str(self.errors)}"

    def __str__(self):
        return self.message


class LoginError(KikCaptchaError):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)

        if self.is_dialog():
            pass
        elif self.is_captcha():
            self.message = f"A Captcha is required to log in; URL: {self.captcha_url}"
        elif self.error.find('not-registered', recursive=False):
            self.message = "Not Found (Not Registered)"
        elif self.error.find('password-mismatch', recursive=False):
            self.message = "Password mismatch"
        elif self.error.find('device-change-timeout', recursive=False):
            self.message = "Device change timeout"
        elif self.error.find('acct-terminated', recursive=False):
            self.message = "Account permanently banned or deactivated"
        elif self.error.find('message', recursive=False):
            self.message = f"Custom message: {get_text_of_tag(self.error, 'message')}"
        elif self.error.find('internal-server-error', recursive=False):
            self.message = "Internal server error"
        elif self.error.find('bad-request', recursive=False):
            self.message = "Bad request"
        else:
            self.message = f"Unknown login error: {str(self.error)}"

    def __str__(self):
        return self.message
