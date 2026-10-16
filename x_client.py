"""Posts to X (Twitter) with the v2 API, signed with OAuth 1.0a user keys."""
from __future__ import annotations

import logging
import time
from typing import Optional

import requests
from requests_oauthlib import OAuth1

log = logging.getLogger(__name__)

API = "https://api.x.com/2"


class XError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"X API error {status}: {body}")
        self.status = status


class XClient:
    def __init__(self, api_key: str, api_secret: str, access_token: str, access_token_secret: str):
        self.session = requests.Session()
        self.session.auth = OAuth1(api_key, api_secret, access_token, access_token_secret)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        for attempt in range(3):
            resp = self.session.request(method, API + path, timeout=60, **kwargs)
            if resp.status_code == 429:
                reset = int(resp.headers.get("x-rate-limit-reset", time.time() + 60))
                wait = min(max(reset - time.time(), 5), 900)
                log.warning("X rate limit hit, waiting %ds", wait)
                time.sleep(wait)
                continue
            if resp.status_code >= 500 and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            if not resp.ok:
                raise XError(resp.status_code, resp.text[:500])
            return resp.json()
        raise XError(429, "still rate limited after retries")

    def me(self) -> str:
        return self._request("GET", "/users/me")["data"]["username"]

    def upload_image(self, data: bytes, mime: str) -> str:
        ext = "png" if mime == "image/png" else "jpg"
        result = self._request(
            "POST", "/media/upload",
            files={"media": (f"nft.{ext}", data, mime)},
            data={"media_category": "tweet_image"},
        )
        return result["data"]["id"]

    def post(self, text: str, media_id: Optional[str] = None) -> str:
        body: dict = {"text": text}
        if media_id:
            body["media"] = {"media_ids": [media_id]}
        return self._request("POST", "/tweets", json=body)["data"]["id"]
