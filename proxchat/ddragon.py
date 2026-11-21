"""Champion icons from Riot Data Dragon (public CDN), cached in /cache."""
from __future__ import annotations

import json
import urllib.request
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from .config import ROOT

BASE = "https://ddragon.leagueoflegends.com"
CACHE = ROOT / "cache"
INDEX_FILE = CACHE / "champions.json"


class ChampionError(Exception):
    pass


def _norm(s: str) -> str:
    """'Kai'Sa' -> 'kaisa', 'Nunu & Willump' -> 'nunuwillump'."""
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read()


@lru_cache(maxsize=1)
def _champion_index() -> tuple[str, dict]:
    """Return (version, {champion id: info}). Falls back to the cache when offline."""
    try:
        version = json.loads(_download(f"{BASE}/api/versions.json"))[0]
        data = json.loads(_download(f"{BASE}/cdn/{version}/data/en_US/champion.json"))
        CACHE.mkdir(exist_ok=True)
        INDEX_FILE.write_text(json.dumps({"version": version, "data": data["data"]}), encoding="utf-8")
        return version, data["data"]
    except (OSError, ValueError, KeyError) as e:
        if INDEX_FILE.exists():
            cached = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            return cached["version"], cached["data"]
        raise ChampionError(f"Can't reach Riot Data Dragon and nothing is cached yet ({e})")


def resolve(name: str) -> str:
    """Champion display name, id or raw name -> Data Dragon id ('Wukong' -> 'MonkeyKing')."""
    _, champs = _champion_index()
    wanted = _norm(name)
    for cid, info in champs.items():
        if wanted in (_norm(cid), _norm(info["name"])):
            return cid
    raise ChampionError(f"Unknown champion '{name}'. Use the English name, e.g. \"Ahri\" or \"Kai'Sa\".")


def get_icon(name: str) -> np.ndarray:
    """Return the champion's square portrait as BGR (120x120)."""
    version, _ = _champion_index()
    cid = resolve(name)
    path = CACHE / "icons" / version / f"{cid}.png"
    if not path.exists():
        try:
            png = _download(f"{BASE}/cdn/{version}/img/champion/{cid}.png")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(png)
        except OSError as e:
            older = sorted((CACHE / "icons").glob(f"*/{cid}.png"))
            if not older:
                raise ChampionError(f"Can't download the icon for {cid}: {e}")
            path = older[-1]
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise ChampionError(f"Icon file is unreadable: {path}")
    return img


def display_name(name: str) -> str:
    _, champs = _champion_index()
    return champs[resolve(name)]["name"]
