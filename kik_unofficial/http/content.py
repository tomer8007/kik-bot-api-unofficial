import hashlib
import logging
import requests
import time
from threading import Thread

from kik_unofficial.datatypes.exceptions import KikUploadError
from kik_unofficial.datatypes.xmpp.chatting import OutgoingChatImage, OutgoingVideoMessage
from kik_unofficial.datatypes.xmpp.errors import ServiceRequestError
from kik_unofficial.utilities.cryptographic_utilities import CryptographicUtils
from kik_unofficial.device_configuration import kik_version_info

logger = logging.getLogger("kik_unofficial")
SALT = "YA=57aSA!ztajE5"


def upload_gallery_image(image: OutgoingChatImage, jid, username, password):
    url = f"https://platform.kik.com/content/files/{image.content_id}"
    send_gallery_image(image, url, jid, username, password)


def send_gallery_image(image, url, jid, username, password):
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
        target=media_upload_thread,
        args=(image, url, headers, "image"),
        name='KikContent'
    ).start()


def upload_gallery_video(video: OutgoingVideoMessage, jid, username, password):
    url = f"https://platform.kik.com/content/files/{video.content_id}"
    send_gallery_video(video, url, jid, username, password)


def send_gallery_video(video, url, jid, username, password):
    username_passkey = CryptographicUtils.key_from_password(username, password)
    app_id = "com.kik.ext.video-gallery"
    v = SALT + video.content_id + app_id

    verification = hashlib.sha1(v.encode('UTF-8')).hexdigest()
    headers = {
        'Host': 'platform.kik.com',
        'Connection': 'Keep-Alive',
        'Content-Length': str(video.parsed_video['size']),
        'User-Agent': f'Kik/{kik_version_info["kik_version"]} (Android 7.1.2) Content',
        'x-kik-jid': jid,
        'x-kik-password': username_passkey,
        'x-kik-verification': verification,
        'x-kik-app-id': app_id,
        'x-kik-content-chunks': '1',
        'x-kik-content-size': str(video.parsed_video['size']),
        'x-kik-content-md5': video.parsed_video['MD5'],
        'x-kik-chunk-number': '0',
        'x-kik-chunk-md5': video.parsed_video['MD5'],
        'Content-Type': 'video/mp4',
        'x-kik-content-extension': '.mp4'
    }

    Thread(
        target=media_upload_thread,
        args=(video, url, headers, "video"),
        name='KikVideoContent'
    ).start()


def media_upload_thread(media, url, headers, media_type="image"):
    r = None
    max_retries = 5
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            logger.debug(f'Uploading Media {media_type}')
            if media_type == "image":
                media_data = media.parsed_image["original"]
            elif media_type == "video":
                media_data = media.parsed_video['original']
            else:
                break

            r = requests.put(url, data=media_data, headers=headers)
            r.raise_for_status()
            logger.debug(f'Media {media_type} uploaded successfully')
            break
        except requests.exceptions.HTTPError as e:
            if r is not None and r.status_code in [500, 502, 503, 504]:
                logger.warning(f'Failed to upload media {media_type}, attempt {attempt + 1}: {str(e)}')
                if attempt < max_retries - 1:
                    logger.debug(f'Retrying in {retry_delay} seconds...')
                    time.sleep(retry_delay)
                continue
            else:
                logger.error(f'Failed to upload media {media_type}: {str(e)}')
                break
        except Exception as e:
            logger.error(f'An error occurred while uploading media {media_type}: {str(e)}')
            break
