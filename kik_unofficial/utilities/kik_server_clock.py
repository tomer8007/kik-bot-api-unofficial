import time


class KikServerClock:
    """
    Keeps track of the client to server timestamp offset.

    This should be used when sending stanzas that contain timestamps.
    """

    _server_time_offset = 0  # type: int

    @staticmethod
    def get_server_time() -> int:
        return KikServerClock.get_system_time() + KikServerClock._server_time_offset

    @staticmethod
    def recalculate_offset(kik_time: int) -> int:
        if kik_time > 0:
            KikServerClock._server_time_offset = kik_time - KikServerClock.get_system_time()
        return KikServerClock._server_time_offset

    @staticmethod
    def get_system_time() -> int:
        return int(round(time.time() * 1000))
