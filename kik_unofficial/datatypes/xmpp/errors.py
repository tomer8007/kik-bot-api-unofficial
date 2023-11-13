from bs4 import BeautifulSoup

from kik_unofficial.datatypes.xmpp.base_elements import XMPPResponse


class KikError(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        error = data.find("error")
        self.error_code = int(error['code'])
        self.type = error['type']
        self.errors = [e.name for e in error.children]
        self.message = str(self.errors)

    def __str__(self):
        return f'IqError code={self.error_code} type={self.type} errors={",".join(self.errors)}'


class SignUpError(KikError):
    error_messages = {
        409: "Already registered",
        406: "Captcha required"
    }

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)

        if self.error_code in self.error_messages:
            self.message = self.error_messages[self.error_code]

        if data.find('captcha-url'):
            self.captcha_url = data.find('captcha-url').text + "&callback_url=https://kik.com/captcha-url"
            self.message = f"a Captcha is required to sign up; URL: {self.captcha_url}"

    def __str__(self):
        return self.message


class LoginError(KikError):
    error_messages = {
        404: "Not Found (Not Registered)",
    }

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)

        if self.error_code == 406:
            if data.find('captcha-url'):
                self.captcha_url = data.find('captcha-url').text + "&callback_url=https://kik.com/captcha-url"
                self.message = "a Captcha is required to continue"
            else:
                self.message = "Password mismatch"
        elif self.error_code in self.error_messages:
            self.message = self.error_messages[self.error_code]

    def is_captcha(self):
        return self.raw_element.find('captcha-url')

    def solve_captcha_wizard(self, kik_client):
        if not self.is_captcha():
            return
        print(f"To continue, complete the captcha in this URL using a browser: {self.captcha_url}")
        captcha_response = input("Next, intercept the request starting with 'https://kik.com/captcha-url' using F12, "
                                 "and paste the response parameter here: ")

        # Remove the 'response=' part if it exists (if they just copy the response, .find('=') will return -1, we add 1 to that to get 0, which is the start of the string, so it will still work)
        captcha_response = captcha_response[captcha_response.find('=') + 1:]

        kik_client.login(kik_client.username, kik_client.password, captcha_response)

    def __str__(self):
        return self.message


class ServiceRequestError(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        error = data.error
        self.error_code = int(error['code'])
        self.type = error['type']
        self.message_id = data.attrs["id"]
