"""Load, validate and save config.json."""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"

DEFAULTS = {
    "champion": "auto",
    "minimap": {"monitor": 1, "left": 1645, "top": 805, "size": 270},
    "capture_fps": 5,
    "hearing_radius": 2500,
    "context": "lol-custom-friends",
    "detection": {"match_threshold": 0.7, "icon_diameter": 0, "icon_crop": 0},
    "map": {"width": 14870, "height": 14980},
    "death_detection": True,
}


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _fail(msg: str):
    raise SystemExit(f"config.json: {msg}")


def load(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        raise SystemExit(f"Config file not found: {path}")
    try:
        user = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"config.json is not valid JSON (line {e.lineno}): {e.msg}")
    cfg = _merge(DEFAULTS, user)

    mm = cfg["minimap"]
    for key in ("monitor", "left", "top", "size"):
        if not isinstance(mm.get(key), int):
            _fail(f"minimap.{key} must be a whole number")
    if mm["size"] < 50:
        _fail("minimap.size looks too small (< 50 px)")
    if not (1 <= cfg["capture_fps"] <= 30):
        _fail("capture_fps must be between 1 and 30")
    if cfg["hearing_radius"] <= 0:
        _fail("hearing_radius must be positive")
    if not str(cfg["champion"]).strip():
        _fail('champion must be a name like "Ahri", or "auto"')
    if not str(cfg["context"]).strip():
        _fail("context must not be empty (and must be the same for every player)")
    if not (0.2 <= cfg["detection"]["match_threshold"] <= 0.99):
        _fail("detection.match_threshold must be between 0.2 and 0.99")
    if cfg["map"]["width"] <= 0 or cfg["map"]["height"] <= 0:
        _fail("map.width and map.height must be positive")
    return cfg


def champion_is_auto(cfg: dict) -> bool:
    return str(cfg["champion"]).strip().lower() == "auto"


def save_minimap(minimap: dict, path: Path = CONFIG_PATH) -> None:
    """Write only the minimap block back, keeping the user's other settings as-is."""
    data = json.loads(path.read_text(encoding="utf-8"))
    data["minimap"] = {k: int(minimap[k]) for k in ("monitor", "left", "top", "size")}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
