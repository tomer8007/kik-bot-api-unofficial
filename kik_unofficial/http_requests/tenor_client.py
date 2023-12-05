import requests
import base64
from io import BytesIO
from PIL import Image


class KikTenorClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise Exception("A tenor.com API key is required to search for GIFs")
        self.headers = {'X-Goog-Api-Key': api_key}

    def search_for_gif(self, search_term: str):
        params = {'q': search_term, 'limit': '1'}
        r = requests.get(f"https://tenor.googleapis.com/v2/search", params=params, headers=self.headers)
        r.raise_for_status()

        gif = r.json()['results'][0]
        media_formats = gif["media_formats"]

        thumbnail_url = media_formats["nanogifpreview"]["url"]
        buffer = BytesIO()
        thumbnail = Image.open(BytesIO(requests.get(thumbnail_url).content))
        thumbnail.convert("RGB").save(buffer, format="JPEG")

        base64_thumbnail = base64.b64encode(buffer.getvalue()).decode('ascii')
        return base64_thumbnail, media_formats
