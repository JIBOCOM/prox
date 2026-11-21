"""Calibration mode: live view of the captured minimap, with keys to move/resize the box,
and the detected champion position drawn on top."""
from __future__ import annotations

import time
from datetime import datetime

import cv2

from . import champion as champion_mod
from . import config as config_mod
from . import draw
from .capture import MinimapCapture
from .ddragon import ChampionError, get_icon, resolve
from .detect import ChampionDetector
from .mapcoords import minimap_to_map

SAMPLES_DIR = config_mod.ROOT / "samples"

WIN_MINIMAP = "Minimap capture"
WIN_OVERVIEW = "Screen overview (red box = capture area)"

# cv2.waitKeyEx codes for arrow keys on Windows
KEY_LEFT, KEY_UP, KEY_RIGHT, KEY_DOWN = 2424832, 2490368, 2555904, 2621440

HELP = [
    "Arrows: move 1px   WASD: move 10px",
    "+ / - : resize     C: save to config.json",
    "P: save sample to /samples   Q/Esc: quit",
]


def _window_closed(name: str) -> bool:
    try:
        return cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def run(cfg: dict, champion_override: str | None = None) -> None:
    cap = MinimapCapture(cfg["minimap"])
    mm = dict(cap.cfg)
    frame_delay = 1.0 / cfg["capture_fps"]
    status, status_until = "", 0.0

    champ = champion_mod.pick(cfg, champion_override)
    icon, champ_id = None, None
    if champ:
        try:
            champ_id = resolve(champ)
            icon = get_icon(champ_id)
            print(f"Looking for: {champ_id}")
        except ChampionError as e:
            print(f"Detection off: {e}")
    else:
        print('Detection off: champion is "auto" and no game is running. '
              "Start a game, or pass --champion Ahri.")

    def make_detector():
        return ChampionDetector(icon, mm["size"], cfg["detection"]) if icon is not None else None

    detector = make_detector()

    cv2.namedWindow(WIN_MINIMAP, cv2.WINDOW_AUTOSIZE)
    cv2.namedWindow(WIN_OVERVIEW, cv2.WINDOW_AUTOSIZE)
    cv2.moveWindow(WIN_OVERVIEW, 20, 20)
    cv2.moveWindow(WIN_MINIMAP, 20, 600)
    print("Calibration running. Click one of the windows, then use the keys shown on screen.")

    try:
        while True:
            start = time.perf_counter()
            raw = cap.grab()

            # Minimap view, zoomed x2
            view = cv2.resize(raw, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
            lines = [f"x={mm['left']} y={mm['top']} size={mm['size']}"]
            if detector:
                det = detector.detect(raw)
                draw.detection(view, det, zoom=2)
                if det:
                    gx, gy = minimap_to_map(det.x, det.y, mm["size"], cfg["map"])
                    lines.append(f"{champ_id}: px ({det.x:.0f},{det.y:.0f})  score {det.score:.2f}  d={det.diameter}")
                    lines.append(f"map ({gx:.0f}, {gy:.0f})")
                else:
                    lines.append(f"{champ_id}: not found (best {detector.last_score:.2f})")
            if time.time() < status_until:
                lines.append(status)
            draw.text(view, lines)
            cv2.imshow(WIN_MINIMAP, view)

            # Overview: whole monitor scaled down, capture box in red
            full = cap.grab_monitor()
            scale = 960 / full.shape[1]
            small = cv2.resize(full, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            p1 = (int(mm["left"] * scale), int(mm["top"] * scale))
            p2 = (int((mm["left"] + mm["size"]) * scale), int((mm["top"] + mm["size"]) * scale))
            cv2.rectangle(small, p1, p2, (0, 0, 255), 2)
            draw.text(small, HELP)
            cv2.imshow(WIN_OVERVIEW, small)

            wait_ms = max(1, int((frame_delay - (time.perf_counter() - start)) * 1000))
            key = cv2.waitKeyEx(wait_ms)

            if _window_closed(WIN_MINIMAP) or _window_closed(WIN_OVERVIEW):
                break
            if key == -1:
                continue
            ch = chr(key).lower() if 0 <= key < 256 else ""
            old_size = mm["size"]
            moved = True
            if key == KEY_LEFT:
                mm["left"] -= 1
            elif key == KEY_RIGHT:
                mm["left"] += 1
            elif key == KEY_UP:
                mm["top"] -= 1
            elif key == KEY_DOWN:
                mm["top"] += 1
            elif ch == "a":
                mm["left"] -= 10
            elif ch == "d":
                mm["left"] += 10
            elif ch == "w":
                mm["top"] -= 10
            elif ch == "s":
                mm["top"] += 10
            elif ch in ("+", "="):
                mm["size"] += 2
            elif ch in ("-", "_"):
                mm["size"] = max(50, mm["size"] - 2)
            else:
                moved = False

            if moved:
                cap.set_region(mm)
                mm = dict(cap.cfg)  # clamped to the monitor
                if mm["size"] != old_size:
                    detector = make_detector()  # icon size range depends on minimap size
            elif ch == "c":
                config_mod.save_minimap(mm)
                status, status_until = "Saved to config.json", time.time() + 2
                print(f"Saved minimap region to config.json: {mm}")
            elif ch == "p":
                SAMPLES_DIR.mkdir(exist_ok=True)
                tag = f"{champ_id}_" if champ_id else ""
                name = SAMPLES_DIR / f"minimap_{tag}{datetime.now():%Y%m%d_%H%M%S_%f}.png"
                cv2.imwrite(str(name), raw)
                status, status_until = f"Saved {name.name}", time.time() + 2
                print(f"Saved sample: {name}")
            elif ch == "q" or key == 27:
                break
    finally:
        cap.close()
        cv2.destroyAllWindows()
