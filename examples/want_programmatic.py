#!/usr/bin/env python3
# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

"""Example of programmatic usage of the want tool."""

from cnc.want.plan import InstallationPlan
from cnc.want.requirements import (
    CommandRequirement,
    FileRequirement,
    ToolRequirement,
)


def example_simple_installation():
    """Example: Simple tool installation plan."""
    print("=" * 60)
    print("Example 1: Simple Tool Installation")
    print("=" * 60)

    plan = InstallationPlan()

    # Add tools to install
    plan.add_step(ToolRequirement(tool_name="node", version="20.0.0"))
    plan.add_step(ToolRequirement(tool_name="python", version="3.13"))
    plan.add_step(ToolRequirement(tool_name="deno", version="latest"))

    # Display the plan
    print(plan.display())
    print()

    # Output as JSON
    print("JSON representation:")
    print(plan.to_json())
    print()


def example_with_dependencies():
    """Example: Installation with dependencies."""
    print("=" * 60)
    print("Example 2: Installation with Dependencies")
    print("=" * 60)

    plan = InstallationPlan()

    # Install node first
    node_idx = plan.add_step(ToolRequirement(tool_name="node", version="latest"))

    # Install pnpm (depends on node)
    pnpm_idx = plan.add_step(
        ToolRequirement(tool_name="pnpm", version="latest"),
        dependencies=[node_idx],
    )

    # Install project dependencies (depends on both node and pnpm)
    plan.add_step(
        CommandRequirement(
            command="pnpm install",
            description="Install project dependencies",
        ),
        dependencies=[node_idx, pnpm_idx],
    )

    print(plan.display())
    print()


def example_mixed_requirements():
    """Example: Mixed requirement types."""
    print("=" * 60)
    print("Example 3: Mixed Requirement Types")
    print("=" * 60)

    plan = InstallationPlan()

    # Check for configuration file
    config_idx = plan.add_step(FileRequirement(path="./config.toml"))

    # Install tools
    uv_idx = plan.add_step(ToolRequirement(tool_name="uv", version="latest"))

    # Run command (depends on tool and file)
    plan.add_step(
        CommandRequirement(
            command="uv sync",
            description="Sync Python dependencies",
        ),
        dependencies=[config_idx, uv_idx],
    )

    print(plan.display())
    print()


def example_development_environment():
    """Example: Complete development environment setup."""
    print("=" * 60)
    print("Example 4: Development Environment Setup")
    print("=" * 60)

    plan = InstallationPlan()

    # Install build tools
    node_idx = plan.add_step(ToolRequirement(tool_name="node", version="20.0.0"))
    python_idx = plan.add_step(ToolRequirement(tool_name="python", version="3.13"))

    # Install package managers
    pnpm_idx = plan.add_step(
        ToolRequirement(tool_name="pnpm", version="latest"),
        dependencies=[node_idx],
    )
    uv_idx = plan.add_step(
        ToolRequirement(tool_name="uv", version="latest"),
        dependencies=[python_idx],
    )

    # Install development tools
    plan.add_step(ToolRequirement(tool_name="watchexec", version="latest"))
    plan.add_step(ToolRequirement(tool_name="fd", version="latest"))
    plan.add_step(ToolRequirement(tool_name="dprint", version="latest"))

    # Install dependencies
    plan.add_step(
        CommandRequirement(
            command="pnpm install",
            description="Install Node.js dependencies",
        ),
        dependencies=[node_idx, pnpm_idx],
    )
    plan.add_step(
        CommandRequirement(
            command="uv sync",
            description="Install Python dependencies",
        ),
        dependencies=[python_idx, uv_idx],
    )

    print(plan.display())
    print()
    print("JSON representation:")
    print(plan.to_json())
    print()


if __name__ == "__main__":
    example_simple_installation()
    example_with_dependencies()
    example_mixed_requirements()
    example_development_environment()
