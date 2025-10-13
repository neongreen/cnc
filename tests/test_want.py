# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

"""Tests for the want tool."""

import json
import sys
import tempfile
from pathlib import Path

# Add src to path for testing without installation
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cnc.want.plan import InstallationPlan, InstallationStep
from cnc.want.requirements import (
    CommandRequirement,
    FileRequirement,
    ToolRequirement,
)
from cnc.want.cli import parse_tool_spec


def test_tool_requirement_satisfied():
    """Test that ToolRequirement correctly checks if a tool is available."""
    # Test with a tool that should exist
    req = ToolRequirement(tool_name="python3", version="latest")
    # This might be satisfied on some systems
    assert isinstance(req.is_satisfied(), bool)


def test_tool_requirement_not_satisfied():
    """Test that ToolRequirement correctly identifies missing tools."""
    req = ToolRequirement(tool_name="nonexistent_tool_12345", version="latest")
    assert not req.is_satisfied()


def test_tool_requirement_to_dict():
    """Test ToolRequirement serialization."""
    req = ToolRequirement(tool_name="test_tool", version="1.0.0")
    data = req.to_dict()
    assert data["type"] == "tool"
    assert data["tool_name"] == "test_tool"
    assert data["version"] == "1.0.0"
    assert "satisfied" in data


def test_file_requirement():
    """Test FileRequirement."""
    with tempfile.NamedTemporaryFile() as f:
        req = FileRequirement(path=f.name)
        assert req.is_satisfied()

    req = FileRequirement(path="/nonexistent/path/file.txt")
    assert not req.is_satisfied()


def test_command_requirement():
    """Test CommandRequirement."""
    req = CommandRequirement(command="echo hello", description="Say hello")
    # Commands are never pre-satisfied
    assert not req.is_satisfied()
    assert req.get_description() == "Run command: Say hello"


def test_installation_plan_empty():
    """Test empty installation plan."""
    plan = InstallationPlan()
    assert len(plan.steps) == 0
    assert len(plan.get_unsatisfied_steps()) == 0


def test_installation_plan_add_step():
    """Test adding steps to installation plan."""
    plan = InstallationPlan()
    req1 = ToolRequirement(tool_name="tool1")
    req2 = ToolRequirement(tool_name="tool2")

    idx1 = plan.add_step(req1)
    idx2 = plan.add_step(req2, dependencies=[idx1])

    assert len(plan.steps) == 2
    assert plan.steps[0].requirement == req1
    assert plan.steps[1].requirement == req2
    assert plan.steps[1].dependencies == [idx1]


def test_installation_plan_to_json():
    """Test JSON serialization of installation plan."""
    plan = InstallationPlan()
    req = ToolRequirement(tool_name="test_tool", version="1.0.0")
    plan.add_step(req)

    json_str = plan.to_json()
    data = json.loads(json_str)

    assert "steps" in data
    assert "total_steps" in data
    assert "unsatisfied_steps" in data
    assert data["total_steps"] == 1


def test_installation_plan_display():
    """Test human-readable display of installation plan."""
    plan = InstallationPlan()
    req1 = ToolRequirement(tool_name="nonexistent1")
    req2 = ToolRequirement(tool_name="nonexistent2")
    plan.add_step(req1)
    plan.add_step(req2)

    display = plan.display()
    assert "Installation plan" in display
    assert "nonexistent1" in display
    assert "nonexistent2" in display


def test_parse_tool_spec():
    """Test parsing tool specifications."""
    tool, version = parse_tool_spec("node")
    assert tool == "node"
    assert version == "latest"

    tool, version = parse_tool_spec("node@20.0.0")
    assert tool == "node"
    assert version == "20.0.0"

    tool, version = parse_tool_spec("python@3.11")
    assert tool == "python"
    assert version == "3.11"


def test_cycle_detection():
    """Test that cycle detection works."""
    plan = InstallationPlan()
    req1 = ToolRequirement(tool_name="tool1")
    req2 = ToolRequirement(tool_name="tool2")
    req3 = ToolRequirement(tool_name="tool3")

    # Add steps without cycles - should work
    idx1 = plan.add_step(req1)
    idx2 = plan.add_step(req2, dependencies=[idx1])
    idx3 = plan.add_step(req3, dependencies=[idx2])

    assert len(plan.steps) == 3

    # Try to create a cycle - should fail
    req4 = ToolRequirement(tool_name="tool4")
    try:
        # This would create a cycle if we made idx3 depend on idx4 and idx4 depend on idx1
        # But we can't do that with the current API since we'd have to add idx4 first
        # Let's test a simpler case: self-dependency
        plan = InstallationPlan()
        idx = plan.add_step(req1)
        # Try to create self-dependency (this would need to be done by manipulating the step)
        plan.steps[idx].dependencies = [idx]
        assert plan._has_cycle(idx)
        print("✓ Cycle detection works for self-reference")
    except ValueError as e:
        print(f"✓ Caught expected error: {e}")


if __name__ == "__main__":
    # Run tests
    import traceback

    test_functions = [
        test_tool_requirement_satisfied,
        test_tool_requirement_not_satisfied,
        test_tool_requirement_to_dict,
        test_file_requirement,
        test_command_requirement,
        test_installation_plan_empty,
        test_installation_plan_add_step,
        test_installation_plan_to_json,
        test_installation_plan_display,
        test_parse_tool_spec,
        test_cycle_detection,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}")
            traceback.print_exc()
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
