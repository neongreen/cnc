# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

import os
from typing import Generic, TypeVar
from datetime import datetime
import structlog


def setup_logging() -> None:
    env_level = os.getenv("LOG_LEVEL", "INFO").upper()
    if env_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        level = env_level
    else:
        print(f"Warning: Invalid LOG_LEVEL '{env_level}', defaulting to INFO")
        level = "INFO"
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )


def sort_tuple[T](t: tuple[T, T]) -> tuple[T, T]:
    """Sort a tuple of two elements."""
    return (t[0], t[1]) if t[0] < t[1] else (t[1], t[0])  # pyright: ignore


def pprint_dict(d: dict) -> str:
    """Pretty print a dictionary, handling Pydantic models and other objects."""
    import json

    def json_serializer(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if isinstance(obj, (datetime, bytes, bytearray)):
            return str(obj)
        return str(obj)

    return "\n".join(
        [f"{k}: {json.dumps(v, default=json_serializer)}" for k, v in d.items()]
    )


T = TypeVar("T")


class Pair(Generic[T]):
    def __init__(self, a: T, b: T):
        self.a, self.b = (a, b) if a < b else (b, a)  # type: ignore

    def __repr__(self):
        return f"Pair({self.a}, {self.b})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pair):
            return False
        return self.a == other.a and self.b == other.b

    def __hash__(self) -> int:
        return hash((self.a, self.b))
