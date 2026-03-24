#!/bin/bash
# Stop red-alert service and turn off LEDs
sudo systemctl stop red-alert 2>/dev/null
sudo python3 -c "
import board, neopixel
p = neopixel.NeoPixel(board.D18, 32, auto_write=False)
p.fill((0, 0, 0))
p.show()
" 2>/dev/null
echo "Stopped. LEDs off."
