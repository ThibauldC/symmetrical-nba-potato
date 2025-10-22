from datetime import datetime, timedelta
import logging
import sys

import requests

logging.basicConfig(
    filename="tmp.txt",
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

def get_last_nights_games(date: datetime) -> set[str] | None:
    params = {
        "playerOrTeam": "T",
        "LeagueID": "00",
        "DateFrom": date.strftime("%m/%d/%Y"),
    }

    game_url = "https://stats.nba.com/stats/leaguegamefinder"

    with requests.Session() as session:
        session.headers.update(HEADERS)
        resp = session.get(game_url, params=params, timeout=10)
        if resp.status_code == 200:
            games = resp.json().get("resultSets")[0].get("rowSet")
            return {row[4] for row in games}

    return None



if __name__ == "__main__":
    yesterday = datetime.today() - timedelta(days=1)

    games = get_last_nights_games(yesterday)

    if games is None:
        LOGGER.info("No games found last night")

    LOGGER.info(f"{len(games)} games found")
