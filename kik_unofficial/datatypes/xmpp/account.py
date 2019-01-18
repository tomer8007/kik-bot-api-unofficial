from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils

from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement


class ChangeNameRequest(XMPPElement):
    def __init__(self, first_name, last_name):
        super().__init__()
        self.first_name = first_name
        self.last_name = last_name

    def serialize(self) -> bytes:
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:iq:user-profile">'
                '<first>{}</first>'
                '<last>{}</last>'
                '</query>'
                '</iq>').format(self.message_id, self.first_name, self.last_name)
        return data.encode()


class ChangePasswordRequest(XMPPElement):
    def __init__(self, old_password, new_password, email, username):
        super().__init__()
        self.old_password = old_password
        self.new_password = new_password
        self.email = email
        self.username = username

    def serialize(self):
        passkey_e = CryptographicUtils.key_from_password(self.email, self.old_password)
        passkey_u = CryptographicUtils.key_from_password(self.username, self.new_password)
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:iq:user-profile">'
                '<passkey-e>{}</passkey-e>'
                '<passkey-u>{}</passkey-u>'
                '</query>'
                '</iq>').format(self.message_id, passkey_e, passkey_u)
        return data.encode()


class ChangeEmailRequest(XMPPElement):
    def __init__(self, password, old_email, new_email):
        super().__init__()
        self.password = password
        self.old_email = old_email
        self.new_email = new_email

    def serialize(self):
        passkey_e = CryptographicUtils.key_from_password(self.old_email, self.password)
        data = ('<iq type="set" id="{}">'
                '<query xmlns="kik:iq:user-profile">'
                '<email>{}</email>'
                '<passkey-e>{}</passkey-e>'
                '</query>'
                '</iq>').format(self.message_id, self.new_email, passkey_e)
        return data.encode()
