"""Small HTTP layer with retry/backoff. The session is injectable so tests never touch the network."""
import time

import requests

RETRY_STATUS = {429, 500, 502, 503, 504}


class HttpClient:
    def __init__(self, session=None, retries=3, backoff=1.0,
                 user_agent="scholar-ingest/0.1 (mailto:your.email@example.com)"):
        self.session = session or requests.Session()
        self.retries = retries
        self.backoff = backoff
        self.user_agent = user_agent

    def get_json(self, url, params=None, headers=None):
        """GET a URL and return parsed JSON. Returns None on 404. Retries on 429/5xx."""
        merged = {"User-Agent": self.user_agent, "Accept": "application/json"}
        merged.update(headers or {})
        for attempt in range(self.retries):
            resp = self.session.get(url, params=params, headers=merged, timeout=30)
            if resp.status_code == 404:
                return None
            if resp.status_code in RETRY_STATUS:
                time.sleep(self.backoff * (2 ** attempt))
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError(f"Giving up on {url} after {self.retries} attempts")
