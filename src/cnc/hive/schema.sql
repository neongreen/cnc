-- Copyright (c) 2025 Emily
--
-- This work is licensed under the Creative Commons Zero v1.0 Universal License.
--
-- To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
--
-- You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

-- Hive Database Schema
-- This file contains all table definitions for the Hive game data processing

-- Create enum type for game results
CREATE TYPE game_result AS ENUM ('white', 'black', 'draw');

-- Players table (from hive.toml)
CREATE TABLE players (
    id TEXT PRIMARY KEY,           -- player#emily
    display_name TEXT NOT NULL,    -- "Emily"
    groups TEXT[] NOT NULL,        -- ["emily"], ["crc"], ["crc", "momoh"]
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