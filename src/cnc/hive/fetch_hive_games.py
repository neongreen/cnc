# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

"""
Script to fetch and cache Hive game data for all players.
This avoids having to fetch games every time the page is generated.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, NewType
from pydantic import BaseModel
import structlog

from cnc.hive.config import KnownPlayer, get_config
from cnc.hive.hivegamecom import (
    HG_GameResponse,
    fetch_games_for_player,
)
from cnc.hive.player_ids import KnownPlayerId
from cnc.utils import setup_logging

logger = structlog.get_logger()

PlayerKey = NewType("PlayerKey", str)
"""Key in the cache file, e.g. "@emily" for a player's games"""


class PlayerCache(BaseModel):
    """Cache for a single player's games"""

    last_fetch: datetime
    games: list[HG_GameResponse]


class GameCache(BaseModel):
    """Complete cache of all games and metadata"""

    players: Dict[PlayerKey, PlayerCache]


def get_games_for_current_player(
    cache: GameCache,
    all_players: Dict[KnownPlayerId, KnownPlayer],
    current_player_id: KnownPlayerId,
) -> list[HG_GameResponse]:
    """Get all games for a current player, aggregating across all their nicks (current + past)"""
    all_games = []

    player_data = all_players[current_player_id]

    # Find all cache entries that involve any of this player's nicks
    for player_key, player_data_cache in cache.players.items():
        games = player_data_cache.games
        player_nick = player_key.replace("@", "")

        # Check if this nick belongs to this player
        if player_nick in player_data.hivegame:
            all_games.extend(games)

    return all_games


def fetch_all_player_games_with_cache(
    known_players: dict[KnownPlayerId, KnownPlayer],
    cache_file: Path,
    force_refresh: bool = False,
    stale_seconds: int = (
        60 * 60 * 24 * 7
    ),  # if the cache for a player is older than this, fetch new games
) -> GameCache:
    """Fetch all games for all players, using cache when possible"""
    logger.debug("Starting game fetch", cache_file=str(cache_file))

    # Load existing cache if it exists
    cache = GameCache(players={})
    if cache_file.exists() and not force_refresh:
        try:
            logger.debug("Loading existing cache file")
            with open(cache_file, "r") as f:
                cache_data = json.load(f)
                # Convert JSON data back to GameCache object using Pydantic
                cache = GameCache.model_validate(cache_data)

            logger.info(
                "Loaded cache", games=sum(len(p.games) for p in cache.players.values())
            )

        except Exception as e:
            logger.error(f"Error loading existing cache: {e}", exc_info=True)
            cache = GameCache(players={})
    else:
        if force_refresh:
            logger.info("Force refresh requested, ignoring existing cache")
        else:
            logger.info("No existing cache file found, starting fresh")

    had_to_fetch = False  # Whether we had to fetch any games
    new_games = 0  # Number of new games fetched

    # Fetch games for each player
    for player_id, player_data in known_players.items():
        for hivegame_nick in player_data.hivegame:
            player_key = PlayerKey(f"@{hivegame_nick}")
            logger.debug("Processing player", player=player_id, hivegame=hivegame_nick)

            should_fetch = False
            if player_key not in cache.players:
                logger.debug("Player not in cache, fetching", player_key=player_key)
                should_fetch = True
            else:
                logger.debug(
                    "Player in cache, checking if stale", player_key=player_key
                )
                last_fetch = cache.players[player_key].last_fetch
                # Normalize to aware UTC (treat legacy naive values as UTC)
                if last_fetch.tzinfo is None:
                    last_fetch = last_fetch.replace(tzinfo=timezone.utc)
                is_stale = last_fetch < datetime.now(timezone.utc) - timedelta(
                    seconds=stale_seconds
                ) or (stale_seconds == 0)
                logger.debug(
                    "Player is stale, fetching"
                    if is_stale
                    else "Player is not stale, skipping fetch",
                    last_fetch=last_fetch.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    stale_seconds=stale_seconds,
                )
                should_fetch = is_stale

            if should_fetch:
                had_to_fetch = True
                try:
                    games = fetch_games_for_player(hivegame_nick)

                    # Merge games into existing cache entry
                    if player_key not in cache.players:
                        cache.players[player_key] = PlayerCache(
                            last_fetch=datetime.now(timezone.utc), games=games
                        )
                        new_games += len(games)
                    else:
                        # Deduplicate games by game_id
                        cached_games = cache.players[player_key].games
                        updated_games = list(
                            {g.game_id: g for g in (cached_games + games)}.values()
                        )
                        new_games += len(updated_games) - len(cached_games)
                        cache.players[player_key] = PlayerCache(
                            last_fetch=datetime.now(timezone.utc), games=updated_games
                        )
                except Exception as e:
                    logger.error(
                        f"Error fetching games for {player_key}: {e}",
                        exc_info=True,
                    )

    if had_to_fetch:
        logger.info("Fetch summary", new_games=new_games)
    else:
        logger.info("Cache is not stale and there are no new players, skipping fetch")

    # Save updated cache
    try:
        logger.debug("Saving cache", cache_file=str(cache_file))
        cache_data = {
            "players": cache.players,
        }

        # Ensure cache directory exists
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        with open(cache_file, "w") as f:
            json.dump(
                cache_data,
                f,
                indent=2,
                default=lambda obj: obj.model_dump()
                if hasattr(obj, "model_dump")
                else (
                    obj.isoformat().replace("+00:00", "Z")
                    if isinstance(obj, datetime)
                    else str(obj)
                ),
            )

        logger.debug("Cache saved successfully")

    except Exception as e:
        logger.error(f"Error saving cache: {e}", exc_info=True)

    return cache


def main():
    """Main function to fetch and cache Hive game data."""

    setup_logging()

    import argparse

    parser = argparse.ArgumentParser(description="Fetch and cache Hive game data")
    parser.add_argument(
        "--force", action="store_true", help="Force refresh all pairings"
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=60 * 10,  # 10 minutes
        help="Maximum age in seconds before refreshing",
    )
    parser.add_argument(
        "--cache-file",
        default="data/hive_games_cache.json",
        help="Cache file path (default: data/hive_games_cache.json)",
    )

    args = parser.parse_args()

    # Get project root (go up from src/cnc/ to project root)
    project_root = Path(
        __file__
    ).parent.parent.parent.parent  # TODO: don't hardcode this
    cache_file = project_root / args.cache_file

    if args.force:
        logger.info("Force refresh mode - will fetch all pairings")
    else:
        logger.info(f"Will refresh pairings older than {args.max_age} seconds")

    # Get all players
    config = get_config(project_root / "data" / "hive.toml")
    all_players = config.players

    # Fetch games with caching
    cache = fetch_all_player_games_with_cache(
        all_players,
        cache_file,
        force_refresh=args.force,
        stale_seconds=args.max_age,
    )

    # Show games per current player (aggregating across all nicks)
    logger.info(
        "Games per player",
        **{
            str(player_id): len(player_games)
            for player_id in all_players.keys()
            if (
                player_games := get_games_for_current_player(
                    cache, all_players, player_id
                )
            )
        },
    )


if __name__ == "__main__":
    main()
