from pathlib import Path
import tomllib
from pydantic import BaseModel

from cnc.hive.player_ids import HG_PlayerId, KnownPlayerId


class KnownPlayer(BaseModel):
    """Information about a player from hive.toml"""

    model_config = {"arbitrary_types_allowed": True}

    display_name: str
    group: str
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
        """Check if this player is a bot based on their group"""
        return self.group == "bot"


class ConfigSettings(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    group_order: list[str]
    highlight_games: list[str]
    fetch_outsiders: list[str]


class Config(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    settings: ConfigSettings
    players: dict[KnownPlayerId, KnownPlayer]


def get_config(file_path: Path) -> Config:
    """Get the config from hive.toml"""
    with file_path.open("rb") as f:
        data = tomllib.load(f)
    return Config.model_validate(data)
