#!/usr/bin/env python3
"""Red Alert Player — Monitors Pikud HaOref alerts for חריש."""

import json
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request

# ── Configuration ──────────────────────────────────────────────────────────

CITY = "חריש"
PLAYLIST_URL = "https://music.youtube.com/watch?v=H3ozk8juc8o"
ALERT_URL = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
POLL_INTERVAL = 2
MUSIC_TIMEOUT = 30 * 60  # 30 minutes

LED_COUNT = 32
LED_PIN = 18
LED_BRIGHTNESS = 0.08  # Adafruit neopixel: 0.0–1.0
COMET_SPEED_IDLE = 0.12   # green — slow ambient
COMET_SPEED_CALM = 0.08   # yellow — relaxed pace
COMET_SPEED_ALERT = 0.04  # red/orange — urgent pace
COMET_TAIL = 6

MPV_SOCKET = "/tmp/red-alert-mpv.sock"
FADE_DURATION = 3.0
FADE_STEPS = 15
ALERT_LOG_PATH = "/home/raziel/alert_log.jsonl"

ALERT_HEADERS = {
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
    "Accept-Language": "he",
}

CAT_NAMES = {
    # Real alerts (by matrix_id from alertCategories.json — cat field = matrix_id)
    1: "Missiles",              # missilealert
    2: "Non-conventional",      # nonconventional + memorialday (shared matrix_id)
    3: "Earthquake",            # earthquakealert1 + earthquakealert2
    4: "CBRNE",
    5: "Tsunami",
    6: "Hostile Aircraft",      # uav
    7: "Hazardous Materials",   # hazmat
    8: "Warning",
    10: "Update",               # update (event-end) + flash (pre-alert) — disambiguate by title
    13: "Terrorist Attack",
    # Drills (by matrix_id)
    101: "Missiles Drill",
    102: "Drill",               # nonconventional + warning + memorial day drills
    103: "Earthquake Drill",    104: "CBRNE Drill",
    105: "Tsunami Drill",       106: "Hostile Aircraft Drill",
    107: "Hazardous Materials Drill",
    110: "Update Drill",        113: "Terrorist Attack Drill",
}

SHELTER_CATS = {1, 6, 13}      # Missiles + Hostile Aircraft + Terrorist Attack (by matrix_id)
DRILL_CATS = {101, 102, 103, 104, 105, 106, 107, 110, 113}
EVENT_END_TITLE = "האירוע הסתיים"
ABSENCE_TIMEOUT = 60 * 60      # 60 min safety net — primary exit is event-end (cat=10)


def city_match(city_name: str) -> bool:
    """Match CITY exactly or as a prefix (e.g. 'חריש' matches 'חריש - מזרח')."""
    stripped = city_name.strip()
    return stripped == CITY or stripped.startswith(CITY + " ")


# ── Colored Logger ─────────────────────────────────────────────────────────

ANSI = {
    "quiet":      "\033[32m",        # green
    "other_city": "\033[33m",        # yellow
    "rocket":     "\033[1;31m",      # red bold
    "pre_alert":  "\033[31m",        # red
    "all_clear":  "\033[36m",        # cyan
    "music":      "\033[35m",        # magenta
    "system":     "\033[34m",        # blue
    "reset":      "\033[0m",
}

logger = logging.getLogger("red_alert")
logger.setLevel(logging.DEBUG)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%H:%M:%S"))
logger.addHandler(_handler)


def log(level: str, msg: str, category: str = "system") -> None:
    color = ANSI.get(category, "")
    reset = ANSI["reset"]
    colored_msg = f"{color}{msg}{reset}"
    getattr(logger, level, logger.info)(colored_msg)


# ── LED Controller ─────────────────────────────────────────────────────────

