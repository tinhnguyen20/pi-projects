"""Fetch scores from ESPN's public scoreboard feed.

All ESPN-specific code lives in this file, so if the feed ever
changes, this is the only place that needs fixing.

fetch_games() is the way in. It returns a list of Game, each with two Teams.
"""
import json
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

BASE = "https://site.api.espn.com/apis/site/v2/sports"
PATHS = {"nba": "basketball/nba", "nfl": "football/nfl",
         "nhl": "hockey/nhl", "mlb": "baseball/mlb"}
UNKNOWN_ABBR = "???"


@dataclass
class Team:
    abbr: str
    name: str
    score: str
    logo_url: str            # "" if the team is unknown
    color: str
    record: str
    winner: bool


@dataclass
class Game:
    id: str
    start: datetime          # local time
    state: str               # "pre", "in" or "post"
    status: str              # short text: "Q3 4:12", "Final", "7:30 PM"
    away: Team
    home: Team
    tv: str

    @property
    def upcoming(self):
        return self.state == "pre"

    @property
    def live(self):
        return self.state == "in"

    @property
    def finished(self):
        return self.state == "post"


def fetch_games(league, view):
    """The games for a league's "today" or "week" view."""
    return _fetch_today(league) if view == "today" else _fetch_week(league)


def clock(dt):
    """'7:30 PM', without strftime's non-portable %-I."""
    return dt.strftime("%I:%M %p").lstrip("0")


def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "pi-scoreboard/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------- which days to ask for ----------
def _fetch_today(league):
    today = datetime.now().date()
    if league == "nfl":
        # NFL: use the current week and keep today's + live games
        return [g for g in _fetch_scoreboard("nfl") if g.start.date() == today or g.live]
    return _fetch_scoreboard(league, f"{today:%Y%m%d}")


def _fetch_week(league):
    if league == "nfl":
        return _fetch_scoreboard("nfl")  # ESPN's default NFL scoreboard is the current week
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    # ESPN answers 400 to YYYYMMDD-YYYYMMDD ranges, so ask one day at a time
    games = {}
    for i in range(7):
        day = monday + timedelta(days=i)
        for g in _fetch_scoreboard(league, f"{day:%Y%m%d}"):
            games[g.id] = g
    return sorted(games.values(), key=lambda g: g.start)


def _fetch_scoreboard(league, dates=None):
    url = f"{BASE}/{PATHS[league]}/scoreboard"
    url += f"?dates={dates}&limit=200" if dates else "?limit=200"
    return parse(json.loads(http_get(url).decode("utf-8")), league)


# ---------- turning ESPN's JSON into Games ----------
def parse(data, league):
    games = []
    for event in data.get("events", []):
        try:
            games.append(_game(event, league))
        except (KeyError, IndexError, ValueError):
            continue  # skip anything malformed rather than crash
    games.sort(key=lambda g: g.start)
    return games


def _game(event, league):
    competition = event["competitions"][0]
    sides = {c.get("homeAway"): _team(c, league) for c in competition["competitors"]}
    start = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ")
    start = start.replace(tzinfo=timezone.utc).astimezone()
    status_type = event.get("status", {}).get("type", {})
    state = status_type.get("state", "pre")
    return Game(
        id=event.get("id", ""),
        start=start,
        state=state,
        status=_status_text(state, status_type, start, league),
        away=sides["away"],
        home=sides["home"],
        tv=_tv(competition),
    )


def _team(competitor, league):
    team = competitor.get("team", {})
    abbr = team.get("abbreviation", UNKNOWN_ABBR)
    return Team(
        abbr=abbr,
        name=team.get("shortDisplayName") or team.get("name", ""),
        score=str(competitor.get("score", "") or ""),
        logo_url=_logo_url(team, abbr, league),
        color=team.get("color", "444444") or "444444",
        record=_record(competitor),
        winner=bool(competitor.get("winner")),
    )


def _logo_url(team, abbr, league):
    if abbr == UNKNOWN_ABBR:
        return ""
    # Use the logo URL from the feed; if missing, ESPN's standard logo path
    feed_url = team.get("logo") or ((team.get("logos") or [{}])[0].get("href", ""))
    return feed_url or f"https://a.espncdn.com/i/teamlogos/{league}/500/{abbr.lower()}.png"


def _record(competitor):
    for record in competitor.get("records") or []:
        if record.get("type") in ("total", "ytd", None) or record.get("name") == "overall":
            return record.get("summary", "")
    return ""


def _tv(competition):
    for broadcast in competition.get("broadcasts") or []:
        names = broadcast.get("names") or []
        if names:
            return names[0]
    return ""


def _status_text(state, status_type, start, league):
    if state == "pre":
        if status_type.get("name") == "STATUS_POSTPONED":
            return "PPD"
        return clock(start)
    if state == "post":
        detail = status_type.get("shortDetail") or "Final"
        return detail.replace("Final/", "F/")  # "Final/OT" -> "F/OT"
    # live: "Q3 4:12" style. ESPN gives e.g. "4:12 - 3rd" or "Halftime"
    detail = status_type.get("shortDetail") or status_type.get("detail") or "Live"
    if " - " in detail:
        game_clock, period = detail.split(" - ", 1)
        if league in ("nba", "nfl"):  # hockey keeps "3rd"
            period = period.replace("1st", "Q1").replace("2nd", "Q2") \
                           .replace("3rd", "Q3").replace("4th", "Q4")
        return f"{period} {game_clock}"
    return detail


if __name__ == "__main__":
    # Quick test: python3 scores.py
    for league in PATHS:
        print(f"--- {league.upper()} today ---")
        for g in fetch_games(league, "today"):
            print(f"{g.away.abbr:>4} {g.away.score:>3}  @  {g.home.abbr:<4} "
                  f"{g.home.score:<3}  {g.status}")
