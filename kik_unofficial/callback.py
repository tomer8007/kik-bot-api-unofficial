from kik_unofficial.message.roster import RosterResponse
from kik_unofficial.message.unauthorized.checkunique import CheckUniqueResponse
from kik_unofficial.message.unauthorized.register import RegisterError, RegisterResponse, LoginResponse


class KikCallback:
    def on_check_unique(self, response: CheckUniqueResponse):
        raise NotImplementedError

    def on_register_error(self, response: RegisterError):
        raise NotImplementedError

    def on_register(self, response: RegisterResponse):
        raise NotImplementedError

    def on_login(self, response: LoginResponse):
        raise NotImplementedError

    def on_roster(self, response: RosterResponse):
        raise NotImplementedError

    def on_authorized(self):
        raise NotImplementedError