# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

"""CLI interface for the want tool."""

import argparse
import sys

from cnc.want.plan import InstallationPlan
from cnc.want.requirements import ToolRequirement


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="want",
        description="Declarative dependency management tool",
    )

    parser.add_argument(
        "tools",
        nargs="*",
        help="Tools to install (format: tool[@version])",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the installation plan as JSON instead of executing it",
    )

    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Automatically answer yes to all prompts",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it",
    )

    return parser


def parse_tool_spec(spec: str) -> tuple[str, str]:
    """Parse a tool specification like 'tool@version' or 'tool'."""
    if "@" in spec:
        tool, version = spec.split("@", 1)
        return tool, version
    return spec, "latest"


def confirm_plan(plan: InstallationPlan) -> bool:
    """Ask user to confirm the installation plan."""
    unsatisfied = plan.get_unsatisfied_steps()
    
    print()
    print(plan.display())
    print()
    
    # Show summary
    print(f"This will install {len(unsatisfied)} item(s) using mise.")
    print()

    try:
        response = input("Proceed with installation? [y/N] ").strip().lower()
        return response in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        print()
        return False


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Create installation plan
    plan = InstallationPlan()

    # Parse tool specifications and add to plan
    for tool_spec in args.tools:
        tool_name, version = parse_tool_spec(tool_spec)
        requirement = ToolRequirement(tool_name=tool_name, version=version)
        plan.add_step(requirement)

    # If no tools specified, show help
    if not args.tools:
        parser.print_help()
        return 1

    # Output as JSON if requested
    if args.json:
        print(plan.to_json())
        return 0

    # Check if anything needs to be done
    unsatisfied = plan.get_unsatisfied_steps()
    satisfied_count = len(plan.steps) - len(unsatisfied)
    
    if satisfied_count > 0:
        print(f"✓ {satisfied_count} requirement(s) already satisfied")
    
    if not unsatisfied:
        print("✓ All requirements are already satisfied!")
        return 0

    # Show plan and ask for confirmation (unless --yes or --dry-run)
    if args.dry_run:
        print(plan.display())
        return 0

    if not args.yes:
        if not confirm_plan(plan):
            print("Installation cancelled.")
            return 1
    else:
        print(plan.display())
        print()

    # Execute the plan
    success = plan.execute()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
