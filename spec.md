# Hive Configuration Update Implementation Plan

## Overview

Update the table generator and related components to use the new group-based configuration system instead of hardcoded logic.

## Key Changes Made to hive.toml

### 1. Settings Section Transformation

- **Removed**: `skip_highlight = ["emily", "easybot", "mediumbot", "hardbot"]`
- **Added**:
  - `group_order = ["emily", "crc", "bot", "(outsider)"]` - defines display order
  - `highlight_games = ["crc"]` - highlights games between CRC players
  - `fetch_outsiders = ["emily", "crc"]` - only fetch outsider games for these groups

### 2. Player Structure Changes

- **Added**: `group` field to every player (emily, crc, bot)
- **Removed**: `bot = true` from bot players (now using `group = "bot"` instead)
- **Added**: Clear section headers for organization

## Implementation Changes Required

### 1. Configuration Models (`src/cnc/hive/config.py`)

- Update `ConfigSettings` to include new fields:
  - `group_order: list[str]`
  - `highlight_games: list[str]`
  - `fetch_outsiders: list[str]`
- Update `KnownPlayer` to include `group: str` field
- Remove `bot: bool` field (replaced by group system)

### 2. Database Schema (`src/cnc/hive/schema.sql`)

- Replace `bot BOOLEAN DEFAULT FALSE` with `group TEXT NOT NULL`
- Update any existing data migration if needed

### 3. Table Generator (`src/cnc/hive/table_generator.py`)

- **Pass configuration to function**: `generate_game_counts_table(db: HiveDatabase, config: Config)`
- **Respect group_order**: Sort players according to `config.settings.group_order`
- **Dynamic outsider calculation**: Use `config.settings.fetch_outsiders` instead of hardcoded SQL
- **Implement highlighting**: Add CSS classes for games between players in `config.settings.highlight_games`

### 4. Database Operations (`src/cnc/hive/database.py`)

- Update `load_toml_data` to handle `group` field instead of `bot`
- Update any SQL queries that reference the old `bot` field

### 5. HTML Generation (`src/cnc/hive/html_generator.py`)

- Pass config to table generator
- Update template rendering to handle new highlighting

## Key Principles

### Configuration-Driven, Not Hardcoded

- **Outsider calculation**: Defined by `fetch_outsiders = ["emily", "crc"]` in TOML
- **Group ordering**: Defined by `group_order` in TOML
- **Game highlighting**: Defined by `highlight_games` in TOML
- **No hardcoded group names** in SQL or Python code (except "outsider" which is special)

### Outsider Logic

Instead of hardcoded SQL like:

```sql
WHERE known_black_player NOT IN (SELECT id FROM players WHERE bot = true)
```

Use configuration-driven approach:

```sql
WHERE known_black_player NOT IN (
    SELECT id FROM players
    WHERE group = ANY($fetch_outsiders_groups)
)
```

## Expected Results

1. **Players display in specified group order**: emily → crc → bot → outsider
2. **CRC vs CRC games are highlighted** with special styling
3. **Outsider games only calculated** for players from groups in `fetch_outsiders`
4. **System is extensible** - easy to add new groups without code changes
5. **Configuration is the single source of truth** for behavior

## Files to Modify

- `src/cnc/hive/config.py` - Update models
- `src/cnc/hive/schema.sql` - Update database schema
- `src/cnc/hive/table_generator.py` - Implement new logic
- `src/cnc/hive/database.py` - Update data loading
- `src/cnc/hive/html_generator.py` - Pass config through
- `templates/hive.html.j2` - Add highlighting CSS classes
