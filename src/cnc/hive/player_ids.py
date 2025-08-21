# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

"""Type-safe player ID classes for the Hive game system.

This module defines separate classes for different types of player identifiers
to eliminate ambiguity between hivegame.com usernames, known player IDs, etc.
"""

from typing import Any
from pydantic_core import core_schema


class KnownPlayerId(str):
    """A player ID from hive.toml - represents a known player in our system."""

    def __new__(cls, value: str):
        if not value or not value.strip():
            raise ValueError("Player ID cannot be empty")
        return super().__new__(cls, value.strip())

    def __repr__(self) -> str:
        return f"KnownPlayerId('{self}')"

    def tagged(self) -> str:
        return f"player#{self}"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler
    ) -> core_schema.CoreSchema:
        """Pydantic v2 validator for automatic string conversion."""
        return core_schema.with_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )

    @classmethod
    def _validate(cls, v: str, info) -> "KnownPlayerId":
        """Validate and convert string to KnownPlayerId."""
        return cls(v)


class HG_PlayerId(str):
    """A player ID from hivegame.com - represents a username on the platform."""

    def __new__(cls, value: str):
        if not value or not value.strip():
            raise ValueError("Hivegame player ID cannot be empty")
        # Remove @ prefix if present
        return super().__new__(cls, value.strip().lstrip("@"))

    def __repr__(self) -> str:
        return f"HivegamePlayerId('{self}')"

    def tagged(self) -> str:
        return f"HG#{self}"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler
    ) -> core_schema.CoreSchema:
        """Pydantic v2 validator for automatic string conversion."""
        return core_schema.with_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )

    @classmethod
    def _validate(cls, v: str, info) -> "HG_PlayerId":
        """Validate and convert string to HG_PlayerId."""
        return cls(v)
