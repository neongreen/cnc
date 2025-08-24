import sys
from pathlib import Path

# Add the src directory to the path so we can import the Python modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cnc.hive.table_generator_react import save_game_counts_json
from cnc.hive.database import HiveDatabase
from cnc.hive.config import get_config
from cnc.hive.fetch_hive_games import GameCache
from cnc.hive.games_data import create_games_list


def generate_data_files():
    """Generate all the data files needed for the site."""
    root = Path(__file__).parent.parent.parent
    data_dir = root / "data"
    build_dir = root / "build" / "data"

    print(root)

    print("Generating data files...")

    # Generate hive data
    print("  - Generating hive data...")
    config = get_config(data_dir / "hive.toml")
    db = HiveDatabase()

    cache_file = data_dir / "hive_games_cache.json"
    if cache_file.exists():
        all_games_raw = GameCache.model_validate_json(cache_file.read_text()).players
    else:
        all_games_raw = {}

    raw_games = create_games_list(
        [game for player_cache in all_games_raw.values() for game in player_cache.games]
    )
    db.load_data(config, raw_games)

    # Save JSON data
    hive_data_path = build_dir / "hive-data.json"
    save_game_counts_json(db, config, hive_data_path)
    print(f"    Saved hive data to {hive_data_path}")


def main():
    """Main build process."""

    try:
        generate_data_files()
        sys.exit(0)

    except Exception as e:
        print(f"❌ Build failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
