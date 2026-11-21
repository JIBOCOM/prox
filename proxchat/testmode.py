"""Test mode: run detection on saved minimap screenshots in /samples (no game needed).

Results are printed and annotated copies are written to /samples/out.
The champion comes from --champion, else from the file name
(minimap_<Champion>_....png, which calibration's P key writes), else from config.json.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import cv2

from . import config as config_mod
from . import draw
from .ddragon import ChampionError, get_icon, resolve
from .detect import ChampionDetector
from .mapcoords import minimap_to_map

SAMPLES_DIR = config_mod.ROOT / "samples"
OUT_DIR = SAMPLES_DIR / "out"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp"}


def _champion_for(path: Path, cfg: dict, override: str | None) -> str | None:
    if override:
        return override
    parts = path.stem.split("_")
    if len(parts) >= 3 and parts[0] == "minimap" and not parts[1].isdigit():
        return parts[1]
    if not config_mod.champion_is_auto(cfg):
        return str(cfg["champion"])
    return None


def run(cfg: dict, champion_override: str | None = None, show: bool = False) -> int:
    files = sorted(p for p in SAMPLES_DIR.glob("*") if p.suffix.lower() in IMAGE_EXT)
    if not files:
        print(f"No screenshots in {SAMPLES_DIR}. Save some with calibrate (P key) first.")
        return 1
    OUT_DIR.mkdir(exist_ok=True)

    icons: dict[str, object] = {}
    found = 0
    sizes = Counter()
    for path in files:
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            print(f"{path.name}: can't read, skipped")
            continue
        champ = _champion_for(path, cfg, champion_override)
        if not champ:
            print(f"{path.name}: which champion? Pass --champion NAME (config says \"auto\")")
            continue
        try:
            cid = resolve(champ)
            if cid not in icons:
                icons[cid] = get_icon(cid)
        except ChampionError as e:
            print(f"{path.name}: {e}")
            continue

        size = img.shape[1]  # samples are minimap captures, so width = minimap size
        det = ChampionDetector(icons[cid], size, cfg["detection"]).detect(img)
        view = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
        draw.detection(view, det, zoom=2)
        if det:
            found += 1
            sizes[(det.diameter, det.crop)] += 1
            gx, gy = minimap_to_map(det.x, det.y, size, cfg["map"])
            msg = (f"{cid}: px ({det.x:.0f},{det.y:.0f}) map ({gx:.0f},{gy:.0f}) "
                   f"score {det.score:.2f} d={det.diameter} crop={det.crop}")
            print(f"{path.name}: FOUND  {msg}")
        else:
            msg = f"{cid}: not found"
            print(f"{path.name}: MISSED {cid}")
        draw.text(view, [msg], colour=(0, 255, 0) if det else (0, 0, 255))
        cv2.imwrite(str(OUT_DIR / f"{path.stem}_result.png"), view)
        if show:
            cv2.imshow("Test mode (any key = next, Q = stop)", view)
            if cv2.waitKey(0) & 0xFF in (ord("q"), 27):
                break

    if show:
        cv2.destroyAllWindows()
    print(f"\nFound the champion in {found}/{len(files)} screenshots. Annotated copies: {OUT_DIR}")
    if sizes:
        (d, crop), _ = sizes.most_common(1)[0]
        print(f"Most common icon size: diameter {d}px, crop {crop}. To speed up detection you can set\n"
              f'  "detection": {{ "icon_diameter": {d}, "icon_crop": {crop} }}  in config.json')
    return 0
