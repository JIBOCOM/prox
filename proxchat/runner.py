"""The real thing: minimap -> position -> MumbleLink, with death detection.

Link behaviour (what your friends hear):
  - Before your champion is first found, and after the game ends: not linked,
    so Mumble plays you normally (everyone hears everyone, like a lobby).
  - In game: your position is sent; Mumble fades you out with distance.
    If the icon is briefly lost (fog flicker, a fight, recall animation), the
    last known position is kept.
  - Dead: moved to the "graveyard" far above the map. The living can't hear you,
    the dead hear each other.
"""
from __future__ import annotations

import math
import time

from . import config as config_mod
from .capture import MinimapCapture
from .ddragon import ChampionError, get_icon, resolve
from .detect import ChampionDetector
from .liveclient import LiveClient
from .mapcoords import GRAVEYARD, map_to_mumble, minimap_to_map, radius_to_metres
from .mumble_link import MumbleLink

GAME_OVER_AFTER = 5.0  # seconds without the Live Client API (after a game) -> unlink


def print_mumble_settings(cfg: dict) -> None:
    r = radius_to_metres(cfg["hearing_radius"])
    print("Mumble settings for hearing_radius "
          f"{cfg['hearing_radius']} (Settings > Audio Output > Positional Audio):")
    print(f"  Minimum distance: {max(1.0, r * 0.2):.0f} m   Maximum distance: {r:.0f} m   "
          "Minimum volume: 0%   Bloom: 0%")
    print(f"  Context: \"{cfg['context']}\" (every player must use the same one)\n")


def fake(cfg: dict, x: float, y: float, dead: bool = False, circle: float = 0.0) -> None:
    """Send a made-up position (game units) so you can test Mumble without playing."""
    link = MumbleLink()
    print_mumble_settings(cfg)
    print("Sending a fake position to Mumble. Ctrl+C to stop.")
    t0 = time.time()
    try:
        while True:
            gx, gy = x, y
            if circle:
                a = (time.time() - t0) / 10 * 2 * math.pi  # one lap every 10 s
                gx, gy = x + circle * math.cos(a), y + circle * math.sin(a)
            pos = GRAVEYARD if dead else map_to_mumble(gx, gy)
            link.update(pos, "fake-player", cfg["context"])
            where = "graveyard (dead)" if dead else f"map ({gx:.0f}, {gy:.0f})"
            print(f"\r{where}  ->  mumble ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) m    ", end="", flush=True)
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        link.close()


def run(cfg: dict) -> None:
    auto = config_mod.champion_is_auto(cfg)
    live = LiveClient()
    live.start()
    cap = MinimapCapture(cfg["minimap"])
    size = cap.cfg["size"]
    link = MumbleLink()
    frame_delay = 1.0 / cfg["capture_fps"]

    print_mumble_settings(cfg)
    if auto:
        print("Champion: auto (read from the game once it starts).")
    print("Waiting for the game... Ctrl+C to quit.\n")

    detector: ChampionDetector | None = None
    det_champ: str | None = None
    bad_champ: str | None = None
    last_px: tuple[float, float] | None = None
    last_seen = 0.0
    last_state = ""

    try:
        while True:
            t0 = time.perf_counter()
            now = time.time()

            # 1. Which champion? (re-checked every frame: a new game may use another one)
            want = live.champion if auto else str(cfg["champion"])
            if want and want != det_champ and want != bad_champ:
                try:
                    cid = resolve(want)
                    detector = ChampionDetector(get_icon(cid), size, cfg["detection"])
                    det_champ, last_px = want, None
                    print(f"\nLooking for {cid} on the minimap.")
                except ChampionError as e:
                    bad_champ = want
                    print(f"\n{e}")

            # 2. Game over? Unlink so everyone hears each other normally again.
            if live.ever_connected and not live.connected and now - live.last_ok > GAME_OVER_AFTER:
                if link.linked:
                    link.unlink()
                    print("\nGame over: unlinked from Mumble.")
                last_px = None
                if auto:
                    detector, det_champ = None, None
                live.ever_connected = False

            # 3. Find ourselves on the minimap
            score = 0.0
            if detector:
                det = detector.detect(cap.grab())
                score = detector.last_score
                if det:
                    last_px, last_seen = (det.x, det.y), now

            # 4. Tell Mumble
            dead = cfg["death_detection"] and live.connected and live.is_dead
            identity = live.player or "player"
            if dead:
                link.update(GRAVEYARD, identity, cfg["context"])
                state = "DEAD -> graveyard (living players can't hear you)"
            elif last_px:
                gx, gy = minimap_to_map(last_px[0], last_px[1], size, cfg["map"])
                link.update(map_to_mumble(gx, gy), identity, cfg["context"])
                lost = now - last_seen > 1.0
                state = (f"map ({gx:5.0f}, {gy:5.0f})  score {score:.2f}"
                         + ("  [icon lost, keeping last position]" if lost else ""))
            elif detector:
                state = f"searching for {det_champ}... (best match {score:.2f})"
            else:
                state = "waiting for the game / champion"

            if state != last_state:
                print(f"\r{state:<78}", end="", flush=True)
                last_state = state

            time.sleep(max(0.0, frame_delay - (time.perf_counter() - t0)))
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        live.stop()
        link.close()
        cap.close()
