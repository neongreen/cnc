#!/usr/bin/env python3
# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

"""Demo script showing want tool usage."""

import sys
from pathlib import Path

# Add src to path for testing without installation
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cnc.want.plan import InstallationPlan
from cnc.want.requirements import ToolRequirement


def demo_simple_plan():
    """Demo: Simple installation plan."""
    print("=" * 60)
    print("Demo 1: Simple Installation Plan")
    print("=" * 60)
    print()

    plan = InstallationPlan()
    plan.add_step(ToolRequirement(tool_name="node", version="latest"))
    plan.add_step(ToolRequirement(tool_name="python", version="3.13"))

    print(plan.display())
    print()


def demo_json_output():
    """Demo: JSON output."""
    print("=" * 60)
    print("Demo 2: JSON Output")
    print("=" * 60)
    print()

    plan = InstallationPlan()
    plan.add_step(ToolRequirement(tool_name="node", version="20.0.0"))
    plan.add_step(ToolRequirement(tool_name="deno", version="latest"))

    print(plan.to_json())
    print()


def demo_with_dependencies():
    """Demo: Plan with dependencies."""
    print("=" * 60)
    print("Demo 3: Plan with Dependencies")
    print("=" * 60)
    print()

    plan = InstallationPlan()
    idx1 = plan.add_step(ToolRequirement(tool_name="node", version="latest"))
    idx2 = plan.add_step(ToolRequirement(tool_name="pnpm", version="latest"))
    plan.add_step(
        ToolRequirement(tool_name="typescript", version="latest"),
        dependencies=[idx1, idx2],
    )

    print(plan.display())
    print()


def demo_satisfied_requirements():
    """Demo: Already satisfied requirements."""
    print("=" * 60)
    print("Demo 4: Already Satisfied Requirements")
    print("=" * 60)
    print()

    plan = InstallationPlan()
    # Python3 should be available on most systems
    plan.add_step(ToolRequirement(tool_name="python3", version="latest"))

    print(plan.display())
    print()


if __name__ == "__main__":
    demo_simple_plan()
    demo_json_output()
    demo_with_dependencies()
    demo_satisfied_requirements()
