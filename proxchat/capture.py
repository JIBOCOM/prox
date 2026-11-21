"""Screen capture of the minimap region only (mss, no game-process access)."""
from __future__ import annotations

import mss
import numpy as np


class MinimapCapture:
    """Grabs a square region of one monitor. Coordinates are relative to that monitor."""

    def __init__(self, minimap_cfg: dict):
        self._sct = mss.mss()
        self.monitors = self._sct.monitors  # [0] = all monitors combined, [1..] = each screen
        self.set_region(minimap_cfg)

    def set_region(self, minimap_cfg: dict) -> None:
        idx = minimap_cfg["monitor"]
        if not (1 <= idx < len(self.monitors)):
            raise SystemExit(
                f"config.json: minimap.monitor={idx}, but only monitors 1..{len(self.monitors) - 1} exist"
            )
        mon = self.monitors[idx]
        size = minimap_cfg["size"]
        left, top = minimap_cfg["left"], minimap_cfg["top"]
        # Keep the region inside the monitor so mss never fails.
        left = max(0, min(left, mon["width"] - size))
        top = max(0, min(top, mon["height"] - size))
        self.cfg = {"monitor": idx, "left": left, "top": top, "size": size}
        self.region = {
            "left": mon["left"] + left,
            "top": mon["top"] + top,
            "width": size,
            "height": size,
        }

    def grab(self) -> np.ndarray:
        """Return the minimap as a BGR image (H x W x 3, uint8)."""
        shot = self._sct.grab(self.region)
        return np.ascontiguousarray(np.asarray(shot)[:, :, :3])

    def grab_monitor(self) -> np.ndarray:
        """Return the whole monitor as BGR (used by calibration to show where the box is)."""
        shot = self._sct.grab(self.monitors[self.cfg["monitor"]])
        return np.ascontiguousarray(np.asarray(shot)[:, :, :3])

    def close(self) -> None:
        self._sct.close()
