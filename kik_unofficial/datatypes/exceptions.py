class KikErrorException(Exception):
    def __init__(self, xml_error, message=None):
        self.message = message
        self.xml_error = xml_error

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if self.message is not None:
            return self.message
        else:
            if "prettify" in dict(self.xml_error):
                error_string = self.xml_error.prettify()
            else:
                error_string = self.xml_error
            return "Kik error: \r\n" + error_string


class KikCaptchaException(KikErrorException):
    def __init__(self, xml_error, message, captcha_url):
        super().__init__(xml_error, message)
        self.captcha_url = captcha_url


class KikLoginException(KikErrorException):
    pass


class KikInvalidAckException(KikErrorException):
    pass


class KikEmptyResponseException(KikErrorException):
    pass


class KikApiException(Exception):
    pass


class KikUploadError(Exception):
    def __init__(self, status_code, reason=None):
        self.status_code = reason
        self.reason = reason

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if self.reason is None:
            return self.status_code
        return f"[{self.status_code}] {self.reason}"
