# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

from pathlib import Path
import tomllib
from pydantic import BaseModel, model_validator

from cnc.hive.player_ids import HG_PlayerId, KnownPlayerId


class KnownPlayer(BaseModel):
    """Information about a player from hive.toml"""

    model_config = {"arbitrary_types_allowed": True}

    display_name: str
    groups: list[str]
    hivegame: list[HG_PlayerId]
    hivegame_current: HG_PlayerId | None = None

    @property
    def current_nick(self) -> HG_PlayerId:
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

    @property
    def is_bot(self) -> bool:
        """Check if this player is a bot based on their groups"""
        return "bot" in self.groups


class ConfigSettings(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    group_order: list[str]
    highlight_games: list[str]
    fetch_outsiders: list[str]


class Config(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    settings: ConfigSettings
    players: dict[KnownPlayerId, KnownPlayer]

    @model_validator(mode='after')
    def validate_groups_in_order(self):
        """Validate that all groups used by players are defined in group_order"""
        valid_groups = set(self.settings.group_order)
        valid_groups.add("(outsider)")  # Special group that doesn't need to be in group_order
        
        # Collect all groups used by players
        used_groups = set()
        for player_id, player in self.players.items():
            for group in player.groups:
                used_groups.add(group)
        
        # Check for undefined groups
        undefined_groups = used_groups - valid_groups
        if undefined_groups:
            undefined_list = sorted(undefined_groups)
            raise ValueError(
                f"Groups {undefined_list} are used by players but not defined in settings.group_order. "
                f"Current group_order: {self.settings.group_order}"
            )
        
        return self


def get_config(file_path: Path) -> Config:
    """Get the config from hive.toml"""
    with file_path.open("rb") as f:
        data = tomllib.load(f)
    return Config.model_validate(data)
