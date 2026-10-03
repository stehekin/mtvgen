"""Lyric provider implementations for Chinese & global services."""

from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_kugou_lyrics(title: str, artist: str, duration: Optional[float] = None) -> Optional[str]:
    """Fetch synchronized LRC lyrics directly from Kugou Music API.

    Kugou has one of the largest libraries for Chinese, Cantonese, and Asian pop songs.
    """
    keyword = f"{title} {artist}".strip()
    logger.info(f"Searching Kugou Music for: '{keyword}'")

    try:
        # Step 1: Search track to get hash
        search_url = f"http://mobilecdn.kugou.com/api/v3/search/song?keyword={requests.utils.quote(keyword)}&page=1&pagesize=5"
        resp = requests.get(search_url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return None

        data = resp.json()
        info_list = data.get("data", {}).get("info", [])
        if not info_list:
            return None

        track_hash = info_list[0].get("hash")
        if not track_hash:
            return None

        # Step 2: Search lyrics candidates
        duration_sec = int(duration or 0)
        lrc_search_url = f"http://lyrics.kugou.com/search?ver=1&man=yes&client=pc&keyword={requests.utils.quote(keyword)}&duration={duration_sec}&hash={track_hash}"
        resp2 = requests.get(lrc_search_url, headers=HEADERS, timeout=8)
        if resp2.status_code != 200:
            return None

        candidates = resp2.json().get("candidates", [])
        if not candidates:
            return None

        cand = candidates[0]
        cand_id, accesskey = cand["id"], cand["accesskey"]

        # Step 3: Download LRC content
        dl_url = f"http://lyrics.kugou.com/download?ver=1&client=pc&id={cand_id}&accesskey={accesskey}&fmt=lrc&charset=utf8"
        resp3 = requests.get(dl_url, headers=HEADERS, timeout=8)
        if resp3.status_code != 200:
            return None

        content_b64 = resp3.json().get("content", "")
        if not content_b64:
            return None

        lrc = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
        if lrc.strip():
            logger.info(f"✓ Found synchronized lyrics on Kugou ({len(lrc)} chars)")
            return lrc
    except Exception as e:
        logger.warning(f"Kugou lyric search failed: {e}")

    return None


def fetch_netease_lyrics(title: str, artist: str) -> Optional[str]:
    """Fetch synchronized LRC lyrics directly from NetEase Cloud Music API."""
    keyword = f"{title} {artist}".strip()
    logger.info(f"Searching NetEase Cloud Music for: '{keyword}'")

    try:
        search_url = f"http://music.163.com/api/search/pc?limit=5&type=1&offset=0&s={requests.utils.quote(keyword)}"
        resp = requests.get(search_url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return None

        songs = resp.json().get("result", {}).get("songs", [])
        if not songs:
            return None

        song_id = songs[0]["id"]
        lyric_url = f"http://music.163.com/api/song/lyric?id={song_id}&lv=1"
        resp2 = requests.get(lyric_url, headers=HEADERS, timeout=8)
        if resp2.status_code != 200:
            return None

        lrc = resp2.json().get("lrc", {}).get("lyric", "")
        if lrc.strip():
            logger.info(f"✓ Found synchronized lyrics on NetEase ({len(lrc)} chars)")
            return lrc
    except Exception as e:
        logger.warning(f"NetEase lyric search failed: {e}")

    return None
