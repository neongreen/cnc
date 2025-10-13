# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

"""Installation plan generation and execution."""

import json
import subprocess
from dataclasses import dataclass, field
from typing import Any

from cnc.want.requirements import Requirement, ToolRequirement


@dataclass
class InstallationStep:
    """A single step in the installation plan."""

    requirement: Requirement
    dependencies: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "requirement": self.requirement.to_dict(),
            "dependencies": self.dependencies,
        }


@dataclass
class InstallationPlan:
    """An installation plan consisting of ordered steps."""

    steps: list[InstallationStep] = field(default_factory=list)

    def add_step(self, requirement: Requirement, dependencies: list[int] | None = None) -> int:
        """Add a step to the plan and return its index."""
        step = InstallationStep(
            requirement=requirement,
            dependencies=dependencies or [],
        )
        self.steps.append(step)
        return len(self.steps) - 1

    def get_unsatisfied_steps(self) -> list[InstallationStep]:
        """Get steps that are not yet satisfied."""
        return [step for step in self.steps if not step.requirement.is_satisfied()]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "steps": [step.to_dict() for step in self.steps],
            "total_steps": len(self.steps),
            "unsatisfied_steps": len(self.get_unsatisfied_steps()),
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def display(self) -> str:
        """Display the plan in a human-readable format."""
        unsatisfied = self.get_unsatisfied_steps()
        if not unsatisfied:
            return "✓ All requirements are already satisfied!"

        lines = []
        lines.append(f"Installation plan ({len(unsatisfied)} step(s)):")
        lines.append("")

        step_num = 1
        for i, step in enumerate(self.steps):
            if not step.requirement.is_satisfied():
                prefix = f"  {step_num}."
                lines.append(f"{prefix} {step.requirement.get_description()}")
                if step.dependencies:
                    dep_nums = [str(self.steps.index(self.steps[d]) + 1) for d in step.dependencies]
                    lines.append(f"     (depends on: {', '.join(dep_nums)})")
                step_num += 1

        return "\n".join(lines)

    def execute(self, dry_run: bool = False) -> bool:
        """Execute the installation plan."""
        unsatisfied = self.get_unsatisfied_steps()
        if not unsatisfied:
            print("✓ All requirements are already satisfied!")
            return True

        if dry_run:
            print(self.display())
            return True

        print(self.display())
        print()

        for i, step in enumerate(self.steps):
            if step.requirement.is_satisfied():
                continue

            print(f"Executing step {i + 1}...")

            if isinstance(step.requirement, ToolRequirement):
                success = self._install_tool(step.requirement)
            else:
                # For other requirement types, we'd implement their execution here
                print(f"  Skipping unsupported requirement type: {type(step.requirement).__name__}")
                success = False

            if not success:
                print(f"✗ Failed to execute step {i + 1}")
                return False

            print(f"✓ Step {i + 1} completed")

        print()
        print("✓ Installation plan completed successfully!")
        return True

    def _install_tool(self, tool_req: ToolRequirement) -> bool:
        """Install a tool using mise."""
        try:
            # Build mise command
            tool_spec = f"{tool_req.tool_name}@{tool_req.version}"
            cmd = ["mise", "install", tool_spec]

            print(f"  Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            if result.stdout:
                print(f"  {result.stdout.strip()}")

            return True
        except subprocess.CalledProcessError as e:
            print(f"  Error: {e}")
            if e.stderr:
                print(f"  {e.stderr.strip()}")
            return False
        except FileNotFoundError:
            print("  Error: mise not found. Please install mise first.")
            return False
