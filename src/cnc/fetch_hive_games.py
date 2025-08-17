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

from cnc.hivegame import (
    HG_GameResponse,
    fetch_games_between_players,
    get_all_players,
    HiveGameNick,
    HivePlayerId,
    HivePlayerInfo,
)
from cnc.utils import get_logger

# Get logger for this module
logger = get_logger("fetch_hive_games")

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
    logger.info(f"Starting game fetch with cache from {cache_file}")
    logger.info(
        f"Force refresh: {force_refresh}, stale threshold: {stale_seconds} seconds"
    )

    # Load existing cache if it exists
    cache = GameCache(pairings={})
    if cache_file.exists() and not force_refresh:
        try:
            logger.info("Loading existing cache file")
            with open(cache_file, "r") as f:
                cache_data = json.load(f)
                # Convert JSON data back to GameCache object using Pydantic
                cache = GameCache.model_validate(cache_data)

            logger.info(f"Loaded {len(cache.pairings)} pairings from existing cache")

        except Exception as e:
            logger.error(f"Error loading existing cache: {e}", exc_info=True)
            cache = GameCache(pairings={})
    else:
        if force_refresh:
            logger.info("Force refresh requested, ignoring existing cache")
        else:
            logger.info("No existing cache file found, starting fresh")

    for (p1, p1_data), (p2, p2_data) in combinations(all_players.items(), 2):
        for p1_hivegame, p2_hivegame in product(p1_data.hivegame, p2_data.hivegame):
            logger.info(f"Processing @{p1_hivegame} vs @{p2_hivegame}")
            pairing_key = create_pairing_key(p1_hivegame, p2_hivegame)
            should_fetch = pairing_key not in cache.pairings or (
                cache.pairings[pairing_key].last_fetch
                < datetime.now() - timedelta(seconds=stale_seconds)
            )

            if should_fetch:
                try:
                    logger.info(f"Fetching games for {pairing_key}")
                    games = fetch_games_between_players(p1_hivegame, p2_hivegame)

                    # Merge games into existing cache entry
                    if pairing_key not in cache.pairings:
                        cache.pairings[pairing_key] = PairingCache(
                            last_fetch=datetime.now(), games=games
                        )
                    else:
                        cache.pairings[pairing_key] = PairingCache(
                            last_fetch=datetime.now(),
                            # Deduplicate games by game_id
                            games=list(
                                {
                                    g.game_id: g
                                    for g in (cache.pairings[pairing_key].games + games)
                                }.values()
                            ),
                        )

                    logger.info(f"Fetched {len(games)} games for {pairing_key}")
                except Exception as e:
                    logger.error(
                        f"Error fetching games for {pairing_key}: {e}",
                        exc_info=True,
                    )

    # Save updated cache
    try:
        logger.info(f"Saving cache to {cache_file}")
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

        logger.info("Cache saved successfully")

    except Exception as e:
        logger.error(f"Error saving cache: {e}", exc_info=True)

    return cache


def main():
    """Main function to fetch and cache Hive game data."""
    # Set up logging first
    from cnc.utils import setup_logging

    logger = setup_logging(console_output=True)

    logger.info("🎮 Hive Games Fetcher")
    logger.info("=" * 50)

    import argparse

    parser = argparse.ArgumentParser(description="Fetch and cache Hive game data")
    parser.add_argument(
        "--force", action="store_true", help="Force refresh all pairings"
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=7,
        help="Maximum age in days before refreshing (default: 7)",
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
        logger.info("🔄 Force refresh mode - will fetch all pairings")
    else:
        logger.info(f"📅 Will refresh pairings older than {args.max_age} days")

    logger.info(f"💾 Cache file: {cache_file}")

    # Get all players
    logger.info("📋 Loading player data...")
    all_players = get_all_players(project_root / "data" / "hive.toml")
    logger.info(f"Found {len(all_players)} players")

    # Fetch games with caching
    start_time = datetime.now()
    cache = fetch_all_player_games_with_cache(
        all_players,
        cache_file,
        force_refresh=args.force,
        stale_seconds=args.max_age * 60 * 60 * 24,
    )
    end_time = datetime.now()

    # Print summary
    logger.info("=" * 50)
    logger.info("📊 FETCH SUMMARY")
    logger.info("=" * 50)

    total_games = sum(
        len(pairing_data.games) for pairing_data in cache.pairings.values()
    )
    active_pairings = sum(
        1 for pairing_data in cache.pairings.values() if len(pairing_data.games) > 0
    )

    logger.info(f"Total pairings processed: {len(cache.pairings)}")
    logger.info(f"Active pairings (with games): {active_pairings}")
    logger.info(f"Total games cached: {total_games}")
    logger.info(f"Time taken: {end_time - start_time}")

    # Show games per current player (aggregating across all nicks)
    logger.info("👥 GAMES PER CURRENT PLAYER:")
    for player_id in all_players.keys():
        player_games = get_games_for_current_player(cache, all_players, player_id)
        if player_games:
            player_data = all_players[player_id]
            nick_info = ", ".join(f"@{nick}" for nick in player_data.hivegame)
            logger.info(f"  {player_id} ({nick_info}): {len(player_games)} games")

    # Show some stats about recent games
    logger.info("🎯 RECENT GAMES (last 30 days):")
    cutoff_date = datetime.now() - timedelta(days=30)
    recent_games = 0

    for pairing_key, pairing_data in cache.pairings.items():
        games = pairing_data.games
        for game in games:
            if game.created_at.replace(tzinfo=None) > cutoff_date:
                recent_games += 1
    logger.info(f"Games in last 30 days: {recent_games}")

    logger.info("✨ Done!")


if __name__ == "__main__":
    main()
