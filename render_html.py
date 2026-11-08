# /// script
# dependencies = [
#   "curl-cffi>=0.13.0",
#   "slack-sdk>=3.37.0",
# ]
# ///
"""Prototype: render today's NBA scoreboard as a self-contained HTML page.

Run locally with:  uv run render_html.py
"""

from html import escape
from pathlib import Path

from curl_cffi import requests as curl_requests

from nba import HEADERS

SCOREBOARD_URL = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
OUTPUT = Path(__file__).parent / "scores.html"

# tricode -> (primary, secondary)
TEAM_COLORS: dict[str, tuple[str, str]] = {
    "ATL": ("#E03A3E", "#C1D32F"),
    "BOS": ("#007A33", "#BA9653"),
    "BKN": ("#000000", "#A1A1A4"),
    "CHA": ("#1D1160", "#00788C"),
    "CHI": ("#CE1141", "#000000"),
    "CLE": ("#860038", "#FDBB30"),
    "DAL": ("#00538C", "#B8C4CA"),
    "DEN": ("#0E2240", "#FEC524"),
    "DET": ("#C8102E", "#1D42BA"),
    "GSW": ("#1D428A", "#FFC72C"),
    "HOU": ("#CE1141", "#000000"),
    "IND": ("#002D62", "#FDBB30"),
    "LAC": ("#C8102E", "#1D428A"),
    "LAL": ("#552583", "#FDB927"),
    "MEM": ("#5D76A9", "#12173F"),
    "MIA": ("#98002E", "#F9A01B"),
    "MIL": ("#00471B", "#EEE1C6"),
    "MIN": ("#0C2340", "#78BE20"),
    "NOP": ("#0C2340", "#C8102E"),
    "NYK": ("#006BB6", "#F58426"),
    "OKC": ("#007AC1", "#EF3B24"),
    "ORL": ("#0077C0", "#C4CED4"),
    "PHI": ("#006BB6", "#ED174C"),
    "PHX": ("#1D1160", "#E56020"),
    "POR": ("#E03A3E", "#000000"),
    "SAC": ("#5A2D81", "#63727A"),
    "SAS": ("#C4CED4", "#000000"),
    "TOR": ("#CE1141", "#000000"),
    "UTA": ("#002B5C", "#F9A01B"),
    "WAS": ("#002B5C", "#E31837"),
}
FALLBACK_COLORS = ("#555555", "#999999")


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _distance(a: str, b: str) -> float:
    (r1, g1, b1), (r2, g2, b2) = _rgb(a), _rgb(b)
    return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5


def pick_colors(left: str, right: str) -> tuple[str, str]:
    """Primary colors for both teams; if they look too alike, the right team uses its secondary."""
    left_primary, _ = TEAM_COLORS.get(left, FALLBACK_COLORS)
    right_primary, right_secondary = TEAM_COLORS.get(right, FALLBACK_COLORS)
    if _distance(left_primary, right_primary) < 110:
        right_primary = right_secondary
    return left_primary, right_primary


def fetch_games() -> tuple[str, list[dict]]:
    resp = curl_requests.get(SCOREBOARD_URL, headers=HEADERS, impersonate="chrome110", timeout=10)
    resp.raise_for_status()
    scoreboard = resp.json()["scoreboard"]
    return scoreboard["gameDate"], scoreboard["games"]


def _team_side(team: dict, align: str, show_score: bool, is_winner: bool) -> str:
    record = f"{team['wins']}-{team['losses']}"
    score = f'<span class="score{" win" if is_winner else ""}">{team["score"]}</span>' if show_score else ""
    return (
        f'<div class="side {align}">'
        f'<div class="team"><span class="abbr">{escape(team["teamTricode"])}</span>'
        f'<span class="record">{escape(record)}</span></div>'
        f"{score}</div>"
    )


def render_game(game: dict) -> str:
    # Same orientation as the Slack message: home team on the left.
    left, right = game["homeTeam"], game["awayTeam"]
    started = game["gameStatus"] >= 2
    left_pts, right_pts = left["score"], right["score"]
    total = left_pts + right_pts
    left_pct = left_pts / total * 100 if started and total else 50.0
    right_pct = 100 - left_pct
    left_color, right_color = pick_colors(left["teamTricode"], right["teamTricode"])
    final = game["gameStatus"] == 3
    left_wins = final and left_pts > right_pts
    right_wins = final and right_pts > left_pts

    return f"""
    <article class="game">
      <div class="status">{escape(game["gameStatusText"].strip())}</div>
      <div class="row">
        {_team_side(left, "left", started, left_wins)}
        <div class="bar" role="img"
             aria-label="{escape(left["teamTricode"])} {left_pts}, {escape(right["teamTricode"])} {right_pts}">
          <div class="fill" style="width:{left_pct:.2f}%;background:{left_color}"></div>
          <div class="fill" style="width:{right_pct:.2f}%;background:{right_color}"></div>
        </div>
        {_team_side(right, "right", started, right_wins)}
      </div>
    </article>"""


CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 32px 16px 48px;
  background: #0f1115; color: #f2f4f8;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
main { max-width: 860px; margin: 0 auto; }
.game { background: #171a21; border: 1px solid #232834; border-radius: 14px; padding: 12px 18px 16px; margin-bottom: 12px; }
.status { color: #8b93a3; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; text-align: center; margin-bottom: 8px; }
.row { display: flex; align-items: center; gap: 14px; }
.side { display: flex; align-items: center; gap: 12px; flex: 0 0 auto; width: 150px; }
.side.left { justify-content: space-between; }
.side.right { flex-direction: row-reverse; justify-content: space-between; }
.team { display: flex; flex-direction: column; line-height: 1.1; }
.side.right .team { align-items: flex-end; }
.abbr { font-size: 22px; font-weight: 800; letter-spacing: .03em; }
.record { font-size: 12px; color: #8b93a3; margin-top: 3px; font-variant-numeric: tabular-nums; }
.score { font-size: 30px; font-weight: 700; color: #9aa2b1; font-variant-numeric: tabular-nums; }
.score.win { color: #fff; }
.bar { position: relative; flex: 1 1 auto; height: 34px; display: flex; border-radius: 999px; overflow: hidden; background: #2a2f3b; }
.fill { height: 100%; transition: width .4s; }
.fill + .fill { border-left: 2px solid #171a21; }
@media (max-width: 560px) {
  .row { flex-wrap: wrap; }
  .bar { order: 3; flex: 1 1 100%; }
  .side { width: auto; flex: 1 1 0; }
}
"""


def render_page(game_date: str, games: list[dict]) -> str:
    body = "\n".join(render_game(g) for g in games) or '<p class="status">No games today.</p>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NBA scores – {escape(game_date)}</title>
<style>{CSS}</style>
</head>
<body>
<main>
  {body}
</main>
</body>
</html>
"""


if __name__ == "__main__":
    date, games = fetch_games()
    OUTPUT.write_text(render_page(date, games), encoding="utf-8")
    print(f"Wrote {len(games)} games for {date} to {OUTPUT}")
