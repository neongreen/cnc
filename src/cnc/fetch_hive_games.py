"""
Script to fetch and cache Hive game data between all players.
This avoids having to fetch games every time the page is generated.
"""

from itertools import combinations, product
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, NewType, Tuple
from pydantic import BaseModel
import structlog

from cnc.hivegame import (
    HG_GameResponse,
    fetch_games_between_players,
    get_all_players,
    HiveGameNick,
    HivePlayerId,
    HivePlayerInfo,
)
from cnc.utils import setup_logging

logger = structlog.get_logger()

PairingKey = NewType("PairingKey", str)
"""Key in the cache file, e.g. "@emily|@yew", with the nicks sorted alphabetically"""


def create_pairing_key(player1: HiveGameNick, player2: HiveGameNick) -> PairingKey:
    """Create a unique pairing key with players in alphabetical order"""
    # Sort players alphabetically to ensure unique encoding
    if player1.lower() < player2.lower():
        return PairingKey(f"@{player1}|@{player2}")
    else:
        return PairingKey(f"@{player2}|@{player1}")


def parse_pairing_key(pairing_key: PairingKey) -> Tuple[HiveGameNick, HiveGameNick]:
    """Parse a pairing key back to player nicks"""
    # Remove @ symbols and split by |
    players = pairing_key.replace("@", "").split("|")
    return HiveGameNick(players[0]), HiveGameNick(players[1])


class PairingCache(BaseModel):
    """Cache for a single pairing"""

    last_fetch: datetime
    games: list[HG_GameResponse]


class GameCache(BaseModel):
    """Complete cache of all games and metadata"""

    pairings: Dict[PairingKey, PairingCache]


def get_games_for_current_player(
    cache: GameCache,
    all_players: Dict[HivePlayerId, HivePlayerInfo],
    current_player_id: HivePlayerId,
) -> list[HG_GameResponse]:
    """Get all games for a current player, aggregating across all their nicks (current + past)"""
    all_games = []

    player_data = all_players[current_player_id]

    # Find all cache entries that involve any of this player's nicks
    for pairing_key, pairing_data in cache.pairings.items():
        games = pairing_data.games
        nick1, nick2 = parse_pairing_key(pairing_key)

        # Check if either nick belongs to this player
        if nick1 in player_data.hivegame or nick2 in player_data.hivegame:
            all_games.extend(games)

    return all_games


def fetch_all_player_games_with_cache(
    all_players: dict[HivePlayerId, HivePlayerInfo],
    cache_file: Path,
    force_refresh: bool = False,
    stale_seconds: int = (
        60 * 60 * 24 * 7
    ),  # if the cache for a pairing is older than this, fetch new games
) -> GameCache:
    """Fetch all games between all players, using cache when possible"""
    logger.debug("Starting game fetch", cache_file=str(cache_file))

    # Load existing cache if it exists
    cache = GameCache(pairings={})
    if cache_file.exists() and not force_refresh:
        try:
            logger.debug("Loading existing cache file")
            with open(cache_file, "r") as f:
                cache_data = json.load(f)
                # Convert JSON data back to GameCache object using Pydantic
                cache = GameCache.model_validate(cache_data)

            logger.info(
                "Loaded cache", games=sum(len(p.games) for p in cache.pairings.values())
            )

        except Exception as e:
            logger.error(f"Error loading existing cache: {e}", exc_info=True)
            cache = GameCache(pairings={})
    else:
        if force_refresh:
            logger.info("Force refresh requested, ignoring existing cache")
        else:
            logger.info("No existing cache file found, starting fresh")

    had_to_fetch = False  # Whether we had to fetch any games
    new_games = 0  # Number of new games fetched

    for (p1, p1_data), (p2, p2_data) in combinations(all_players.items(), 2):
        for p1_hivegame, p2_hivegame in product(p1_data.hivegame, p2_data.hivegame):
            logger.debug("Processing pairing", p1=p1_hivegame, p2=p2_hivegame)
            pairing_key = create_pairing_key(p1_hivegame, p2_hivegame)
            should_fetch = False
            if pairing_key not in cache.pairings:
                logger.debug("Pairing not in cache, fetching", pairing_key=pairing_key)
                should_fetch = True
            else:
                logger.debug(
                    "Pairing in cache, checking if stale", pairing_key=pairing_key
                )
                last_fetch = cache.pairings[pairing_key].last_fetch
                is_stale = last_fetch < datetime.now() - timedelta(
                    seconds=stale_seconds
                )
                logger.debug(
                    "Pairing is stale, fetching"
                    if is_stale
                    else "Pairing is not stale, skipping fetch",
                    last_fetch=last_fetch.strftime("%Y-%m-%d %H:%M:%S"),
                    stale_seconds=stale_seconds,
                )
                should_fetch = is_stale

            if should_fetch:
                had_to_fetch = True
                try:
                    games = fetch_games_between_players(p1_hivegame, p2_hivegame)

                    # Merge games into existing cache entry
                    if pairing_key not in cache.pairings:
                        cache.pairings[pairing_key] = PairingCache(
                            last_fetch=datetime.now(), games=games
                        )
                        new_games += len(games)
                    else:
                        # Deduplicate games by game_id
                        cached_games = cache.pairings[pairing_key].games
                        updated_games = list(
                            {g.game_id: g for g in (cached_games + games)}.values()
                        )
                        new_games += len(updated_games) - len(cached_games)
                        cache.pairings[pairing_key] = PairingCache(
                            last_fetch=datetime.now(), games=updated_games
                        )
                except Exception as e:
                    logger.error(
                        f"Error fetching games for {pairing_key}: {e}",
                        exc_info=True,
                    )

    if had_to_fetch:
        logger.info("Fetch summary", new_games=new_games)
    else:
        logger.info("Cache is not stale and there are no new pairings, skipping fetch")

    # Save updated cache
    try:
        logger.debug("Saving cache", cache_file=str(cache_file))
        cache_data = {
            "pairings": cache.pairings,
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
                else str(obj),
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
        default=0,
        help="Maximum age in days before refreshing",
    )
    parser.add_argument(
        "--cache-file",
        default="data/hive_games_cache.json",
        help="Cache file path (default: data/hive_games_cache.json)",
    )

    args = parser.parse_args()

    # Get project root (go up from src/cnc/ to project root)
    project_root = Path(__file__).parent.parent.parent
    cache_file = project_root / args.cache_file

    if args.force:
        logger.info("Force refresh mode - will fetch all pairings")
    else:
        logger.info(f"Will refresh pairings older than {args.max_age} days")

    # Get all players
    all_players = get_all_players(project_root / "data" / "hive.toml")

    # Fetch games with caching
    cache = fetch_all_player_games_with_cache(
        all_players,
        cache_file,
        force_refresh=args.force,
        stale_seconds=args.max_age * 60 * 60 * 24,
    )

    # Show games per current player (aggregating across all nicks)
    logger.info(
        "Games per player",
        **{
            player_id: len(player_games)
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
