"""Live score viewer for a Raspberry Pi with a small touch screen.

Run on the Pi:          python3 main.py
Preview as PNGs (any computer, sample data):  python3 main.py --demo
"""
import argparse
import queue
import threading
import time
from datetime import datetime

import config
import display
import framebuffer
import scores
import touch
from game_cache import GameCache

CLOCK_REDRAW_SECONDS = 20    # redraw this often anyway, to keep the clock right


class App:
    """What's on screen, and the loop that keeps it up to date.

    Touch, buttons and downloads run on their own threads and only ever put
    events on the queue. The main loop is the one place the screen changes.
    """

    def __init__(self, output):
        self.output = output           # function(img)
        self.cache = GameCache(scores.fetch_games)
        self.events = queue.Queue()    # a BAR_ACTION, or "redraw"
        self.league_i = 0
        self.view = "today"
        self.page = 0
        self.pages = 1                 # how many the last draw came to
        self.last_image = None

    @property
    def league(self):
        return config.LEAGUES[self.league_i]

    # ----- data -----
    def refresh(self):
        league, view = self.league, self.view
        if self.cache.refresh_if_due(league, view):
            games, _, _ = self.cache.latest(league, view)
            display.prepare_logos(league, games or [])    # so later pages draw fast
            self.events.put("redraw")

    def keep_fresh(self):
        while True:
            self.refresh()
            time.sleep(1)

    # ----- input -----
    def handle(self, event):
        if event == "league":
            self.league_i = (self.league_i + 1) % len(config.LEAGUES)
            self.page = 0
        elif event == "view":
            self.view = "week" if self.view == "today" else "today"
            self.page = 0
        elif event == "prev":
            self.page = (self.page - 1) % self.pages
        elif event == "next":
            self.page = (self.page + 1) % self.pages

    def tap(self, x, y):
        action = display.action_at(x, y)
        if action:
            self.events.put(action)

    def setup_buttons(self):
        if not config.BUTTONS:
            return
        try:
            from gpiozero import Button
        except ImportError:
            print("gpiozero not installed: buttons disabled")
            return
        self._buttons = []
        for pin, action in config.BUTTONS.items():
            b = Button(pin, bounce_time=0.05)
            b.when_pressed = lambda a=action: self.events.put(a)
            self._buttons.append(b)

    # ----- drawing -----
    def draw(self):
        games, updated, error = self.cache.latest(self.league, self.view)
        img, self.pages = display.render(self.league, self.view, self.page,
                                         games, updated, error)
        self.page %= self.pages
        sig = img.tobytes()
        if sig != self.last_image:      # only push changed frames
            self.output(img)
            self.last_image = sig

    def run(self):
        self.setup_buttons()
        threading.Thread(target=touch.run, args=(self.tap,), daemon=True).start()
        threading.Thread(target=self.keep_fresh, daemon=True).start()
        while True:
            self.draw()
            try:
                self.handle(self.events.get(timeout=CLOCK_REDRAW_SECONDS))
            except queue.Empty:
                pass


def demo():
    """Render sample screens to PNG files, for previewing without a Pi."""
    import sample_data
    for league in ("nba", "nfl"):
        for view in ("today", "week"):
            games = sample_data.games(league, view)
            img, _ = display.render(league, view, 0, games, datetime.now())
            img.save(f"preview_{league}_{view}.png")
    print("Wrote preview_*.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="render sample PNGs and exit")
    ap.add_argument("--png", action="store_true",
                    help="use live data but write screen.png instead of the screen")
    args = ap.parse_args()
    if args.demo:
        demo()
    else:
        if args.png:
            out = lambda img: img.save("screen.png")
        else:
            out = framebuffer.Framebuffer().show
        App(out).run()


if __name__ == "__main__":
    main()
