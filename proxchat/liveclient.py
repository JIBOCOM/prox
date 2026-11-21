"""Riot's official Live Client Data API (local, read-only, only while a game is running).

https://127.0.0.1:2999/liveclientdata/allgamedata uses a self-signed certificate, so
certificate checks are turned off for this one local address only.
"""
from __future__ import annotations

import json
import ssl
import threading
import time
import urllib.error
import urllib.request

URL = "https://127.0.0.1:2999/liveclientdata/allgamedata"
RAW_PREFIX = "game_character_displayname_"

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE


def fetch_once(timeout: float = 1.0) -> dict | None:
    try:
        with urllib.request.urlopen(URL, timeout=timeout, context=_SSL) as resp:
            return json.loads(resp.read())
    except (OSError, ValueError):
        return None


def parse(data: dict) -> dict | None:
    """-> {'player', 'champion', 'is_dead'} for the active player, or None (e.g. spectating)."""
    active = data.get("activePlayer") or {}
    ids = {active.get(k) for k in ("riotId", "summonerName")} - {None, ""}
    for p in data.get("allPlayers") or []:
        if {p.get(k) for k in ("riotId", "summonerName")} & ids:
            raw = p.get("rawChampionName", "")
            champ = raw[len(RAW_PREFIX):] if raw.startswith(RAW_PREFIX) else p.get("championName", "")
            return {
                "player": p.get("riotId") or p.get("summonerName") or "player",
                "champion": champ,
                "is_dead": bool(p.get("isDead")),
            }
    return None


class LiveClient(threading.Thread):
    """Polls the API once a second in the background. Read the attributes from any thread."""

    def __init__(self, interval: float = 1.0):
        super().__init__(daemon=True)
        self.interval = interval
        self.connected = False
        self.ever_connected = False
        self.last_ok = 0.0
        self.player: str | None = None
        self.champion: str | None = None
        self.is_dead = False
        self._halt = threading.Event()

    def run(self) -> None:
        while not self._halt.is_set():
            data = fetch_once()
            info = parse(data) if data else None
            if info:
                self.player, self.champion, self.is_dead = info["player"], info["champion"], info["is_dead"]
                self.connected = self.ever_connected = True
                self.last_ok = time.time()
            else:
                self.connected = False
                self.is_dead = False
            self._halt.wait(self.interval)

    def stop(self) -> None:
        self._halt.set()
