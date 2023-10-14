import hashlib
import logging
import requests
import time
from threading import Thread

from kik_unofficial.datatypes.exceptions import KikUploadError
from kik_unofficial.datatypes.xmpp.chatting import OutgoingChatImage
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils
from kik_unofficial.device_configuration import kik_version_info


log = logging.getLogger('kik_unofficial')
SALT = "YA=57aSA!ztajE5"


def upload_gallery_image(client, image: OutgoingChatImage, jid, username, password):
    url = f"https://platform.kik.com/content/files/{image.content_id}"
    send_gallery_image(client, image, url, jid, username, password)


def send_gallery_image(client, image, url, jid, username, password):
    username_passkey = CryptographicUtils.key_from_password(username, password)
    app_id = "com.kik.ext.gallery"
    v = SALT + image.content_id + app_id

    verification = hashlib.sha1(v.encode('UTF-8')).hexdigest()
    headers = {
        'Host': 'platform.kik.com',
        'Connection': 'Keep-Alive',
        'Content-Length': str(image.parsed_image['size']),
        'User-Agent': f'Kik/{kik_version_info["kik_version"]} (Android 7.1.2) Content',
        'x-kik-jid': jid,
        'x-kik-password': username_passkey,
        'x-kik-verification': verification,
        'x-kik-app-id': app_id,
        'x-kik-content-chunks': '1',
        'x-kik-content-size': str(image.parsed_image['size']),
        'x-kik-content-md5': image.parsed_image['MD5'],
        'x-kik-chunk-number': '0',
        'x-kik-chunk-md5': image.parsed_image['MD5'],
        'x-kik-sha1-original': image.parsed_image['SHA1'].upper(),
        'x-kik-sha1-scaled': image.parsed_image['SHA1Scaled'].upper(),
        'x-kik-blockhash-scaled': image.parsed_image['blockhash'].upper(),
        'Content-Type': 'image/jpeg',
        'x-kik-content-extension': '.jpg'
    }

    Thread(
        target=image_upload_thread,
        args=(client, image, url, headers),
        name='KikContent'
    ).start()


def image_upload_thread(client, image, url, headers):
    log.debug('Uploading Image')
    r = requests.put(url, data=image.parsed_image["original"], headers=headers)
    if r.status_code != 200:
        raise KikUploadError(r.status_code, r.reason)
    else:
        client.send_stanza(image.serialize(), "Image")
