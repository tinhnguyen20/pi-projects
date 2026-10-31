"""Fake ESPN-style data for `python3 main.py --demo` (no internet needed)."""
from datetime import datetime, timedelta, timezone

import scores

TEAMS = {
    "nba": [("LAL", "552583"), ("BOS", "007A33"), ("GS", "1D428A"), ("DEN", "0E2240"),
            ("MIA", "98002E"), ("NY", "006BB6"), ("PHX", "1D1160"), ("MIL", "00471B"),
            ("DAL", "00538C"), ("OKC", "007AC1"), ("LAC", "C8102E"), ("MIN", "0C2340")],
    "nfl": [("SF", "AA0000"), ("SEA", "002244"), ("KC", "E31837"), ("BUF", "00338D"),
            ("DAL", "041E42"), ("PHI", "004C54"), ("LAR", "003594"), ("DET", "0076B6"),
            ("GB", "203731"), ("CHI", "0B162A"), ("MIA", "008E97"), ("BAL", "241773")],
}


def _competitor(abbr, color, side, score, winner, record):
    return {"homeAway": side, "score": score, "winner": winner,
            "records": [{"type": "total", "summary": record}],
            "team": {"abbreviation": abbr, "shortDisplayName": abbr,
                     "color": color, "logo": ""}}


def _event(i, when, state, detail, away, home, away_score="", home_score=""):
    away_won = state == "post" and int(away_score) > int(home_score)
    return {
        "id": str(i),
        "date": when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "status": {"type": {"state": state, "shortDetail": detail, "name": "x"}},
        "competitions": [{
            "competitors": [
                _competitor(*home, "home", home_score, state == "post" and not away_won, "5-2"),
                _competitor(*away, "away", away_score, away_won, "4-3"),
            ],
            "broadcasts": [{"names": ["ESPN"]}] if i % 3 == 0 else [],
        }],
    }


def games(league, view):
    teams = TEAMS[league]
    now = datetime.now().astimezone().replace(second=0, microsecond=0)
    live = "4:12 - 3rd" if league == "nba" else "8:41 - 3rd"
    events = [
        _event(1, now - timedelta(hours=1), "in", live, teams[0], teams[1], "78", "74"),
        _event(2, now - timedelta(hours=3), "post", "Final", teams[2], teams[3], "112", "105"),
        _event(3, now + timedelta(hours=2), "pre", "", teams[4], teams[5]),
        _event(4, now + timedelta(hours=3), "pre", "", teams[6], teams[7]),
        _event(5, now - timedelta(hours=4), "post", "Final/OT",
               teams[8], teams[9], "120", "121"),
    ]
    if view == "week":
        for k in range(1, 4):
            day = now + timedelta(days=k)
            events.append(_event(10 + k, day.replace(hour=16, minute=30), "pre", "",
                                 teams[(2 * k) % 12], teams[(2 * k + 5) % 12]))
            events.append(_event(20 + k, day.replace(hour=19, minute=0), "pre", "",
                                 teams[(2 * k + 1) % 12], teams[(2 * k + 8) % 12]))
    return scores.parse({"events": events}, league)
