"""Work out which champion to look for."""
from __future__ import annotations

from . import config as config_mod
from . import liveclient


def pick(cfg: dict, override: str | None = None) -> str | None:
    """--champion flag > config.json > the running game (Live Client API) > None."""
    if override:
        return override
    if not config_mod.champion_is_auto(cfg):
        return str(cfg["champion"]).strip()
    data = liveclient.fetch_once(timeout=1.5)
    info = liveclient.parse(data) if data else None
    return info["champion"] if info else None
