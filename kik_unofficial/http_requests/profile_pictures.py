import logging
import os
from threading import Thread

import requests
from kik_unofficial.device_configuration import kik_version_info
from kik_unofficial.datatypes.exceptions import KikApiException, KikUploadError
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils
from kik_unofficial.utilities.parsing_utilities import get_file_bytes

log = logging.getLogger('kik_unofficial')

BASE_URL = 'https://profilepicsup.kik.com/profilepics'


def set_profile_picture(file, jid, username, password):
    send(BASE_URL, file, jid, username, password)


def set_background_picture(file, jid, username, password):
    url = f'{BASE_URL}?extension_type=BACKGROUND'
    send(url, file, jid, username, password)


def set_group_picture(image_file, user_jid, group_jid, username, password, silent: bool = False):
    url = f'{BASE_URL}?g={group_jid}'
    if silent:
        url += '&silent=true'
    send(url, image_file, user_jid, username, password)


def send(url, filename, jid, username, password):
    if not os.path.isfile(filename):
        raise KikApiException("File doesn't exist")
    headers = {
        'x-kik-jid': jid,
        'x-kik-password': CryptographicUtils.key_from_password(username, password),
        'User-Agent': f'Kik/{kik_version_info["kik_version"]} (Android 7.1.2) Dalvik/2.1.0 (Linux; U; Android 7.1.2; Nexus 7 Build/NJH47F)',
    }
    Thread(target=picture_upload_thread, args=(url, filename, headers), name='KikProfilePics').start()


def picture_upload_thread(url, filename, headers):
    picture_data = get_file_bytes(filename)
    log.debug('Uploading picture')

    # Profile picture uploads can fail without a known cause.
    # Retry up to 3 times.
    max_retries = 3

    for retry_number in range(max_retries):
        r = requests.post(url, data=picture_data, headers=headers)
        if r.status_code == 200:
            if retry_number == max_retries - 1:
                raise KikUploadError(r.status_code, r.reason)
            else:
                log.warning("Uploading picture failed with %s, executing retry (%s/%s)",
                            r.status_code, retry_number + 1, max_retries)
        else:
            log.debug("Uploading picture succeeded")
            return
