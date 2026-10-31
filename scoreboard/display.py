"""Draw the score screens with Pillow.

Three things are used from outside this file:
  render()         turns games into a finished image
  action_at()      says which touch-bar button is at a screen position
  prepare_logos()  downloads the logos a list of games will need
"""
import os
from datetime import datetime
from functools import lru_cache
from math import ceil

from PIL import Image, ImageDraw, ImageFont

import config
import scores
import team_logos

W, H = config.WIDTH, config.HEIGHT
COMPACT = H < 300                        # 320x240: tighter layout, no status strip
# the touch bar is the bottom BAR_H
HEADER_H, STATUS_H, BAR_H = (24, 0, 34) if COMPACT else (32, 18, 48)
FOOTER_H = STATUS_H + BAR_H
AREA_H = H - HEADER_H - FOOTER_H         # where the games go
EDGE = 8                                 # gap between text and the screen edge
NEXT_PAGE_BAR_H = 3                      # sits at the top of the touch bar, above the buttons

# Colors
BG = (12, 14, 20)
PANEL = (24, 28, 38)
FAVORITE = (34, 44, 70)
TEXT = (235, 238, 245)
DIM = (130, 138, 155)
LIVE = (255, 70, 70)
BUTTON = (42, 48, 62)
ACCENT = {"nba": (255, 140, 40), "nfl": (60, 160, 255),
          "nhl": (90, 210, 220), "mlb": (235, 80, 90)}

ROWS_TODAY = max(1, AREA_H // (58 if COMPACT else 74))
ROWS_WEEK = max(2, AREA_H // (20 if COMPACT else 26))
LOGO_TODAY = 34 if COMPACT else 44
LOGO_WEEK = 18 if COMPACT else 22
BAR_ACTIONS = ("league", "view", "prev", "next")

# TODAY row: logos sit this far in from each side, around a middle status column
TODAY_LOGO_INSET = 12
STATUS_HALF_W = 40
# WEEK row: x position of each column
WEEK_AWAY_LOGO, WEEK_AWAY_ABBR, WEEK_AT = 8, 34, 80
WEEK_HOME_LOGO, WEEK_HOME_ABBR, WEEK_SCORE = 96, 122, 170


def _font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
             "arialbd.ttf" if bold else "arial.ttf"]   # for --demo on Windows
    dirs = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/TTF",
            "C:/Windows/Fonts"]
    for d in dirs:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


FONT_HEADER = _font(16, True)
FONT_TEAM = _font(15, True)
FONT_SCORE = _font(28, True)
FONT_SMALL = _font(12)
FONT_SMALL_BOLD = _font(12, True)
FONT_ROW = _font(14)
FONT_ROW_BOLD = _font(14, True)
FONT_MESSAGE = _font(20, True)


def render(league, view, page, games, updated=None, error=False, next_in=None):
    """Draw one page of a view ("today" or "week"). Returns (image, page_count).

    games is None if nothing has been downloaded yet. A page past the end
    wraps around, so a page number stays safe when the games change.
    next_in is the seconds until the page turns by itself, or None if it won't.
    """
    if games is None and not error:
        img, draw = _frame(league, view, 0, 1, None, False)
        _message(draw, "Loading…", "Getting scores from ESPN")
        return img, 1
    games = games or []
    pages = _today_pages(games) if view == "today" else _week_pages(games)
    page %= len(pages)
    if len(pages) < 2:
        next_in = None                   # nothing to turn to
    img, draw = _frame(league, view, page, len(pages), updated, error, next_in)
    if not games:
        _no_games_message(draw, view, error)
    elif view == "today":
        _draw_today_page(img, draw, league, pages[page])
    else:
        _draw_week_page(img, draw, league, pages[page])
    return img, len(pages)


