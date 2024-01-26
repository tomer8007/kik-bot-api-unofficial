from __future__ import annotations

import io
import logging
import os
import pathlib
from threading import Thread
from typing import Mapping

import requests
from kik_unofficial.device_configuration import kik_version_info
from kik_unofficial.datatypes.exceptions import KikApiException, KikUploadError
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils
from kik_unofficial.utilities.parsing_utilities import get_file_bytes

log = logging.getLogger("kik_unofficial")

BASE_URL = "https://profilepicsup.kik.com/profilepics"


def set_profile_picture(file: str or bytes or pathlib.Path or io.IOBase, jid: str, username: str, password: str):
    send(BASE_URL, file, jid, username, password)


def set_background_picture(file: str or bytes or pathlib.Path or io.IOBase, jid: str, username: str, password: str):
    url = f"{BASE_URL}?extension_type=BACKGROUND"
    send(url, file, jid, username, password)


def set_group_picture(file: str or bytes or pathlib.Path or io.IOBase, user_jid: str, group_jid: str, username: str, password: str, silent: bool = False):
    url = f"{BASE_URL}?g={group_jid}"
    if silent:
        url += "&silent=1"
    send(url, file, user_jid, username, password)


def send(url: str, file: str or bytes or pathlib.Path or io.IOBase, jid: str, username: str, password: str):
    if not os.path.isfile(file):
        raise KikApiException("File doesn't exist")
    headers = {
        "x-kik-jid": jid,
        "x-kik-password": CryptographicUtils.key_from_password(username, password),
        "User-Agent": f'Kik/{kik_version_info["kik_version"]} (Android 7.1.2) Dalvik/2.1.0 (Linux; U; Android 7.1.2; Nexus 7 Build/NJH47F)',
    }
    Thread(target=picture_upload_thread, args=(url, file, headers), name="KikProfilePics").start()


def picture_upload_thread(url: str, file: str or bytes or pathlib.Path or io.IOBase, headers: Mapping[str, str | bytes]):
    picture_data = get_file_bytes(file)
    log.debug("Uploading picture")

    # Profile picture uploads can fail without a known cause.
    # Retry up to 3 times.
    max_retries = 3

    for retry_number in range(max_retries):
        r = requests.post(url, data=picture_data, headers=headers)
        if r.status_code == 200:
            if retry_number == max_retries - 1:
                raise KikUploadError(r.status_code, r.reason)
            else:
                log.warning("Uploading picture failed with %s, executing retry (%s/%s)", r.status_code, retry_number + 1, max_retries)
        else:
            log.debug("Uploading picture succeeded")
            return
