"""Team logos: downloaded once, shrunk, and kept in logos/ on the SD card."""
import io
import os

from PIL import Image

import scores

LOGO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logos")

_loaded = {}     # (league, abbr, size) -> image, or None if there's no logo


def get(league, team, size):
    """The team's logo as an RGBA image up to size x size, or None if there isn't one."""
    key = (league, team.abbr, size)
    if key not in _loaded:
        _loaded[key] = _open(ensure_downloaded(league, team, size))
    return _loaded[key]


def ensure_downloaded(league, team, size):
    """Get the logo onto the SD card if it isn't there yet. Returns its path, or None."""
    path = os.path.join(LOGO_DIR, f"{league}_{team.abbr}_{size}.png")
    if os.path.exists(path):
        return path
    if not team.logo_url:
        return None
    try:
        im = Image.open(io.BytesIO(scores.http_get(team.logo_url))).convert("RGBA")
        im.thumbnail((size, size), Image.LANCZOS)
        os.makedirs(LOGO_DIR, exist_ok=True)
        im.save(path)
        return path
    except Exception as e:
        print(f"logo download failed for {team.abbr}: {e}")
        return None


def _open(path):
    if path is None:
        return None
    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None
