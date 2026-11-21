# LoL ProxChat

Proximity voice chat for **League of Legends custom games** with friends (up to 10).
Players who are close on the map hear each other. Far away = silent. Dead players
can only talk to other dead players.

It's free: voice goes through **Mumble**, and a small Python app tells Mumble where
you are by **looking at your minimap** (a screenshot of that corner, 5 times a second).

> **Anti-cheat:** the app only takes screenshots of the minimap and reads Riot's
> official [Live Client Data API](https://developer.riotgames.com/docs/lol#game-client-api)
> (the local one Riot provides for overlays). It never reads game memory, injects
> anything, or touches the game process.

---

## For everyone: install (once)

1. **Python 3.11 or newer**: https://www.python.org/downloads/. During install, tick
   **"Add python.exe to PATH"**.
2. **Mumble** (the client): https://www.mumble.info/downloads/
3. **The VPN** the host uses: [Radmin VPN](https://www.radmin-vpn.com/) or
   [Tailscale](https://tailscale.com/download). Join the host's network (ask them
   for the name and password, or the invite).
4. **This app**: download it (green **Code** button > **Download ZIP**) and unzip it
   somewhere, e.g. `C:\LoLProxChat`. Double-click **`setup.bat`**.

### Mumble settings (once)

Open Mumble > **Configure > Settings**, and tick **Advanced** at the bottom left.

- **Plugins**: tick **Link to Game and Transmit Position**. In the plugin list,
  make sure **Link** is enabled.
- **Audio Output > Positional Audio**: tick **Enable**. If you use a headset,
  also tick **Headphones**. Then set:
  - Minimum distance: **5 m**
  - Maximum distance: **25 m**
  - Minimum volume: **0 %**
  - Bloom: **0 %**

  (25 m = `hearing_radius` 2500 in `config.json`. When you start the app it
  prints the right numbers if the host changed that value.)
- **Audio Input**: pick **Push To Talk** or **Voice Activity**, whichever you like.

### Connect to the voice server

Mumble > **Server > Connect > Add New**:
- Address: the host's VPN IP (Radmin: `26.x.x.x`, Tailscale: `100.x.x.x`)
- Port: `64738`
- Username: your name
- Password: the one the host gives you

### Calibrate (once, in any game)

1. Set League to **Borderless** (Video > Window Mode). Fullscreen can give black screenshots.
2. Start a practice tool or custom game, then double-click **`calibrate.bat`**.
3. Move the red box until it covers **exactly** the minimap
   (arrow keys = 1 px, W/A/S/D = 10 px, + / − = size). Press **C** to save.
4. Your champion should get a **green circle** in the "Minimap capture" window.
   Press **Q** to quit.

If you change your minimap size or screen resolution, calibrate again.

## Every game

1. Join the Mumble server.
2. Double-click **`run.bat`** (before or during the game, either works).
3. Play. In Mumble's log you'll see **"LoL ProxChat linked"** once your champion is found.

Until your champion is found (loading screen, lobby) and after the game ends,
Mumble works normally and everyone hears everyone.

---

## For the host: Mumble server

1. Download **Mumble Server** for Windows from https://www.mumble.info/downloads/ and install it.
2. Open its config file (`mumble-server.ini`, or `murmur.ini` on older versions, in
   the install folder) and set:
   ```ini
   serverpassword=pick-a-password
   users=12
   ```
3. Start the server. When Windows Firewall asks, **allow** it (private networks).
4. VPN:
   - **Radmin VPN** (easiest for 10 people): Network > Create network, then give
     friends the name and password. Your IP is the `26.x.x.x` next to your PC's name.
   - **Tailscale**: the free plan allows 3 users per network, so instead of inviting
     everyone, open the admin console, click your PC > **Share…**, and send each
     friend a share link. Your IP is the `100.x.x.x` one.
5. Give friends: VPN details, your VPN IP, the server password, and the same
   `config.json` values (`context` and `hearing_radius` must match for everyone).

---

## config.json

| Key | Meaning |
|---|---|
| `champion` | `"auto"` reads it from the game. Or write a name like `"Ahri"`. |
| `minimap` | Where the minimap is on screen. Set it with `calibrate.bat`. |
| `capture_fps` | Screenshots per second (5 is plenty). |
| `hearing_radius` | Hearing distance in game units (Flash ≈ 400, a lane is ≈ 10000 long). Only used to print the Mumble numbers. Mumble's Maximum distance = this ÷ 100. |
| `context` | Any text, but **the same for all players**. Mumble only applies distance between players with the same context. |
| `detection.match_threshold` | How sure the match must be (0–1). Lower it a little if your champion is often "not found". Raise it if the circle jumps onto other icons. |
| `detection.icon_diameter`, `icon_crop` | `0` = auto. `test` mode suggests values that make detection faster. |
| `map` | Size of Summoner's Rift in game units. Leave as is. |
| `death_detection` | `true` = dead players go to the "graveyard": only other dead players hear them. |

## Commands (for testing)

Run from the app folder in PowerShell:

```
.venv\Scripts\python.exe main.py calibrate [--champion Ahri]
.venv\Scripts\python.exe main.py test [--champion Ahri] [--show]
.venv\Scripts\python.exe main.py fake 7400 7400 [--circle 2000] [--dead]
.venv\Scripts\python.exe main.py run
```

- `test` runs detection on the screenshots in `samples/` (save them with **P** in
  calibrate) and writes marked-up copies to `samples/out/`. No game needed.
- `fake` sends a made-up position, to test Mumble without playing. With two
  people: one runs `fake 2000 2000`, the other `fake 2500 2000` (close, loud),
  then `fake 12000 12000` (far, silent). `--circle 2000` walks around, so you
  hear the volume and left/right change.

## Troubleshooting

- **No "linked" message in Mumble**: check that Link is enabled and
  **Link to Game and Transmit Position** is ticked. Run Mumble and the app as the
  same Windows user (both normal, or both as administrator).
- **Everyone is loud no matter where they are**: positional audio isn't enabled
  in Audio Output, or players have different `context` values.
- **Champion "not found"**: re-run calibrate. The red box must match the minimap
  edges exactly. Try `match_threshold` 0.65 (default 0.7).
- **Black minimap in calibrate**: switch League to Borderless.
