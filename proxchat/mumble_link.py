"""Write our position into Mumble's "Link" shared memory (Windows: named mapping "MumbleLink").

struct LinkedMem {            // offset
    UINT32  uiVersion;        //    0
    DWORD   uiTick;           //    4
    float   fAvatarPosition[3];  //  8
    float   fAvatarFront[3];  //   20
    float   fAvatarTop[3];    //   32
    wchar_t name[256];        //   44
    float   fCameraPosition[3];  // 556
    float   fCameraFront[3];  //  568
    float   fCameraTop[3];    //  580
    wchar_t identity[256];    //  592
    UINT32  context_len;      // 1104
    unsigned char context[256];  // 1108
    wchar_t description[2048];   // 1364
};                            // 5460 bytes
"""
from __future__ import annotations

import mmap
import struct

SIZE = 5460
APP_NAME = "LoL ProxChat"
DESCRIPTION = "Proximity voice for League of Legends custom games (minimap-based)."

FRONT = (0.0, 0.0, 1.0)
TOP = (0.0, 1.0, 0.0)


def _wstr(text: str, chars: int) -> bytes:
    raw = text.encode("utf-16-le")[: (chars - 1) * 2]
    return raw.ljust(chars * 2, b"\0")


class MumbleLink:
    def __init__(self):
        self.mem = mmap.mmap(-1, SIZE, tagname="MumbleLink")
        self.tick = 0
        self.linked = False

    def update(self, position: tuple[float, float, float], identity: str, context: str) -> None:
        m = self.mem
        if not self.linked:
            struct.pack_into("<I", m, 0, 2)
            m[44:44 + 512] = _wstr(APP_NAME, 256)
            m[1364:1364 + 4096] = _wstr(DESCRIPTION, 2048)
            self.linked = True
        struct.pack_into("<9f", m, 8, *position, *FRONT, *TOP)
        struct.pack_into("<9f", m, 556, *position, *FRONT, *TOP)
        m[592:592 + 512] = _wstr(identity, 256)
        ctx = context.encode("utf-8")[:255]
        struct.pack_into("<I", m, 1104, len(ctx))
        m[1108:1108 + 256] = ctx.ljust(256, b"\0")
        self.tick = (self.tick + 1) & 0xFFFFFFFF
        struct.pack_into("<I", m, 4, self.tick)  # written last: tells Mumble there's new data

    def unlink(self) -> None:
        """uiVersion = 0 makes Mumble drop the link at once (everyone hears you normally again)."""
        if self.linked:
            struct.pack_into("<I", self.mem, 0, 0)
            self.linked = False

    def close(self) -> None:
        self.unlink()
        self.mem.close()
