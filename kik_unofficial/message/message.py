from kik_unofficial.cryptographic_utils import KikCryptographicUtils


class Message:
    def __init__(self):
        self.message_id = KikCryptographicUtils.make_kik_uuid()

    def serialize(self) -> bytes:
        raise NotImplemented()
