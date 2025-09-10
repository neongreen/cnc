# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, RootModel, field_validator
import cbor2
import requests
import structlog

from cnc.utils import pprint_dict
from cnc.hive.player_ids import HG_PlayerId

logger = structlog.get_logger()


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

    @field_validator("timestamp")
    def ensure_utc(cls, v: datetime) -> datetime:
        """Ensure timestamp is UTC."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class HG_PlayerFilter(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    username: HG_PlayerId
    color: Literal["White", "Black"] | None = None
    result: Literal["Win", "Loss", "Draw"] | None = None


class HG_UserResponse(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    username: HG_PlayerId
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
    updated_at: datetime
    speed: str  # e.g., "Blitz", "Rapid", "Correspondence", "Untimed"
    game_type: str  # e.g., "MLP" (Mosquito Ladybug Pillbug), "Base"
    last_interaction: datetime | None

    @field_validator("created_at", "updated_at", "last_interaction")
    def ensure_utc(cls, v: datetime | None) -> datetime | None:
        """Ensure timestamp is UTC."""
        if v and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    model_config = {"extra": "allow"}  # extra fields will be available in model_extra


def fetch_games_between_players(
    player1: HG_PlayerId,
    player2: HG_PlayerId,
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
        response = requests.post(
            full_endpoint,
            data=cbor_data,
            headers={
                "accept": "application/cbor",
                "content-type": "application/cbor",
            },
            timeout=30,
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


def fetch_games_for_player(
    player: HG_PlayerId,
    max_games: int = 200,  # TODO: actually keep going instead of just doing one batch
) -> list[HG_GameResponse]:
    """
    Fetch all games for a single player from hivegame.com

    Args:
        player: Username of the player
        max_games: Maximum number of games to fetch (default 100)
    Returns:
        List of HG_GameResponse objects with game details
    """
    logger.info(
        "Fetching games for player",
        player=player,
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
        # Query for finished games for this player (either as white or black)
        query_data = {
            "options": {
                **HG_GamesQueryOptions(
                    player1=HG_PlayerFilter(username=player),
                    player2=None,  # No specific opponent
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
        response = requests.post(
            full_endpoint,
            data=cbor_data,
            headers={
                "accept": "application/cbor",
                "content-type": "application/cbor",
            },
            timeout=30,
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

        logger.debug(
            "Successfully fetched games for player",
            count=len(all_games),
            player=player,
        )
        return all_games

    except Exception as e:
        logger.error(f"Error fetching games for player {player}: {e}", exc_info=True)
        return []
