# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

"""Game data processing functions using data classes and lists"""

from dataclasses import dataclass
from typing import Literal
import structlog

from cnc.hive.config import KnownPlayer
from cnc.hive.hivegamecom import (
    HG_GameResponse,
    HG_GameStatusFinished,
)
from cnc.hive.player_ids import (
    HG_PlayerId,
    KnownPlayerId,
)

# Get logger for this module
logger = structlog.get_logger()


@dataclass
class RawGameData:
    """Raw game data extracted from HG_GameResponse"""

    game_id: str
    white_HG: HG_PlayerId
    black_HG: HG_PlayerId
    result: Literal["white", "black", "draw"]
    rated: bool

    def player_result(self, player: HG_PlayerId) -> Literal["win", "loss", "draw"]:
        """Determine the result for a specific player

        Args:
            player: The player's nickname to check
        """
        if self.result == "draw":
            return "draw"
        elif self.result == "white" and self.white_HG == player:
            return "win"
        elif self.result == "black" and self.black_HG == player:
            return "win"
        else:
            return "loss"


@dataclass
class GameData(RawGameData):
    """Transformed game data with player ID mappings"""

    white_id: KnownPlayerId | None
    black_id: KnownPlayerId | None
    white_info: KnownPlayer | None
    black_info: KnownPlayer | None


def create_games_list(raw_games_list: list[HG_GameResponse]) -> list[RawGameData]:
    """Convert raw HG_GameResponse games to a list of RawGameData objects"""
    games_data = []

    for game in raw_games_list:
        if not isinstance(game.game_status.root, HG_GameStatusFinished):
            logger.error(f"Unknown game status: {game.game_status.root}")
            continue

        # Determine result
        if game.game_status.root.Finished == "Draw":
            result = "draw"
        elif game.game_status.root.Finished.Winner == "White":
            result = "white"
        else:
            result = "black"

        games_data.append(
            RawGameData(
                game_id=game.game_id,
                white_HG=game.white_player.username,
                black_HG=game.black_player.username,
                result=result,
                rated=game.rated,
            )
        )

    return games_data


def merge_games_with_players(
    games_list: list[RawGameData], known_players: dict[KnownPlayerId, KnownPlayer]
) -> list[GameData]:
    """Add player_id mappings to games list and create canonical player IDs"""
    transformed_games = []

    for game in games_list:
        # Get white player info
        white_id, white_info = next(
            (
                (id, info)
                for id, info in known_players.items()
                if game.white_HG in info.hivegame
            ),
            (None, None),
        )

        # Get black player info
        black_id, black_info = next(
            (
                (id, info)
                for id, info in known_players.items()
                if game.black_HG in info.hivegame
            ),
            (None, None),
        )

        transformed_games.append(
            GameData(
                game_id=game.game_id,
                white_HG=game.white_HG,
                black_HG=game.black_HG,
                result=game.result,
                rated=game.rated,
                white_id=white_id,
                black_id=black_id,
                white_info=white_info,
                black_info=black_info,
            )
        )

    return transformed_games
