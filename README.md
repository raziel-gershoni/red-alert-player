# Red Alert Player

> A Raspberry Pi appliance that turns Israeli Home Front Command rocket alerts into an ambient LED status light and, when the sirens sound for your city, plays calming music in the shelter.

![Python](https://img.shields.io/badge/Python_3-3776ab?style=flat-square&logo=python&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry_Pi-a22846?style=flat-square&logo=raspberrypi&logoColor=white)
![systemd](https://img.shields.io/badge/systemd-service-30b980?style=flat-square&logo=linux&logoColor=white)
![NeoPixel](https://img.shields.io/badge/WS281x_NeoPixel-ff6f00?style=flat-square)
![mpv](https://img.shields.io/badge/mpv_%2B_yt--dlp-691f74?style=flat-square&logo=mpv&logoColor=white)

A single-purpose device I built and run at home. It polls the official Pikud HaOref (Israeli Home Front Command) alerts feed every two seconds and reacts on two physical channels, scoped to the city **חריש (Harish)**:

- **LED strip** — a WaveShare 8×4 (32-pixel) WS281x/NeoPixel matrix on GPIO18 runs an ambient comet/rainbow animation whose colour and pace reflect the current threat level, so a glance across the room tells you the situation.
- **Music** — during an active shelter alert it fades a YouTube playlist in through `mpv`, holds it while you're in the *mamad* (safe room), and fades out when the event ends — a small piece of calm for the household during a hard moment.

<!-- Screenshot placeholder: leave exactly this HTML comment so the owner can drop a photo/GIF of the device in later:
     ![the device](docs/device.jpg) -->

## 🚦 LED legend

| LED | State | Meaning |
|-----|-------|---------|
| 🟢 Green   | `green_sweep`      | Idle — no active alerts / all clear |
| 🟡 Yellow  | `yellow_sweep`     | Other cities under threat; Harish is clear |
| 🔴 Red     | `red_sweep`        | Harish pre-alert (*"get close to a protected space"*) or a non-shelter alert — be near the mamad |
| 🟠 Orange  | `red_yellow_sweep` | Harish pre-alert **and** other cities under threat at the same time |
| 🌈 Rainbow | `rainbow`          | Active shelter alert for Harish (missiles / hostile aircraft / terror) — in the mamad, music playing |

Orange is the deliberate blend of red (our own pre-alert) and yellow (others under alert) — strictly "louder" than plain red. The comet animation also speeds up as the threat level rises.

## 🏗️ How it works

**Precise alert matching.** The Oref feed is noisy and city names vary, so alerts are matched to Harish by exact name or a `"חריש "` prefix (which also catches sub-districts like `חריש - מזרח`). Alert *categories* are read from the feed's `cat` field (a matrix id), and only the genuinely shelter-triggering categories — **Missiles (1), Hostile Aircraft (6), and Terror (13)** — escalate to the rainbow-and-music state; everything else drives a calmer LED state. Drills are recognised and handled separately.

**Event lifecycle, not just a timer.** An active event ends primarily on the feed's own *event-ended* signal (`cat=10`, title `האירוע הסתיים`) rather than a blind countdown, with a 60-minute absence safety net so a missed end-signal can't leave the music running forever.

**Smooth audio via mpv IPC.** Music streams with `mpv --ytdl` (yt-dlp) and is controlled at runtime over mpv's JSON IPC on a Unix domain socket, ramping the volume across ~25 steps for a gentle fade-in/out instead of an abrupt cut. mpv's stdout/stderr is captured to a log file so playback failures (yt-dlp extraction, ALSA routing) surface their real cause instead of failing silently.

**Built to keep running unattended.** It ships as a `root` systemd service (`red-alert.service`) that restarts on failure and starts after the network and sound targets are up. Because YouTube regularly changes how it serves audio, a second systemd unit (`yt-dlp-update.timer`) refreshes yt-dlp weekly so playback doesn't quietly break, and `deno` is installed to help yt-dlp solve YouTube's JS challenges. Every alert is appended to `alert_log.jsonl` for later review.

**No heavy dependencies.** The application logic is a single Python file using only the standard library (`urllib`, `socket`, `subprocess`, `signal`, `threading`, `logging`); the only third-party pieces are the `rpi_ws281x` LED driver and the external `mpv`/`yt-dlp` binaries.

## 🛠️ Tech stack
**Language:** Python 3 (standard library only for application logic)
**Hardware:** Raspberry Pi + WaveShare 8×4 WS281x/NeoPixel matrix on GPIO18, USB speaker
**LED driver:** `rpi_ws281x`
**Audio:** `mpv` (controlled via JSON IPC over a Unix socket) + `yt-dlp`
**Service:** systemd (`red-alert.service` + a weekly `yt-dlp-update.timer`)
**Data source:** the public Pikud HaOref alerts feed (`oref.org.il`)

## 🚀 Getting started

> This runs on a Raspberry Pi with a WS281x LED matrix wired to GPIO18 and a speaker attached. `red_alert_player.py` and the unit files expect to live under `/home/raziel/` — adjust the paths in `setup.sh` and `red-alert.service` for your own user.

### Prerequisites
- Raspberry Pi OS with `python3`, `mpv`, and `yt-dlp` installed
- A WS281x/NeoPixel matrix on GPIO18 and audio output (e.g. a USB speaker)

### Install
```bash
./setup.sh   # installs rpi_ws281x, registers the systemd service + the weekly yt-dlp updater
```

### Everyday commands
| Command | What it does |
|---------|--------------|
| `./status.sh`  | Show service status |
| `./logs.sh`    | Follow the live service logs |
| `./restart.sh` | Restart the service |
| `./stop.sh`    | Stop the service and clear the LEDs |
| `python3 red_alert_player.py --demo` | Cycle through every LED state and play the shelter music (~75s) — no real alert needed |

## ⚙️ Configuration
The key settings are constants at the top of `red_alert_player.py`:

- `CITY` — the city to monitor (default `חריש`)
- `PLAYLIST_URL` — the YouTube (Music) playlist to play during a shelter alert
- `LED_COUNT` / `LED_PIN` / `LED_BRIGHTNESS` — LED matrix geometry and brightness
- `SHELTER_CATS` — which alert categories trigger music + rainbow

## 📄 License
Shared publicly as a portfolio project.
