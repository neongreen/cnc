#!/usr/bin/env python3
# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

"""Test CLI execution with simulated arguments."""

import sys
from pathlib import Path
from io import StringIO

# Add src to path for testing without installation
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_cli_json_output():
    """Test --json flag."""
    print("=" * 60)
    print("Test: CLI with --json flag")
    print("=" * 60)

    # Backup original argv
    original_argv = sys.argv
    original_stdout = sys.stdout

    try:
        # Simulate command line: want --json node deno
        sys.argv = ["want", "--json", "node", "deno"]
        sys.stdout = StringIO()

        # Import and run main
        from cnc.want.cli import main

        try:
            main()
        except SystemExit:
            pass

        output = sys.stdout.getvalue()
        
        # Restore stdout before printing
        sys.stdout = original_stdout
        sys.argv = original_argv
        
        print(output)

        # Verify it's valid JSON
        import json
        data = json.loads(output)
        assert "steps" in data
        assert "total_steps" in data
        print("✓ Valid JSON output")

    except Exception as e:
        sys.argv = original_argv
        sys.stdout = original_stdout
        raise

    print()


def test_cli_dry_run():
    """Test --dry-run flag."""
    print("=" * 60)
    print("Test: CLI with --dry-run flag")
    print("=" * 60)

    # Backup original argv
    original_argv = sys.argv
    original_stdout = sys.stdout

    try:
        # Simulate command line: want --dry-run nonexistent_tool
        sys.argv = ["want", "--dry-run", "nonexistent_tool_xyz"]
        sys.stdout = StringIO()

        # Import and run main
        from cnc.want.cli import main

        try:
            main()
        except SystemExit:
            pass

        output = sys.stdout.getvalue()
        
        # Restore stdout before printing
        sys.stdout = original_stdout
        sys.argv = original_argv
        
        print(output)
        assert "Installation plan" in output or "nonexistent_tool_xyz" in output
        print("✓ Dry-run output looks correct")

    except Exception as e:
        sys.argv = original_argv
        sys.stdout = original_stdout
        raise

    print()


def test_cli_no_args():
    """Test CLI with no arguments (should show help)."""
    print("=" * 60)
    print("Test: CLI with no arguments")
    print("=" * 60)

    # Backup original argv
    original_argv = sys.argv
    original_stdout = sys.stdout

    try:
        # Simulate command line: want
        sys.argv = ["want"]
        sys.stdout = StringIO()

        # Import and run main
        from cnc.want.cli import main

        exit_code = None
        try:
            exit_code = main()
        except SystemExit as e:
            exit_code = e.code

        output = sys.stdout.getvalue()
        
        # Restore stdout before printing
        sys.stdout = original_stdout
        sys.argv = original_argv
        
        print(output)
        assert "usage:" in output or exit_code == 1
        print("✓ Shows help or exits with error")

    except Exception as e:
        sys.argv = original_argv
        sys.stdout = original_stdout
        raise

    print()


if __name__ == "__main__":
    test_cli_json_output()
    test_cli_dry_run()
    test_cli_no_args()
    print("All CLI execution tests passed!")