def action_at(x, y):
    """Which touch-bar action is at screen position (x, y), if any."""
    if not (H - BAR_H <= y < H and 0 <= x < W):
        return None
    return BAR_ACTIONS[x * len(BAR_ACTIONS) // W]


def prepare_logos(league, games):
    """Download any missing logos now, so drawing doesn't have to wait for them."""
    for g in games:
        for team in (g.away, g.home):
            team_logos.ensure_downloaded(league, team, LOGO_TODAY)
            team_logos.ensure_downloaded(league, team, LOGO_WEEK)


def _is_favorite(g):
    return g.away.abbr in config.FAVORITES or g.home.abbr in config.FAVORITES


# ---------- shared chrome ----------
def _frame(league, view, page, pages, updated, error, next_in=None):
    """A blank screen with everything except the games drawn on it."""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    _header(draw, league, view, page, pages, error, next_in)
    draw.rectangle((0, H - FOOTER_H, W, H), fill=PANEL)
    if STATUS_H:
        _status_strip(draw, page, pages, updated, error, next_in)
    _touch_bar(draw, league, view, pages)
    if next_in is not None:
        _next_page_bar(draw, league, next_in)
    return img, draw


def _header(draw, league, view, page, pages, error, next_in):
    accent = ACCENT.get(league, TEXT)
    draw.rectangle((0, 0, W, HEADER_H - 1), fill=PANEL)
    draw.rectangle((0, HEADER_H - 2, W, HEADER_H - 1), fill=accent)
    y = (HEADER_H - 20) // 2
    name = league.upper()
    draw.text((EDGE, y), name, font=FONT_HEADER, fill=accent)
    draw.text((EDGE + _text_width(draw, name, FONT_HEADER) + 8, y),
              "TODAY" if view == "today" else "THIS WEEK", font=FONT_HEADER, fill=TEXT)
    # with no status strip, the page number and "offline" go up here
    if not STATUS_H and error:
        _draw_right(draw, W - EDGE, y + 2, "offline", FONT_SMALL_BOLD, LIVE)
        return
    right = scores.clock(datetime.now())
    if not STATUS_H and pages > 1:
        right = f"{page + 1}/{pages}{_seconds_left(next_in)}   " + right
    _draw_right(draw, W - EDGE, y + 2, right, FONT_SMALL, DIM)


def _seconds_left(next_in):
    """Goes after the page number. Short: the header has little room to spare."""
    return "" if next_in is None else f" · {ceil(next_in)}s"


def _status_strip(draw, page, pages, updated, error, next_in):
    y = H - FOOTER_H + 2
    if pages > 1:
        draw.text((EDGE, y), f"Page {page + 1} of {pages}{_seconds_left(next_in)}",
                  font=FONT_SMALL, fill=DIM)
    if error:
        _draw_right(draw, W - EDGE, y, "offline", FONT_SMALL_BOLD, LIVE)
    elif updated:
        _draw_right(draw, W - EDGE, y, "updated " + scores.clock(updated), FONT_SMALL, DIM)


def _touch_bar(draw, league, view, pages):
    y0, y1 = H - BAR_H + NEXT_PAGE_BAR_H + 1, H - 4
    n = len(BAR_ACTIONS)
    for i, action in enumerate(BAR_ACTIONS):
        x0, x1 = i * W // n + 3, (i + 1) * W // n - 4
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        draw.rounded_rectangle((x0, y0, x1, y1), radius=6, fill=BUTTON)
        if action == "league":
            _draw_centered(draw, cx, cy - 9, league.upper(), FONT_TEAM,
                           ACCENT.get(league, TEXT))
        elif action == "view":
            other_view = "WEEK" if view == "today" else "TODAY"
            _draw_centered(draw, cx, cy - 9, other_view, FONT_TEAM, TEXT)
        else:
            tip = -8 if action == "prev" else 8
            draw.polygon(((cx - tip, cy - 9), (cx - tip, cy + 9), (cx + tip, cy)),
                         fill=TEXT if pages > 1 else DIM)


def _next_page_bar(draw, league, next_in):
    """A line above the touch bar that runs out when the next page comes on."""
    y0, y1 = H - BAR_H, H - BAR_H + NEXT_PAGE_BAR_H - 1
    draw.rectangle((0, y0, W, y1), fill=BG)
    draw.rectangle((0, y0, int(W * next_in / config.PAGE_SECONDS), y1),
                   fill=ACCENT.get(league, TEXT))


def _message(draw, title, sub=""):
    mid = (HEADER_H + H - FOOTER_H) // 2
    _draw_centered(draw, W // 2, mid - 22, title, FONT_MESSAGE, TEXT)
    if sub:
        _draw_centered(draw, W // 2, mid + 6, sub, FONT_ROW, DIM)


def _no_games_message(draw, view, error):
    title = "No games today" if view == "today" else "No games this week"
    hint = "Tap WEEK to see this week" if view == "today" else ""
    _message(draw, title, "Can't reach ESPN" if error else hint)


# ---------- TODAY view: big rows with logos ----------
def _today_pages(games):
    """Live games first, then favorites, then by start time."""
    games = sorted(games, key=lambda g: (not g.live, not _is_favorite(g), g.start))
    return [games[i:i + ROWS_TODAY] for i in range(0, len(games), ROWS_TODAY)] or [[]]


def _draw_today_page(img, draw, league, games):
    row_h = AREA_H // ROWS_TODAY
    for i, g in enumerate(games):
        _draw_today_row(img, draw, league, g, HEADER_H + i * row_h, row_h)


def _draw_today_row(img, draw, league, g, y, row_h):
    draw.rounded_rectangle((4, y + 2, W - 5, y + row_h - 2), radius=6,
                           fill=FAVORITE if _is_favorite(g) else PANEL)
    abbr_y = y + LOGO_TODAY + 6
    status_y = y + row_h // 3 - 6        # level with the score
    # away on the left, home on the right
    _draw_today_team(img, draw, league, g.away, TODAY_LOGO_INSET, y)
    _draw_today_team(img, draw, league, g.home, W - TODAY_LOGO_INSET - LOGO_TODAY, y)
    _draw_today_scores(draw, g, abbr_y, status_y)
    _draw_today_status(draw, g, status_y)


def _draw_today_team(img, draw, league, team, x, y):
    """Logo over abbreviation."""
    _paste_logo(img, league, team, x, y + 4, LOGO_TODAY)
    _draw_centered(draw, x + LOGO_TODAY // 2, y + LOGO_TODAY + 6, team.abbr, FONT_TEAM, TEXT)


def _draw_today_scores(draw, g, abbr_y, status_y):
    """Score over record. Before the game there's no score, so the record moves up."""
    left, right = W // 2 - STATUS_HALF_W, W // 2 + STATUS_HALF_W
    if g.upcoming:
        record_y = status_y + 2
    else:
        record_y = abbr_y + 2
        score_y = status_y - 8
        _draw_right(draw, left, score_y, g.away.score, FONT_SCORE,
                    _score_color(g, g.away, g.home))
        draw.text((right, score_y), g.home.score, font=FONT_SCORE,
                  fill=_score_color(g, g.home, g.away))
    _draw_right(draw, left, record_y, g.away.record, FONT_SMALL, DIM)
    draw.text((right, record_y), g.home.record, font=FONT_SMALL, fill=DIM)


def _score_color(g, team, other):
    """The losing side's score is dimmed."""
    if g.finished:
        return TEXT if team.winner else DIM
    try:
        return TEXT if int(team.score) >= int(other.score) else DIM
    except ValueError:
        return TEXT


def _draw_today_status(draw, g, y):
    """Status in the middle, TV below it."""
    center = W // 2
    width = 2 * STATUS_HALF_W - 4
    if g.live:
        status = _fit(draw, g.status, FONT_SMALL_BOLD, width - 10)
        x = center - (_text_width(draw, status, FONT_SMALL_BOLD) + 10) // 2
        draw.ellipse((x, y + 4, x + 6, y + 10), fill=LIVE)
        draw.text((x + 10, y), status, font=FONT_SMALL_BOLD, fill=LIVE)
    else:
        status = _fit(draw, g.status, FONT_SMALL_BOLD, width)
        _draw_centered(draw, center, y, status, FONT_SMALL_BOLD, TEXT if g.upcoming else DIM)
    if g.upcoming and g.tv:
        tv = _fit(draw, g.tv, FONT_SMALL, width)
        _draw_centered(draw, center, y + 18, tv, FONT_SMALL, DIM)


# ---------- WEEK view: compact list grouped by day ----------
def _week_lines(games):
    """A ("day", label) line before each new day, and a ("game", g) line per game."""
    lines, last_day = [], None
    for g in games:
        day = g.start.date()
        if day != last_day:
            lines.append(("day", _day_label(g.start)))
            last_day = day
        lines.append(("game", g))
    return lines


def _week_pages(games):
    pages, page = [], []
    for line in _week_lines(games):
        # don't leave a day label alone at the bottom of a page
        if len(page) == ROWS_WEEK - 1 and line[0] == "day":
            pages.append(page)
            page = []
        page.append(line)
        if len(page) == ROWS_WEEK:
            pages.append(page)
            page = []
    if page:
        pages.append(page)
    return pages or [[]]


def _draw_week_page(img, draw, league, lines):
    row_h = AREA_H // ROWS_WEEK
    for i, (kind, item) in enumerate(lines):
        y = HEADER_H + i * row_h
        if kind == "day":
            _draw_week_day(draw, league, item, y, row_h)
        else:
            _draw_week_game(img, draw, league, item, y, row_h)


def _draw_week_day(draw, league, label, y, row_h):
    if label == _day_label(datetime.now().date()):
        label += "  • TODAY"
    draw.text((EDGE, y + (row_h - 12) // 2), label.upper(), font=FONT_SMALL_BOLD,
              fill=ACCENT.get(league, TEXT))


def _draw_week_game(img, draw, league, g, y, row_h):
    if _is_favorite(g):
        draw.rectangle((0, y + 1, W, y + row_h - 1), fill=FAVORITE)
    text_y = y + (row_h - 15) // 2
    logo_y = y + (row_h - LOGO_WEEK) // 2
    _paste_logo(img, league, g.away, WEEK_AWAY_LOGO, logo_y, LOGO_WEEK)
    draw.text((WEEK_AWAY_ABBR, text_y), g.away.abbr, font=FONT_ROW_BOLD, fill=TEXT)
    draw.text((WEEK_AT, text_y), "@", font=FONT_ROW, fill=DIM)
    _paste_logo(img, league, g.home, WEEK_HOME_LOGO, logo_y, LOGO_WEEK)
    draw.text((WEEK_HOME_ABBR, text_y), g.home.abbr, font=FONT_ROW_BOLD, fill=TEXT)
    if g.upcoming:
        right = g.status
        if g.tv and _text_width(draw, f"{right}  {g.tv}", FONT_ROW) <= W - WEEK_SCORE - 6:
            right += f"  {g.tv}"
        _draw_right(draw, W - EDGE, text_y, right, FONT_ROW, DIM)
    else:
        draw.text((WEEK_SCORE, text_y), f"{g.away.score}-{g.home.score}", font=FONT_ROW_BOLD,
                  fill=LIVE if g.live else TEXT)
        _draw_right(draw, W - EDGE, text_y, g.status, FONT_ROW_BOLD if g.live else FONT_ROW,
                    LIVE if g.live else DIM)


def _day_label(day):
    return f"{day:%A} {day.month}/{day.day}"


# ---------- logos ----------
def _paste_logo(img, league, team, x, y, size):
    logo = team_logos.get(league, team, size) or _fallback_logo(team.abbr, team.color, size)
    img.paste(logo, (x + (size - logo.width) // 2, y + (size - logo.height) // 2), logo)


@lru_cache(maxsize=None)
def _fallback_logo(abbr, color, size):
    """A circle in the team's color with its abbreviation."""
    logo = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(logo)
    try:
        fill = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        fill = (80, 80, 80)
    draw.ellipse((0, 0, size - 1, size - 1), fill=fill)
    font = _font(max(8, size // 3), True)
    _draw_centered(draw, size // 2, size // 2 - size // 6, abbr[:3], font, TEXT)
    return logo


# ---------- text helpers ----------
def _text_width(draw, text, font):
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


def _draw_centered(draw, center_x, y, text, font, fill):
    draw.text((center_x - _text_width(draw, text, font) // 2, y), text, font=font, fill=fill)


def _draw_right(draw, right_x, y, text, font, fill):
    draw.text((right_x - _text_width(draw, text, font), y), text, font=font, fill=fill)


def _fit(draw, text, font, width):
    """Cut text down until it fits in width pixels."""
    if _text_width(draw, text, font) <= width:
        return text
    while text and _text_width(draw, text + "…", font) > width:
        text = text[:-1]
    return text + "…"
