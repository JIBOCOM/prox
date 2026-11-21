"""Minimap pixels -> Summoner's Rift game units -> Mumble metres.

Game units: origin at the bottom-left (blue base), x to the right, y up the screen.
The minimap shows the whole map, so it's a straight scale (y flipped, because image
rows go down). 100 game units = 1 Mumble metre, so the Rift is about 150 m wide.
"""
from __future__ import annotations

UNITS_PER_METRE = 100.0

# Dead players all go to the same spot 1 km above the map: the living can't hear
# them (or be heard by them), but the dead can talk to each other.
GRAVEYARD = (0.0, 1000.0, 0.0)


def minimap_to_map(px: float, py: float, minimap_size: int, map_cfg: dict) -> tuple[float, float]:
    gx = px / minimap_size * map_cfg["width"]
    gy = (1.0 - py / minimap_size) * map_cfg["height"]
    return gx, gy


def map_to_mumble(gx: float, gy: float) -> tuple[float, float, float]:
    """Mumble is left-handed: x right, y up, z forward. The map lies flat (y = 0)."""
    return gx / UNITS_PER_METRE, 0.0, gy / UNITS_PER_METRE


def radius_to_metres(game_units: float) -> float:
    return game_units / UNITS_PER_METRE
