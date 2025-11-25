# /// script
# dependencies = [
#   "curl-cffi>=0.13.0",
#   "httpx[http2]>=0.28.1",
#   "slack-sdk>=3.37.0",
# ]
# ///

from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import os
import sys

from curl_cffi import requests as curl_requests
from slack_sdk import WebClient


logging.basicConfig(
    format="%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO
)

LOGGER = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com/"
}

Team = namedtuple("Team", ["abbreviation", "pts", "record"])

@dataclass
class Game:
    home_team: Team
    away_team: Team

    def __str__(self):
        home_team_record = f"({self.home_team.record})" if self.home_team.record is not None else ""
        away_team_record = f"({self.away_team.record})" if self.away_team.record is not None else ""
        return f"{self.home_team.abbreviation} {home_team_record}-{self.away_team.abbreviation} {away_team_record}: {self.home_team.pts}-{self.away_team.pts}\n"


def get_game_info(game: dict[str, int | str]) -> Game:

    home_team_info = game["homeTeam"]
    away_team_info = game["awayTeam"]

    home_team = Team(
        home_team_info["teamTricode"],
        home_team_info["score"],
        f"{home_team_info['wins']}-{home_team_info['losses']}"
    )
    away_team = Team(
        away_team_info["teamTricode"],
        away_team_info["score"],
        f"{away_team_info['wins']}-{away_team_info['losses']}"
    )

    return Game(home_team, away_team)


def get_last_nights_games() -> list[Game] | None:
    games_url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"

    resp = curl_requests.get(
        games_url,
        headers=HEADERS,
        impersonate="chrome110",
        timeout=10
    )

    if resp.status_code != 200:
        return None

    games = resp.json().get("scoreboard").get("games")
    return [get_game_info(game) for game in games]


def send_scores(games: list[Game], yesterday: datetime) -> None:
    bot_token = os.environ["SLACK_BOT_TOKEN"]
    channel_id = os.environ["SLACK_CHANNEL_ID"]
    client = WebClient(token=bot_token)
    client.chat_postMessage(
        channel=channel_id,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*NBA* scores of *{yesterday.strftime('%d/%m/%Y')}* :basketball:",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join([str(game) for game in games]),
                },
            }
        ]
    )


if __name__ == "__main__":
    yesterday = datetime.today() - timedelta(days=1)

    games = get_last_nights_games()
    if games is None or len(games) == 0:
        LOGGER.info("No games found last night")
        sys.exit(0)


    if len(games) != 0:
        send_scores(games, yesterday)
