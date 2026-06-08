# Red Alert Player

A Raspberry Pi monitor for Pikud HaOref (Israeli Home Front Command) rocket
alerts, scoped to the city **חריש (Harish)**. It polls the official Oref alerts
feed every 2 seconds and reacts on two channels:

- **LED strip** — a WaveShare 8×4 (32-pixel) NeoPixel matrix on GPIO18, running
  an ambient comet/rainbow whose colour reflects the current threat level.
- **Music** — during an active shelter alert it plays a YouTube playlist through
  `mpv`, fading in as you enter the mamad and stopping when the event ends.

## LED legend

| LED | State | Meaning |
|-----|-------|---------|
| 🟢 Green   | `green_sweep`      | Idle — no active alerts / all clear |
| 🟡 Yellow  | `yellow_sweep`     | Other cities under threat; חריש is clear |
| 🔴 Red     | `red_sweep`        | חריש pre-alert (״התקרבו למרחב מוגן״) or a non-shelter alert — be near the mamad |
| 🟠 Orange  | `red_yellow_sweep` | חריש pre-alert **and** other cities under threat at the same time |
| 🌈 Rainbow | `rainbow`          | Active shelter alert for חריש (missiles / hostile aircraft / terror) — in the mamad, music playing |

Orange is the blend of red (our pre-alert) and yellow (others under alert) — it
is strictly "louder" than plain red.

## Commands

| Command | What it does |
|---------|--------------|
| `./setup.sh`   | Install dependencies, the systemd service, and the weekly yt-dlp updater |
| `./status.sh`  | Show service status |
| `./logs.sh`    | Follow the live service logs |
| `./restart.sh` | Restart the service |
| `./stop.sh`    | Stop the service and clear the LEDs |
| `python3 red_alert_player.py --demo` | Cycle through every LED state and play the shelter music (~75s) |

## How it works

- Alerts are matched to חריש by exact name or a `"חריש "` prefix.
- Categories use the Oref `cat` field (matrix_id); the shelter-triggering ones
  are Missiles (1), Hostile Aircraft (6), and Terror (13).
- Music streams via `mpv --ytdl` (yt-dlp). yt-dlp is refreshed weekly by a
  systemd timer (`yt-dlp-update.timer`) so YouTube changes don't silently break
  playback, and mpv's output is logged so failures show their real cause.

Runs as a `root` systemd service (`red-alert.service`); audio routes to the USB
speaker via `/etc/asound.conf`.
