from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import sys

import requests

logging.basicConfig(
    filename="logs/nba.txt",
    filemode="a",
    format="%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG
)

LOGGER = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Referer": "https://www.nba.com",
    "Origin": "https://www.nba.com",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "application/json, text/plain, */*",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "sec-ch-ua": '"Chromium";v="120", "Google Chrome";v="120", "Not:A-Brand";v="99"',
    "sec-ch-ua-platform": '"Windows"',
}

Team = namedtuple("Team", ["abbreviation", "pts", "record"])

@dataclass
class Game:
    home_team: Team
    away_team: Team

    def __str__(self):
        home_team_record = f"({self.home_team.record})" if self.home_team.record is not None else ""
        away_team_record = f"({self.away_team.record})" if self.away_team.record is not None else ""
        return f"{self.home_team.abbreviation}{home_team_record}-{self.away_team.abbreviation}{away_team_record}: {self.home_team.pts}-{self.away_team.pts}"


def get_game_info(game_id: str, team_scores: dict[str, int]) -> Game:
    game_url = "https://stats.nba.com/stats/boxscoresummaryv2"
    params = {
        "GameID": game_id
    }

    with requests.Session() as session:
        session.headers.update(HEADERS)
        resp = session.get(game_url, params=params, timeout=10)
        if resp.status_code != 200:
            LOGGER.error(f"No game info found for id {game_id}, status code {resp.status_code}")
    all_game_info = [info["rowSet"] for info in resp.json().get("resultSets") if info["name"] == "LineScore"][0]
    # TODO: get home and away team correct
    home_game_stats, away_game_stats = all_game_info
    home_team_abbr, away_team_abbr = home_game_stats[4], away_game_stats[4]
    home_team_pts = home_game_stats[-1] if home_game_stats[-1] is not None else team_scores[home_team_abbr]
    away_team_pts = away_game_stats[-1] if away_game_stats[-1] is not None else team_scores[away_team_abbr]

    home_team = Team(home_team_abbr, home_team_pts, home_game_stats[7])
    away_team = Team(away_team_abbr, away_team_pts, away_game_stats[7])

    return Game(home_team, away_team)


def get_last_nights_games(date: datetime) -> tuple[set[str], dict[str, int]] | None:
    params = {
        "playerOrTeam": "T",
        "LeagueID": "00",
        "DateFrom": date.strftime("%m/%d/%Y"),
    }

    games_url = "https://stats.nba.com/stats/leaguegamefinder"

    with requests.Session() as session:
        session.headers.update(HEADERS)
        resp = session.get(games_url, params=params, timeout=10)

    if resp.status_code != 200:
        return None

    games = resp.json().get("resultSets")[0].get("rowSet")
    return {row[4] for row in games}, {row[2]: row[9] for row in games}


if __name__ == "__main__":
    yesterday = datetime.today() - timedelta(days=1)

    games, team_scores = get_last_nights_games(yesterday)
    if games is None:
        LOGGER.info("No games found last night")
        sys.exit(0)

    for game_id in games:
        print(get_game_info(game_id, team_scores))
