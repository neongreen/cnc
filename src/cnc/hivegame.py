from datetime import datetime
from pathlib import Path
from typing import Literal, NewType
from uuid import UUID

import cbor2
import requests
import tomllib
from pydantic import BaseModel, RootModel
import structlog

from cnc.utils import pprint_dict

logger = structlog.get_logger()


HiveGameNick = NewType("HiveGameNick", str)
"""Nick on hivegame.com without @"""

HivePlayerId = NewType("HivePlayerId", str)
"""Key in hive.toml, e.g. "emily" who corresponds to emily and ParathaBread from hivegame.com"""


################################################################################
# Types from hivegame.com API
#
# https://github.com/hiveboardgame/hive/blob/a679732bb4e74781d083b35d4c40ec166cc32895/shared_types/src/games_query_options.rs#L89
################################################################################


type HG_GameSpeed = Literal[
    "Bullet",
    "Blitz",
    "Rapid",
    "Classic",
    "Correspondence",
    "Untimed",
    "Puzzle",
]
all_speeds: list[HG_GameSpeed] = [
    "Bullet",
    "Blitz",
    "Rapid",
    "Classic",
    "Correspondence",
    "Untimed",
    "Puzzle",
]


class HG_BatchInfo(BaseModel):
    id: UUID
    timestamp: datetime


class HG_PlayerFilter(BaseModel):
    username: HiveGameNick
    color: Literal["White", "Black"] | None = None
    result: Literal["Win", "Loss", "Draw"] | None = None


class HG_UserResponse(BaseModel):
    username: HiveGameNick
    bot: bool
    admin: bool


class HG_GamesQueryOptions(BaseModel):
    player1: HG_PlayerFilter | None
    player2: HG_PlayerFilter | None
    speeds: list[HG_GameSpeed]
    current_batch: HG_BatchInfo | None
    batch_size: int
    expansions: bool | None
    rated: bool | None
    exclude_bots: bool
    game_progress: Literal["Unstarted", "Playing", "Finished", "All"]


class HG_GameStatusFinished_Winner(BaseModel):
    Winner: Literal["White", "Black"]


class HG_GameStatusFinished(BaseModel):
    Finished: HG_GameStatusFinished_Winner | Literal["Draw"]


class HG_GameStatus(RootModel):
    root: HG_GameStatusFinished | Literal["NotStarted", "InProgress", "Adjudicated"]


class HG_GameResponse(BaseModel):
    """https://github.com/hiveboardgame/hive/blob/a679732bb4e74781d083b35d4c40ec166cc32895/apis/src/responses/game.rs#L29"""

    game_id: str
    finished: bool
    white_player: HG_UserResponse
    black_player: HG_UserResponse
    game_status: HG_GameStatus
    rated: bool
    conclusion: str  # e.g., "Board", "Timeout", "Resigned"
    created_at: datetime
    speed: str  # e.g., "Blitz", "Rapid", "Correspondence", "Untimed"
    game_type: str  # e.g., "MLP" (Mosquito Ladybug Pillbug), "Base"


def fetch_games_between_players(
    player1: HiveGameNick,
    player2: HiveGameNick,
    start: datetime | None = None,  # XXX: not used
    max_games: int = 100,  # TODO: actually keep going instead of just doing one batch
) -> list[HG_GameResponse]:
    """
    Fetch all games between two specific players from hivegame.com

    Args:
        player1: Username of first player
        player2: Username of second player
        max_games: Maximum number of games to fetch (default 100)
        start: Only fetch games after this date (default None)
    Returns:
        List of PlayerGameResult objects with game details
    """
    logger.info(
        "Fetching games",
        player1=player1,
        player2=player2,
        max_games=max_games,
    )

    # The API endpoint ID changes, so we need to discover it
    # For now, we'll use a known working ID from our testing
    base_endpoint = "https://hivegame.com/api/get_batch_from_options"
    endpoint_id = "10902783915456376667"  # XXX This will need to be updated dynamically
    full_endpoint = f"{base_endpoint}{endpoint_id}"

    logger.debug(f"Using API endpoint: {full_endpoint}")

    all_games: list[HG_GameResponse] = []

    try:
        # Query for finished games
        query_data = {
            "options": {
                **HG_GamesQueryOptions(
                    player1=HG_PlayerFilter(username=player1),
                    player2=HG_PlayerFilter(username=player2),
                    speeds=all_speeds,
                    current_batch=None,
                    batch_size=max_games,
                    game_progress="Finished",
                    expansions=None,
                    rated=None,
                    exclude_bots=False,
                ).model_dump(),
            }
        }

        logger.debug("Query data:\n%s", pprint_dict(query_data))

        # Encode to CBOR
        cbor_data = cbor2.dumps(query_data)

        # Make the API request
        headers = {
            "accept": "application/cbor",
            "content-type": "application/cbor",
        }

        response = requests.post(
            full_endpoint, data=cbor_data, headers=headers, timeout=30
        )

        if response.status_code == 200:
            # Decode CBOR response
            response_data = cbor2.loads(response.content)
            logger.debug("Received games from API", count=len(response_data))

            for i, game in enumerate(response_data):
                logger.debug(
                    f"Processing game {i + 1}/{len(response_data)}: {game.get('game_id', 'unknown')}"
                )
                game_result = HG_GameResponse.model_validate(game)
                logger.debug(f"Game: {pprint_dict(game_result.model_dump())}")

                all_games.append(game_result)
                logger.debug(f"Added game: {game_result.game_id}")

        else:
            logger.error(
                f"API request failed with status {response.status_code}: {response.text}"
            )

        # # Filter out games before start date
        # if start:
        #     original_count = len(all_games)
        #     all_games = [game for game in all_games if game.date >= start]
        #     filtered_count = len(all_games)
        #     logger.info(
        #         f"Filtered games: {original_count} -> {filtered_count} (after {start})"
        #     )

        logger.debug(
            "Successfully fetched games",
            count=len(all_games),
            player1=player1,
            player2=player2,
        )
        return all_games

    except Exception as e:
        logger.error(
            f"Error fetching games between {player1} and {player2}: {e}", exc_info=True
        )
        return []


class HivePlayerInfo(BaseModel):
    """Information about a player from hive.toml"""

    display_name: str
    hivegame: list[HiveGameNick]
    hivegame_current: HiveGameNick | None = None

    @property
    def current_nick(self) -> HiveGameNick:
        """
        Returns the current hivegame nick for this player.
        - If hivegame_current is set, use it.
        - If hivegame has exactly one entry, use that.
        - Otherwise, raise an error.
        """
        if self.hivegame_current is not None:
            return self.hivegame_current
        if len(self.hivegame) == 1:
            return self.hivegame[0]
        raise ValueError(
            f"Cannot determine current hivegame nick for {self.display_name}: "
            f"multiple nicks and no hivegame_current set"
        )


class HiveConfigSettings(BaseModel):
    skip_highlight: list[HivePlayerId]


class HiveConfig(BaseModel):
    settings: HiveConfigSettings
    players: dict[HivePlayerId, HivePlayerInfo]


def get_config(file_path: Path) -> HiveConfig:
    """Get the config from hive.toml"""
    with file_path.open("rb") as f:
        data = tomllib.load(f)
    return HiveConfig.model_validate(data)
