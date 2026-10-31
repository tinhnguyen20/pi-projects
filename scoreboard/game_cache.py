"""The latest games for each league and view, and when to download them again.

Downloads run on a background thread while the main loop reads, so all the
locking lives in here.
"""
import threading
import time
from datetime import datetime

import config


class GameCache:
    def __init__(self, fetch):
        self._fetch = fetch            # function(league, view) -> games
        self._games = {}               # (league, view) -> games
        self._updated = {}             # (league, view) -> datetime
        self._failed = set()           # keys whose last download failed
        self._last_try = {}            # (league, view) -> time.time()
        self._lock = threading.Lock()

    def latest(self, league, view):
        """What's known right now, as (games, updated, error).

        games is None until a download has worked. error means the last
        download failed, so any games are out of date.
        """
        key = (league, view)
        with self._lock:
            return self._games.get(key), self._updated.get(key), key in self._failed

    def refresh_if_due(self, league, view):
        """Download if it's time to. Returns True if it tried, even if that failed."""
        key = (league, view)
        if time.time() - self._last_try.get(key, 0) < self._refresh_seconds(key):
            return False
        try:
            games = self._fetch(league, view)
            with self._lock:
                self._games[key] = games
                self._updated[key] = datetime.now()
                self._failed.discard(key)
        except Exception as e:
            print(f"fetch {key} failed: {e}")
            with self._lock:
                self._failed.add(key)
        self._last_try[key] = time.time()
        return True

    def _refresh_seconds(self, key):
        if key[1] == "week":
            return config.REFRESH_WEEK
        games = self._games.get(key, [])
        return config.REFRESH_LIVE if any(g.live for g in games) else config.REFRESH_IDLE
