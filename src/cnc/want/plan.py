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
        step_idx = len(self.steps) - 1
        
        # Validate no cycles
        if self._has_cycle(step_idx):
            self.steps.pop()
            raise ValueError("Adding this step would create a dependency cycle")
        
        return step_idx

    def _has_cycle(self, start_idx: int) -> bool:
        """Check if adding a step creates a cycle in the dependency graph."""
        visited = set()
        
        def visit(idx: int, path: set[int]) -> bool:
            if idx in path:
                return True
            if idx in visited:
                return False
            
            visited.add(idx)
            path.add(idx)
            
            for dep_idx in self.steps[idx].dependencies:
                if dep_idx < 0 or dep_idx >= len(self.steps):
                    raise ValueError(f"Invalid dependency index {dep_idx} (valid range: 0-{len(self.steps)-1})")
                if visit(dep_idx, path):
                    return True
            
            path.remove(idx)
            return False
        
        return visit(start_idx, set())

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

        # Create a mapping from step index to display number (only for unsatisfied)
        step_to_display_num = {}
        display_num = 1
        for i, step in enumerate(self.steps):
            if not step.requirement.is_satisfied():
                step_to_display_num[i] = display_num
                display_num += 1

        # Display unsatisfied steps
        for i, step in enumerate(self.steps):
            if not step.requirement.is_satisfied():
                num = step_to_display_num[i]
                prefix = f"  {num}."
                lines.append(f"{prefix} {step.requirement.get_description()}")
                
                # Show dependencies (only those that are unsatisfied)
                unsatisfied_deps = [d for d in step.dependencies if d in step_to_display_num]
                if unsatisfied_deps:
                    dep_nums = [str(step_to_display_num[d]) for d in unsatisfied_deps]
                    lines.append(f"     (depends on: {', '.join(dep_nums)})")

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

        # Create mapping for display numbers
        step_to_display_num = {}
        display_num = 1
        for i, step in enumerate(self.steps):
            if not step.requirement.is_satisfied():
                step_to_display_num[i] = display_num
                display_num += 1

        for i, step in enumerate(self.steps):
            if step.requirement.is_satisfied():
                continue

            step_num = step_to_display_num[i]
            print(f"[{step_num}/{len(unsatisfied)}] {step.requirement.get_description()}")

            if isinstance(step.requirement, ToolRequirement):
                success = self._install_tool(step.requirement)
            else:
                # For other requirement types, we'd implement their execution here
                print(f"  ⚠ Skipping unsupported requirement type: {type(step.requirement).__name__}")
                success = False

            if not success:
                print(f"  ✗ Step {step_num} failed")
                return False

            print(f"  ✓ Step {step_num} completed")
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
