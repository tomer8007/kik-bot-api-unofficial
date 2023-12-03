import logging
import os
from threading import Thread

import requests
from kik_unofficial.device_configuration import kik_version_info
from kik_unofficial.datatypes.exceptions import KikApiException, KikUploadError
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils
from kik_unofficial.utilities.parsing_utilities import get_file_bytes

log = logging.getLogger('kik_unofficial')


def set_profile_picture(file, jid, username, password):
    url = 'https://profilepicsup.kik.com/profilepics'
    send(url, file, jid, username, password)


def set_background_picture(file, jid, username, password):
    url = 'https://profilepicsup.kik.com/profilepics?extension_type=BACKGROUND'
    send(url, file, jid, username, password)


def send(url, filename, jid, username, password):
    password_key = CryptographicUtils.key_from_password(username, password)
    if not os.path.isfile(filename):
        raise KikApiException("File doesn't exist")
    headers = {
        'x-kik-jid': jid,
        'x-kik-password': password_key,
        'User-Agent': f'Kik/{kik_version_info["kik_version"]} (Android 7.1.2) Dalvik/2.1.0 (Linux; U; Android 7.1.2; Nexus 7 Build/NJH47F)',
    }
    Thread(target=picture_upload_thread, args=(url, filename, headers), name='KikProfilepics').start()


def picture_upload_thread(url, filename, headers):
    picture_data = get_file_bytes(filename)
    log.debug('Uploading picture')
    r = requests.post(url, data=picture_data, headers=headers)
    if r.status_code != 200:
        raise KikUploadError(r.status_code, r.reason)
