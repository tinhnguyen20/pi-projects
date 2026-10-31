# Pi Scoreboard

NBA, NFL, NHL and MLB live scores, team logos and this week's schedule on a
small touch screen. Set up for a 2.8" 320x240 PiTFT by default. `WIDTH` and
`HEIGHT` in `config.py` must match the real panel, and so must the screen line
in `/boot/firmware/config.txt`:

| Screen | `/boot/firmware/config.txt` |
|---|---|
| 2.8" capacitive PiTFT | `dtoverlay=pitft28-capacitive,rotate=90,speed=32000000,fps=30` |
| 2.8" resistive PiTFT | `dtoverlay=pitft28-resistive,rotate=90,speed=32000000,fps=20` |
| 3.5" resistive PiTFT | `dtoverlay=pitft35-resistive,rotate=90,speed=20000000,fps=20` |

## Touch controls
The bar along the bottom of the screen has four buttons:

| Button | Action |
|---|---|
| League name | Switch league |
| WEEK / TODAY | Switch Today / This Week |
| ◀ | Previous page |
| ▶ | Next page |

When there's more than one page of games, the pages turn by themselves and go
back to the first after the last. The line above the buttons runs out as the
next page gets closer, and the page number shows the seconds left (`2/4 · 12s`).
Tapping a button restarts the wait.

## Install (on the Pi, over SSH)
1. Copy this folder to the Pi, e.g. from your computer:
   `scp -r scoreboard admin@192.168.YYY.XXX:~/`
2. Install what it needs:
   `sudo apt install -y python3-pil python3-numpy python3-evdev fonts-dejavu-core fbset`
3. Set your time zone so game times are right:
   `sudo timedatectl set-timezone America/Los_Angeles`
4. Test the data: `cd ~/scoreboard && python3 scores.py`
5. Check the touch screen: `sudo python3 touch.py`, then tap each corner.
   Top-left should print small numbers and bottom-right close to the screen
   size. If not, change the `TOUCH_*` options in `config.py`: `TOUCH_SWAP_XY = True` if
   x and y are swapped, `TOUCH_INVERT_X` or `TOUCH_INVERT_Y` if one runs backwards.
6. Run it: `sudo python3 main.py` (Ctrl+C to stop)

## Start automatically on boot
```
sudo cp scoreboard.service /etc/systemd/system/
sudo systemctl enable --now scoreboard
```
Logs: `journalctl -u scoreboard -f`

## Customize
Edit `config.py`: leagues, favorite teams, refresh times, how long each page
stays up (`PAGE_SECONDS`, 0 to stop pages turning by themselves), and
`FLIP = 180` if the picture is upside down.

## Preview without the Pi
`python3 main.py --demo` writes sample screens to `preview_*.png`. This needs
Pillow 8.2 or newer (`pip install -U Pillow`). `python3 main.py --png` uses live
scores but writes `screen.png` instead of drawing on the screen.

## How it works
Three things run at once, and the main loop is the only one that changes the screen:

```
background thread:  ESPN -> scores.py -> game_cache.py        (and new logos to logos/)
touch and buttons:  tap -> touch.py -> event queue
main loop:          event queue + game_cache.py -> display.py -> framebuffer.py -> screen
```

| File | Its job |
|---|---|
| `config.py` | Your settings |
| `main.py` | Starts everything, remembers what's on screen, runs the main loop |
| `scores.py` | Everything ESPN: downloads the feed and turns it into `Game`s and `Team`s |
| `game_cache.py` | Keeps the latest games and decides when to download them again |
| `team_logos.py` | Downloads team logos and keeps them in `logos/` |
| `display.py` | Draws each screen, and knows where the touch-bar buttons are |
| `framebuffer.py` | Puts a finished image on the panel |
| `touch.py` | Turns finger taps into screen positions |
| `sample_data.py` | Fake games for `--demo` |

Scores come from ESPN's free, unofficial scoreboard feed. Team logos are
trademarks of their teams: fine for your own device, not for sharing or selling.
