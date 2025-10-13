# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

"""Requirement types and definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Requirement(ABC):
    """Base class for all requirements."""

    @abstractmethod
    def is_satisfied(self) -> bool:
        """Check if the requirement is already satisfied."""
        pass

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert requirement to dictionary for JSON serialization."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get a human-readable description of the requirement."""
        pass


@dataclass
class ToolRequirement(Requirement):
    """Requirement for a tool to be installed via mise."""

    tool_name: str
    version: str = "latest"

    def is_satisfied(self) -> bool:
        """Check if the tool is already installed."""
        import shutil
        import subprocess

        # Check if tool is available in PATH
        if shutil.which(self.tool_name):
            # If version is "latest", we consider it satisfied
            if self.version == "latest":
                return True
            # TODO: Check version if specific version is required
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": "tool",
            "tool_name": self.tool_name,
            "version": self.version,
            "satisfied": self.is_satisfied(),
        }

    def get_description(self) -> str:
        """Get description."""
        version_str = f"@{self.version}" if self.version != "latest" else ""
        return f"Install tool: {self.tool_name}{version_str}"


@dataclass
class CommandRequirement(Requirement):
    """Requirement that executes a command."""

    command: str
    description: str

    def is_satisfied(self) -> bool:
        """Commands are never pre-satisfied."""
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": "command",
            "command": self.command,
            "description": self.description,
            "satisfied": self.is_satisfied(),
        }

    def get_description(self) -> str:
        """Get description."""
        return f"Run command: {self.description}"


@dataclass
class FileRequirement(Requirement):
    """Requirement for a file to exist."""

    path: str

    def is_satisfied(self) -> bool:
        """Check if file exists."""
        from pathlib import Path
        return Path(self.path).exists()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": "file",
            "path": self.path,
            "satisfied": self.is_satisfied(),
        }

    def get_description(self) -> str:
        """Get description."""
        return f"Require file: {self.path}"
