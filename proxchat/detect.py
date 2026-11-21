"""Find your own champion's icon on the minimap with OpenCV template matching.

The minimap icon is a circle cut out of the champion's square portrait. We don't know
exactly how big it is (depends on resolution and minimap scale) or how much the portrait
is zoomed, so the first frames try a range of sizes and zooms. Once a match is found,
the detector "locks" onto that size and only tries neighbours, which is much faster.

The template is the square inscribed inside the circle, so the border ring and the
map behind the icon never take part in the match.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

CROPS = (0.80, 0.90, 1.00)   # how much of the portrait is visible inside the circle
INNER = 0.68                 # inscribed square side / circle diameter (a bit under 1/sqrt(2))
MIN_D_RATIO, MAX_D_RATIO = 0.065, 0.135  # icon diameter / minimap size when auto
# The icon size doesn't change during a game, so a miss usually means the icon is hidden
# (dead, recall, overlapped). Only redo the wide search after a long run of misses.
UNLOCK_AFTER_MISSES = 50
COARSE_STEP = 3


@dataclass
class Detection:
    x: float          # icon centre, minimap pixels
    y: float
    score: float      # 0..1 match quality
    diameter: int     # icon diameter in px that matched best
    crop: float


def _make_template(icon: np.ndarray, diameter: int, crop: float) -> np.ndarray:
    n = icon.shape[0]
    c = int(round(n * crop))
    off = (n - c) // 2
    scaled = cv2.resize(icon[off:off + c, off:off + c], (diameter, diameter), interpolation=cv2.INTER_AREA)
    side = max(6, int(diameter * INNER))
    o = (diameter - side) // 2
    return np.ascontiguousarray(scaled[o:o + side, o:o + side])


def _peaks(res: np.ndarray, threshold: float, radius: int, k: int = 3) -> list[tuple[float, tuple[int, int]]]:
    """Up to k separate local maxima above threshold (handles duplicate champions)."""
    res = res.copy()
    out = []
    for _ in range(k):
        _, mx, _, loc = cv2.minMaxLoc(res)
        if mx < threshold:
            break
        out.append((mx, loc))
        x, y = loc
        res[max(0, y - radius):y + radius + 1, max(0, x - radius):x + radius + 1] = -1
    return out


class ChampionDetector:
    def __init__(self, icon: np.ndarray, minimap_size: int, det_cfg: dict):
        self.threshold = float(det_cfg["match_threshold"])
        fixed_d = int(det_cfg.get("icon_diameter") or 0)
        fixed_crop = float(det_cfg.get("icon_crop") or 0)
        if fixed_d:
            diameters = [fixed_d]
        else:
            lo = max(10, round(minimap_size * MIN_D_RATIO))
            hi = max(lo, round(minimap_size * MAX_D_RATIO))
            diameters = list(range(lo, hi + 1))
        crops = [fixed_crop] if fixed_crop else list(CROPS)
        self.templates = {(d, c): _make_template(icon, d, c) for d in diameters for c in crops}
        self.locked: tuple[int, float] | None = None
        self.misses = 0
        self.last_pos: tuple[float, float] | None = None
        self.last_score = 0.0

    def _near(self, d: int, c: float, spread: int) -> list[tuple[int, float]]:
        return [(dd, c) for dd in range(d - spread, d + spread + 1) if (dd, c) in self.templates]

    def _best(self, img: np.ndarray, keys) -> tuple | None:
        best = None
        for key in keys:
            tpl = self.templates[key]
            if tpl.shape[0] >= img.shape[0] or tpl.shape[1] >= img.shape[1]:
                continue
            res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
            res = np.nan_to_num(res, nan=0.0, posinf=0.0, neginf=0.0)
            _, mx, _, _ = cv2.minMaxLoc(res)
            if best is None or mx > best[0]:
                best = (mx, key, res)
        return best

    def detect(self, img: np.ndarray) -> Detection | None:
        if self.locked is not None:
            best = self._best(img, self._near(*self.locked, spread=2))
        else:
            # Coarse pass over every 3rd size, then refine around the winner.
            diameters = sorted({d for d, _ in self.templates})
            coarse = [k for k in self.templates if (k[0] - diameters[0]) % COARSE_STEP == 0]
            best = self._best(img, coarse)
            if best is not None:
                refined = self._best(img, self._near(*best[1], spread=COARSE_STEP - 1))
                if refined is not None and refined[0] > best[0]:
                    best = refined
        if best is None:
            return None

        score, key, res = best
        self.last_score = score
        if score < self.threshold:
            self.misses += 1
            if self.misses >= UNLOCK_AFTER_MISSES:
                self.locked = None
            return None

        self.misses = 0
        self.locked = key
        side = self.templates[key].shape[0]
        # Same champion twice (blind pick)? Prefer the one nearest to where we were.
        peaks = _peaks(res, max(self.threshold, score - 0.08), side)
        pick_score, (lx, ly) = peaks[0]
        if self.last_pos and len(peaks) > 1:
            px, py = self.last_pos
            pick_score, (lx, ly) = min(
                peaks, key=lambda p: (p[1][0] + side / 2 - px) ** 2 + (p[1][1] + side / 2 - py) ** 2)
        x, y = lx + side / 2, ly + side / 2
        self.last_pos = (x, y)
        return Detection(x, y, pick_score, key[0], key[1])