try:
    import board
    import neopixel
    from adafruit_led_animation.animation.comet import Comet
    from adafruit_led_animation.animation.rainbowsparkle import RainbowSparkle

    GREEN = (0, 255, 0)
    YELLOW = (255, 180, 0)
    RED = (255, 0, 0)
    DARK_ORANGE = (255, 80, 0)

    class LEDController:
        STATES = ("green_sweep", "yellow_sweep", "red_sweep", "red_yellow_sweep", "rainbow")

        def __init__(self):
            self._pixels = neopixel.NeoPixel(
                board.D18, LED_COUNT, brightness=LED_BRIGHTNESS, auto_write=False,
            )
            self._effects = {
                "green_sweep": Comet(self._pixels, speed=COMET_SPEED_IDLE, color=GREEN, tail_length=COMET_TAIL, bounce=True),
                "yellow_sweep": Comet(self._pixels, speed=COMET_SPEED_CALM, color=YELLOW, tail_length=COMET_TAIL, bounce=True),
                "red_sweep": Comet(self._pixels, speed=COMET_SPEED_ALERT, color=RED, tail_length=COMET_TAIL, bounce=True),
                "red_yellow_sweep": Comet(self._pixels, speed=COMET_SPEED_ALERT, color=DARK_ORANGE, tail_length=COMET_TAIL, bounce=True),
                "rainbow": RainbowSparkle(self._pixels, speed=0.03, period=2),
            }
            self._state = "green_sweep"
            self._lock = threading.Lock()
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            log("info", f"LED strip initialised ({LED_COUNT} pixels)", "system")

        def set_state(self, state: str) -> None:
            if state not in self.STATES:
                return
            with self._lock:
                if self._state != state:
                    self._state = state
                    log("info", f"LED → {state}", "system")

        def _get_state(self) -> str:
            with self._lock:
                return self._state

        def _loop(self):
            while self._running:
                try:
                    state = self._get_state()
                    self._effects[state].animate()
                except Exception as e:
                    log("error", f"LED thread error: {e}", "system")
                    time.sleep(1)

        def cleanup(self):
            self._running = False
            self._thread.join(timeout=2)
            try:
                self._pixels.fill((0, 0, 0))
                self._pixels.show()
            except Exception:
                pass
            log("info", "LEDs off", "system")

except ImportError:
    log("warning", "neopixel/adafruit not available — using FakeLEDController", "system")

    class LEDController:  # type: ignore[no-redef]
        STATES = ("green_sweep", "yellow_sweep", "red_sweep", "red_yellow_sweep", "rainbow")

        def __init__(self):
            self._state = "green_sweep"
            log("info", "FakeLEDController initialised", "system")

        def set_state(self, state: str) -> None:
            if state in self.STATES and state != self._state:
                self._state = state
                log("info", f"LED → {state} (fake)", "system")

        def cleanup(self):
            log("info", "FakeLEDController cleanup", "system")


# ── Music Controller ───────────────────────────────────────────────────────

class MusicController:
    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._playing = False
        self._start_time: float = 0
        self._lock = threading.Lock()

    @property
    def playing(self) -> bool:
        with self._lock:
            if self._playing and self._proc is not None:
                if self._proc.poll() is not None:
                    log("warning", "mpv process died unexpectedly", "music")
                    self._playing = False
                    self._proc = None
            return self._playing

    def start(self) -> None:
        if self.playing:
            log("info", "Music already playing, skipping start", "music")
            return
        with self._lock:
            self._launch()

    def _launch(self) -> None:
        # Clean up stale socket
        try:
            os.unlink(MPV_SOCKET)
        except FileNotFoundError:
            pass

        cmd = [
            "mpv",
            "--no-video",
            "--shuffle",
            "--ytdl",
            f"--input-ipc-server={MPV_SOCKET}",
            "--volume=0",
            PLAYLIST_URL,
        ]
        log("info", "Starting mpv…", "music")
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            log("error", f"Failed to start mpv: {e}", "music")
            return

        self._playing = True
        self._start_time = time.time()

        # Wait for IPC socket, then fade in
        if self._wait_for_socket(3.0):
            self._fade(0, 100)
            log("info", "Music started and faded in", "music")
        else:
            log("warning", "mpv socket not available, setting volume directly", "music")

    def _wait_for_socket(self, timeout: float) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if os.path.exists(MPV_SOCKET):
                try:
                    self._ipc({"command": ["get_property", "volume"]})
                    return True
                except Exception:
                    pass
            time.sleep(0.2)
        return False

    def _ipc(self, command: dict) -> dict | None:
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect(MPV_SOCKET)
            payload = json.dumps(command) + "\n"
            sock.sendall(payload.encode())
            data = sock.recv(4096)
            sock.close()
            return json.loads(data.decode())
        except Exception:
            return None

    def _fade(self, from_vol: int, to_vol: int) -> None:
        step = (to_vol - from_vol) / FADE_STEPS
        delay = FADE_DURATION / FADE_STEPS
        vol = from_vol
        for _ in range(FADE_STEPS):
            vol += step
            result = self._ipc({"command": ["set_property", "volume", max(0, min(100, int(vol)))]})
            if result is None:
                log("warning", "IPC failed during fade — mpv socket dead, bailing", "music")
                break
            time.sleep(delay)
        self._ipc({"command": ["set_property", "volume", to_vol]})

    def stop(self) -> None:
        with self._lock:
            if not self._playing or self._proc is None:
                return
            log("info", "Stopping music (fade out)…", "music")
            self._fade(100, 0)
            self._ipc({"command": ["quit"]})
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log("warning", "mpv did not exit, killing", "music")
                self._proc.kill()
                self._proc.wait(timeout=2)
            self._playing = False
            self._proc = None
            log("info", "Music stopped", "music")

    def check_timeout(self) -> bool:
        """Returns True if music was auto-stopped due to timeout."""
        if not self.playing:
            return False
        elapsed = time.time() - self._start_time
        if elapsed > MUSIC_TIMEOUT:
            log("warning", f"Music timeout ({int(elapsed)}s) — auto-stopping", "music")
            self.stop()
            return True
        return False


