# Settings for the score viewer. Edit these to taste.

# Leagues to cycle through with the league touch button
# (any of "nba", "nfl", "nhl", "mlb")
LEAGUES = ["nba", "nfl", "nhl", "mlb"]

# Your teams, by ESPN abbreviation (e.g. "LAL", "GS", "SF", "LAR").
# Their games get highlighted and sorted to the top.
FAVORITES = ["LAL", "GS", "SF"]

# How often to re-download scores (seconds)
REFRESH_LIVE = 30        # while any game is in progress
REFRESH_IDLE = 600       # when nothing is live
REFRESH_WEEK = 900       # the week schedule changes slowly

# Screen
# Must match the real panel. 320, 240 for a 2.8" screen; 480, 320 or 320, 480
# for a 3.5" one. A wrong size here scrambles the picture.
WIDTH, HEIGHT = 320, 240
# Framebuffer device. "auto" finds the small screen; or set e.g. "/dev/fb1"
FRAMEBUFFER = "auto"

# Touch screen. "auto" finds it; or set e.g. "/dev/input/event0".
# If taps land in the wrong place, run `sudo python3 touch.py` and adjust these.
TOUCH_DEVICE = "auto"
TOUCH_SWAP_XY = False
TOUCH_INVERT_X = False
TOUCH_INVERT_Y = False

# Optional physical buttons, as {GPIO pin: action}. Off by default: many 3.5"
# screens use these pins themselves (often GPIO 17 for the touch controller).
# PiTFT 2.8" buttons: BUTTONS = {17: "league", 22: "view", 23: "prev", 27: "next"}
# (needs `sudo apt install python3-gpiozero`)
BUTTONS = {}

# Rotate the drawn image if it appears upside down on your screen (0 or 180)
FLIP = 0
