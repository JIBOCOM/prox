"""Drawing helpers shared by calibration and test mode."""
from __future__ import annotations

import cv2
import numpy as np

from .detect import Detection


def text(img: np.ndarray, lines: list[str], y: int = 18, colour=(255, 255, 255)) -> None:
    for line in lines:
        cv2.putText(img, line, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, line, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1, cv2.LINE_AA)
        y += 20


def detection(img: np.ndarray, det: Detection | None, zoom: int = 1) -> None:
    """Draw a green ring + cross where the champion was found (img already zoomed by `zoom`)."""
    if det is None:
        return
    x, y = int(round(det.x * zoom)), int(round(det.y * zoom))
    r = max(6, int(det.diameter * zoom / 2) + 2)
    cv2.circle(img, (x, y), r, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.drawMarker(img, (x, y), (0, 255, 0), cv2.MARKER_CROSS, 10, 1)
