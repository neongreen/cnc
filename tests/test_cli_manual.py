#!/usr/bin/env python3
# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

"""Manual test of CLI functionality."""

import sys
from pathlib import Path

# Add src to path for testing without installation
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cnc.want.cli import create_parser, parse_tool_spec


def test_cli_help():
    """Test CLI help output."""
    print("=" * 60)
    print("Test: CLI Help")
    print("=" * 60)
    parser = create_parser()
    parser.print_help()
    print()


def test_cli_parse_args():
    """Test CLI argument parsing."""
    print("=" * 60)
    print("Test: CLI Argument Parsing")
    print("=" * 60)

    parser = create_parser()

    # Test basic tool specification
    args = parser.parse_args(["node", "python"])
    print(f"Tools: {args.tools}")
    print(f"JSON: {args.json}")
    print(f"Yes: {args.yes}")
    print(f"Dry-run: {args.dry_run}")
    print()

    # Test with options
    args = parser.parse_args(["--json", "node@20.0.0"])
    print(f"Tools: {args.tools}")
    print(f"JSON: {args.json}")
    print()

    # Test with --yes
    args = parser.parse_args(["-y", "deno"])
    print(f"Tools: {args.tools}")
    print(f"Yes: {args.yes}")
    print()


def test_parse_tool_specs():
    """Test tool specification parsing."""
    print("=" * 60)
    print("Test: Tool Specification Parsing")
    print("=" * 60)

    specs = [
        "node",
        "node@20.0.0",
        "python@3.13",
        "deno@latest",
    ]

    for spec in specs:
        tool, version = parse_tool_spec(spec)
        print(f"{spec:20s} -> tool={tool:10s} version={version}")
    print()


if __name__ == "__main__":
    test_cli_help()
    test_cli_parse_args()
    test_parse_tool_specs()
