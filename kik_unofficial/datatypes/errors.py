from bs4 import BeautifulSoup

from kik_unofficial.datatypes.xmpp.base_elements import XMPPResponse


class KikError(XMPPResponse):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        error = data.find("error")
        self.code = int(error['code'])
        self.type = error['type']
        self.errors = [e.name for e in error.children]
        self.message = str(self.errors)

    def __str__(self):
        return "IqError code={} type={} errors={}".format(self.code, self.type, ",".join(self.errors))


class SignUpError(KikError):
    error_messages = {
        409: "Already registered",
        406: "Captcha required"
    }

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        if data.find('captcha-url'):
            self.captcha_url = data.find('captcha-url').text + "&callback_url=https://kik.com/captcha-url"

        if self.code in self.errors:
            self.message = self.error_messages[self.code]


class LoginError(KikError):
    error_messages = {
        404: "Not Found (Not Registered)",
    }

    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        if self.code == 406:
            if data.find('captcha-url'):
                self.captcha_url = data.find('captcha-url').text + "&callback_url=https://kik.com/captcha-url"
                self.message = "Captcha required"
            else:
                self.message = "Password mismatch"
        else:
            if self.code in self.errors:
                self.message = self.error_messages[self.code]
