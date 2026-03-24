#!/usr/bin/env python3
"""Test LED wave patterns — gentle symmetric waves moving L→R on 8x4 matrix."""

import math
import time

LED_COUNT = 32
LED_PIN = 18
LED_BRIGHTNESS = 20
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_INVERT = False
LED_CHANNEL = 0

GRID_COLS = 8
GRID_ROWS = 4
STEP_FRAMES = 4

WAVE_MIN = 0.08
WAVE_MAX = 0.5

try:
    from rpi_ws281x import PixelStrip, Color
except ImportError:
    print("rpi_ws281x not available — needs sudo on the Pi")
    raise SystemExit(1)

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()
n = strip.numPixels()


def wave_brightness(col, tick):
    """Smooth continuous cosine wave — two peaks across 8 columns."""
    step = tick // STEP_FRAMES
    phase = (col - step) * math.pi / (GRID_COLS // 2)
    return WAVE_MIN + (math.cos(phase) + 1) / 2 * (WAVE_MAX - WAVE_MIN)


def wave_two_color(col, tick):
    """Single peak wave, color sweeps L→R, changes at trough."""
    step = tick // STEP_FRAMES
    shifted = step + 4
    cycle = (shifted // GRID_COLS) % 2
    steps_into_cycle = shifted % GRID_COLS
    cidx = cycle if col <= steps_into_cycle else 1 - cycle
    phase = (col - step) * math.pi * 2 / GRID_COLS
    b = WAVE_MIN + (math.cos(phase) + 1) / 2 * (WAVE_MAX - WAVE_MIN)
    return b, cidx


def set_column(col, color):
    for row in range(GRID_ROWS):
        strip.setPixelColor(row * GRID_COLS + col, color)


def wheel(pos):
    pos = pos % 256
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)


def run_pattern(name, render_fn, seconds=7):
    print(f"\n>>> {name} — {seconds} seconds")
    tick = 0
    deadline = time.time() + seconds
    while time.time() < deadline:
        render_fn(tick)
        strip.show()
        tick += 1
        time.sleep(1 / 30)


def green_wave(tick):
    for col in range(GRID_COLS):
        b = wave_brightness(col, tick)
        set_column(col, Color(0, int(255 * b), 0))


def yellow_wave(tick):
    for col in range(GRID_COLS):
        b = wave_brightness(col, tick)
        set_column(col, Color(int(255 * b), int(180 * b), 0))


def red_wave(tick):
    for col in range(GRID_COLS):
        b = wave_brightness(col, tick)
        set_column(col, Color(int(255 * b), 0, 0))


def red_yellow_wave(tick):
    for col in range(GRID_COLS):
        b, cidx = wave_two_color(col, tick)
        if cidx == 0:
            set_column(col, Color(int(255 * b), 0, 0))
        else:
            set_column(col, Color(int(255 * b), int(180 * b), 0))


def rainbow(tick):
    for i in range(n):
        strip.setPixelColor(i, wheel((i * 256 // n + tick * 3) % 256))


try:
    run_pattern("Green wave (idle)", green_wave)
    run_pattern("Yellow wave (other city threat)", yellow_wave)
    run_pattern("Red wave (threat for our city)", red_wave)
    run_pattern("Red + Yellow wave (pre-alert)", red_yellow_wave)
    run_pattern("Rainbow (shelter active)", rainbow)
    print("\nDone — LEDs off")
finally:
    for i in range(n):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
