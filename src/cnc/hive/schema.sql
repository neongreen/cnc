-- Hive Database Schema
-- This file contains all table definitions for the Hive game data processing

-- Create enum type for game results
CREATE TYPE game_result AS ENUM ('white', 'black', 'draw');

-- Players table (from hive.toml)
CREATE TABLE players (
    id TEXT PRIMARY KEY,           -- player#emily
    display_name TEXT NOT NULL,    -- "Emily"
    bot BOOLEAN DEFAULT FALSE,
    hivegame_nicks TEXT[] NOT NULL,  -- ["HG#ParathaBread", "HG#emily"]
    hivegame_current TEXT NOT NULL  -- "HG#emily"
);

-- Games table (from hivegame.com API)
CREATE TABLE hg_games (
    id TEXT PRIMARY KEY,           -- 12345
    hg_white_player TEXT NOT NULL,    -- HG#ParathaBread
    hg_black_player TEXT NOT NULL,    -- HG#nokamute-easy
    known_white_player TEXT,          -- player#emily, if known
    known_black_player TEXT,          -- player#emily, if known
    result game_result NOT NULL,
    rated BOOLEAN NOT NULL,
    date_played DATE,
    time_control TEXT
);

-- TODO: use sqlc to generate python apis from sql queries?