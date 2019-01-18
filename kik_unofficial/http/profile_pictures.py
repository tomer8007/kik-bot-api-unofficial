import logging
import os
from threading import Thread

import requests
from kik_unofficial.datatypes.exceptions import KikApiException
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils

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
        'User-Agent': 'Kik/13.0.0.7521 (Android 7.1.2) Dalvik/2.1.0 (Linux; U; Android 7.1.2; Nexus 7 Build/NJH47F)',
    }
    Thread(target=picture_upload_thread, args=(url, filename, headers), name='KikProfilepics').start()


def picture_upload_thread(url, filename, headers):
    with open(filename, 'rb') as picture:
        picture_data = picture.read()
    log.debug('Uploading picture')
    r = requests.post(url, data=picture_data, headers=headers)
    if r.status_code != 200:
        raise KikApiException(r.status_code)
