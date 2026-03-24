#!/usr/bin/env python3
"""Diagnose LED matrix wiring layout."""

import time
from rpi_ws281x import PixelStrip, Color

strip = PixelStrip(32, 18, 800000, 10, False, 25, 0)
strip.begin()

def clear():
    for i in range(32):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

def show_and_wait(label, seconds=5):
    strip.show()
    print(f">>> {label} — look now ({seconds}s)")
    time.sleep(seconds)
    clear()

# Test 1: first 8 pixels red, next 8 green, next 8 blue, last 8 white
colors = [Color(255, 0, 0), Color(0, 255, 0), Color(0, 0, 255), Color(255, 255, 255)]
for group in range(4):
    for i in range(8):
        strip.setPixelColor(group * 8 + i, colors[group])
show_and_wait("Pixels 0-7=RED, 8-15=GREEN, 16-23=BLUE, 24-31=WHITE")

# Test 2: sequential chase — pixel 0 bright, then 1, etc.
print(">>> Sequential chase — watch the order pixels light up")
for i in range(32):
    clear()
    strip.setPixelColor(i, Color(255, 255, 255))
    strip.show()
    time.sleep(0.2)

clear()

# Test 3: just corners — pixel 0 and pixel 7
strip.setPixelColor(0, Color(255, 0, 0))   # red = pixel 0
strip.setPixelColor(7, Color(0, 255, 0))   # green = pixel 7
strip.setPixelColor(8, Color(0, 0, 255))   # blue = pixel 8
strip.setPixelColor(15, Color(255, 255, 0)) # yellow = pixel 15
show_and_wait("Corners: 0=RED, 7=GREEN, 8=BLUE, 15=YELLOW")

clear()
print("Done")
