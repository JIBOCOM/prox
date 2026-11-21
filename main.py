"""LoL ProxChat: proximity voice for League custom games, through Mumble.

    python main.py run                    play: send your position to Mumble
    python main.py calibrate              find the minimap on screen, check detection
    python main.py test                   run detection on screenshots in /samples
    python main.py fake 7400 7400         send a fixed position (test Mumble without a game)
"""
from __future__ import annotations

import argparse
import sys

from proxchat import config


def main() -> int:
    parser = argparse.ArgumentParser(description="LoL proximity voice chat helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("run", help="send your position to Mumble while you play")

    p = sub.add_parser("calibrate", help="show the captured minimap and adjust the capture box")
    p.add_argument("--champion", help='champion to look for (default: config.json, or the running game if "auto")')

    p = sub.add_parser("test", help="run detection on the screenshots in /samples")
    p.add_argument("--champion", help="champion to look for (default: from file name, then config.json)")
    p.add_argument("--show", action="store_true", help="show each result in a window")

    p = sub.add_parser("fake", help="send a made-up position to Mumble (game units, 0..15000)")
    p.add_argument("x", type=float, help="0 = left edge of the map, ~14870 = right edge")
    p.add_argument("y", type=float, help="0 = bottom edge, ~14980 = top edge")
    p.add_argument("--dead", action="store_true", help="pretend to be dead (graveyard)")
    p.add_argument("--circle", type=float, default=0, metavar="RADIUS",
                   help="walk in a circle of this radius around x,y (one lap / 10 s)")

    args = parser.parse_args()
    cfg = config.load()

    if args.cmd == "run":
        from proxchat import runner
        runner.run(cfg)
    elif args.cmd == "calibrate":
        from proxchat import calibrate
        calibrate.run(cfg, args.champion)
    elif args.cmd == "test":
        from proxchat import testmode
        return testmode.run(cfg, args.champion, args.show)
    elif args.cmd == "fake":
        from proxchat import runner
        runner.fake(cfg, args.x, args.y, args.dead, args.circle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