# ── Alert Poller ───────────────────────────────────────────────────────────

class AlertPoller:
    def __init__(self, led: LEDController, music: MusicController):
        self.led = led
        self.music = music
        self.running = True
        self._shelter_active = False
        self._last_shelter_time: float | None = None

    def poll_once(self) -> list[dict] | None:
        req = urllib.request.Request(ALERT_URL, headers=ALERT_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read()
                # Strip BOM if present
                if raw.startswith(b"\xef\xbb\xbf"):
                    raw = raw[3:]
                text = raw.decode("utf-8").strip()
                if not text:
                    return []
                parsed = json.loads(text)
                # API returns a single object when there's one alert, or a list
                if isinstance(parsed, dict):
                    parsed = [parsed]
                elif not isinstance(parsed, list):
                    return []
                if parsed:
                    try:
                        with open(ALERT_LOG_PATH, "a", encoding="utf-8") as f:
                            entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "alerts": parsed}
                            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    except Exception:
                        pass
                return parsed
        except json.JSONDecodeError:
            log("debug", "Empty/invalid JSON from API (no active alerts)", "quiet")
            return []
        except Exception as e:
            log("warning", f"Poll error: {e}", "system")
            return None

    def _log_other_city_alerts(self, alerts: list[dict], cat_filter: set[int], label: str, color: str) -> None:
        """Group and log alerts for other cities matching the given category filter."""
        by_cat: dict[str, list[str]] = {}
        for a in alerts:
            d = a.get("data", [])
            if isinstance(d, str):
                d = [d]
            if any(city_match(c) for c in d):
                continue
            cat = a.get("cat")
            try:
                cat = int(cat)
            except (TypeError, ValueError):
                cat = 0
            if cat not in cat_filter:
                continue
            eng = CAT_NAMES.get(cat, f"cat {cat}")
            heb_title = a.get("title")
            if heb_title:
                cat_label = f"{eng} | {heb_title[::-1]}"
            else:
                cat_label = eng
            by_cat.setdefault(cat_label, []).extend(d)
        parts = []
        for cat_label, cities in by_cat.items():
            parts.append(f"{len(cities)} cities ({cat_label})")
        if parts:
            log("info", f"{label}: {'; '.join(parts)}", color)

    def process_alerts(self, alerts: list[dict]) -> None:
        if not alerts:
            if self._shelter_active:
                log("debug", "Alert ended — stay in mamad, waiting for all-clear", "rocket")
                return
            log("debug", "No active alerts", "quiet")
            self.led.set_state("green_sweep")
            return

        our_cats: set[int] = set()
        our_event_end = False
        our_pre_alert = False
        other_threat = False
        other_info = False

        for alert in alerts:
            cat = alert.get("cat")
            try:
                cat = int(cat)
            except (TypeError, ValueError):
                continue
            title = alert.get("title", "")
            is_event_end = cat == 10 and EVENT_END_TITLE in title
            cities = alert.get("data", [])
            if isinstance(cities, str):
                cities = [cities]
            if any(city_match(c) for c in cities):
                if cat == 10:
                    if is_event_end or self._shelter_active:
                        our_event_end = True
                    else:
                        our_pre_alert = True
                else:
                    our_cats.add(cat)
            elif is_event_end or cat in DRILL_CATS:
                other_info = True
            else:
                other_threat = True

        # Priority: shelter > event-end > pre-alert > other threat > shelter_active > other cities
        our_shelter = our_cats & SHELTER_CATS
        our_other_threat = our_cats - SHELTER_CATS - DRILL_CATS

        if our_shelter:
            shelter_names = [CAT_NAMES.get(c, f"cat {c}") for c in sorted(our_shelter)]
            log("critical", f"🚨 {' + '.join(shelter_names).upper()} ALERT for {CITY} — ENTER MAMAD!", "rocket")
            self.led.set_state("rainbow")
            self.music.start()
            self._shelter_active = True
            self._last_shelter_time = time.time()
        elif our_event_end:
            if self._shelter_active:
                log("info", f"✅ Event end (cat 10) for {CITY} — EXIT MAMAD", "all_clear")
                self.music.stop()
                self._shelter_active = False
                self._last_shelter_time = None
            else:
                log("info", f"✅ Event end (cat 10) for {CITY} — all clear", "all_clear")
            self.led.set_state("green_sweep")
        elif our_pre_alert:
            log("warning", f"⚠ Pre-alert (cat 10) for {CITY} — be near mamad", "pre_alert")
            self.led.set_state("red_yellow_sweep")
        elif our_other_threat:
            threat_names = [CAT_NAMES.get(c, f"cat {c}") for c in sorted(our_other_threat)]
            log("warning", f"⚠ {', '.join(threat_names)} alert for {CITY}!", "pre_alert")
            self.led.set_state("red_sweep")
        elif self._shelter_active:
            if other_threat:
                threat_cats = set(CAT_NAMES) - DRILL_CATS - {10}
                self._log_other_city_alerts(alerts, threat_cats, "Alerts for other cities", "other_city")
            log("debug", "Shelter still active — maintaining rainbow + music", "rocket")
        elif other_threat:
            threat_cats = set(CAT_NAMES) - DRILL_CATS - {10}
            self._log_other_city_alerts(alerts, threat_cats, "Alerts for other cities", "other_city")
            self.led.set_state("yellow_sweep")
        elif other_info:
            self._log_other_city_alerts(alerts, DRILL_CATS | {10}, "ℹ Other cities info/drills", "quiet")
            self.led.set_state("green_sweep")
        else:
            self.led.set_state("green_sweep")

    def run(self) -> None:
        log("info", f"Polling {ALERT_URL} every {POLL_INTERVAL}s for city: {CITY}", "system")
        while self.running:
            try:
                alerts = self.poll_once()
                if alerts is not None:
                    self.process_alerts(alerts)
                # Hard timeout (30 min) — auto-stop music regardless
                self.music.check_timeout()
                # Absence timeout (60 min) — safety net if event-end never received
                if self._shelter_active and self._last_shelter_time is not None:
                    absence = time.time() - self._last_shelter_time
                    if absence >= ABSENCE_TIMEOUT:
                        log("info", f"No shelter alerts for {int(absence)}s — auto-clearing shelter", "all_clear")
                        self.music.stop()
                        self.led.set_state("green_sweep")
                        self._shelter_active = False
                        self._last_shelter_time = None
            except Exception as e:
                log("error", f"Unexpected error in poll loop: {e}", "system")
            time.sleep(POLL_INTERVAL)


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    log("info", "Red Alert Player starting…", "system")
    log("info", f"Monitoring city: {CITY}", "system")

    led = LEDController()
    music = MusicController()
    poller = AlertPoller(led, music)

    def shutdown(signum, frame):
        sig_name = signal.Signals(signum).name
        log("info", f"Received {sig_name}, shutting down…", "system")
        poller.running = False
        music.stop()
        led.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGHUP, shutdown)

    try:
        poller.run()
    except SystemExit:
        raise
    except Exception as e:
        log("critical", f"Fatal error: {e}", "system")
    finally:
        music.stop()
        led.cleanup()


if __name__ == "__main__":
    main()
