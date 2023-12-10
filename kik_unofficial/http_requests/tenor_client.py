import requests


class KikTenorClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise Exception("A tenor.com API key is required to search for GIFs")
        self.headers = {'X-Goog-Api-Key': api_key}

    def search_for_gif(self, search_term: str) -> tuple[bytes, dict]:
        params = {'q': search_term, 'limit': '1'}
        r = requests.get(f"https://tenor.googleapis.com/v2/search", params=params, headers=self.headers)
        r.raise_for_status()

        gif = r.json()['results'][0]
        media_formats = gif["media_formats"]

        thumbnail_url = media_formats["nanogifpreview"]["url"]
        thumbnail_bytes = requests.get(thumbnail_url).content

        return thumbnail_bytes, media_formats
