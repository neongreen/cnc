# Want Tool - Implementation Summary

This document summarizes the implementation of the `want` tool.

## Problem Statement (from issue)

> `want` should ask before using mise to install something. in fact 'want' should use the same mechanism for satisfying the requirement to "install a tool" as for other requirements. it should decide on an installation plan (which is a DAG probably or maybe just a list of steps) and then present the plan to the user. also add an option to show the plan as json instead of executing it.

## Solution Overview

Created a complete declarative dependency management tool that:
1. ✅ Asks before using mise to install something
2. ✅ Uses unified mechanism for all requirement types
3. ✅ Creates installation plan as DAG
4. ✅ Presents plan to user for approval
5. ✅ Has `--json` option for outputting plan

## Files Created

### Core Implementation (src/cnc/want/)
- `__init__.py` - Package initialization
- `__main__.py` - Entry point for `python -m cnc.want`
- `cli.py` - Command-line interface with argparse
- `plan.py` - Installation plan with DAG and cycle detection
- `requirements.py` - Requirement types with unified interface
- `README.md` - Module documentation

### Tests (tests/)
- `test_want.py` - 11 unit tests covering all functionality
- `test_cli_execution.py` - CLI integration tests
- `test_cli_manual.py` - Manual CLI tests
- `demo_want.py` - Interactive demonstration

### Documentation (examples/)
- `QUICKSTART.md` - Quick start guide for users
- `ARCHITECTURE.md` - Architecture and design documentation
- `want_workflow.md` - Usage workflow examples
- `want_example.sh` - Shell script examples
- `want_programmatic.py` - Programmatic API examples
- `complete_demo.py` - Complete feature demonstration
- `IMPLEMENTATION_SUMMARY.md` - This file

### Configuration
- `pyproject.toml` - Added CLI entry point

## Key Features Implemented

### 1. Unified Requirement Interface

All requirement types implement the same interface:

```python
class Requirement(ABC):
    def is_satisfied(self) -> bool: ...
    def to_dict(self) -> dict: ...
    def get_description(self) -> str: ...
```

Types implemented:
- `ToolRequirement` - Install tools via mise
- `CommandRequirement` - Execute commands
- `FileRequirement` - Check file existence

### 2. Installation Plan (DAG)

The `InstallationPlan` manages:
- Step ordering
- Dependency tracking
- Cycle detection (validates DAG)
- Satisfaction checking
- Display (human & JSON)

### 3. User Confirmation

Before executing, the tool:
1. Shows the complete plan
2. Indicates already-satisfied requirements
3. Asks for user confirmation
4. Can be skipped with `--yes` flag

### 4. JSON Output

Using `--json` flag outputs machine-readable plan:
```json
{
  "steps": [...],
  "total_steps": 3,
  "unsatisfied_steps": 2
}
```

### 5. CLI Interface

Command-line options:
- `want tool1 tool2 ...` - Install tools
- `want tool@version` - Install specific version
- `--json` - Output plan as JSON
- `--yes, -y` - Skip confirmation
- `--dry-run` - Show plan without executing

## Technical Highlights

### Cycle Detection

Implements DFS-based cycle detection:
```python
def _has_cycle(self, start_idx: int) -> bool:
    # Uses DFS with path tracking to detect cycles
    ...
```

### Dependency Resolution

Dependencies tracked as indices:
```python
idx1 = plan.add_step(req1)
idx2 = plan.add_step(req2, dependencies=[idx1])
```

### Smart Display

Only shows unsatisfied requirements in the plan:
```
Installation plan (2 step(s)):
  1. Install tool: python
  2. Install tool: deno
```

## Testing

All tests pass (11 tests):
- ✅ Requirement satisfaction checking
- ✅ Tool requirement serialization
- ✅ File requirement checking
- ✅ Command requirement handling
- ✅ Installation plan creation
- ✅ Step addition with dependencies
- ✅ JSON serialization
- ✅ Plan display formatting
- ✅ Tool spec parsing
- ✅ Cycle detection
- ✅ CLI execution

Run tests:
```bash
python3 tests/test_want.py
python3 tests/test_cli_execution.py
```

## Usage Examples

### Basic usage
```bash
want node python deno
```

### With specific versions
```bash
want node@20.0.0 python@3.13
```

### Dry run
```bash
want --dry-run node python
```

### JSON output
```bash
want --json node python
```

### Without confirmation
```bash
want --yes node python
```

## Design Decisions

### 1. Why a unified interface?

Makes it easy to:
- Add new requirement types
- Compose requirements
- Test each type independently

### 2. Why DAG for dependencies?

- Allows complex dependency relationships
- Prevents circular dependencies
- Enables parallel execution (future)

### 3. Why ask for confirmation?

- Safety: User sees what will happen
- Transparency: No hidden actions
- Control: User can cancel if something looks wrong

### 4. Why JSON output?

- Automation: Can be parsed by scripts
- Integration: Easy to integrate with CI/CD
- Inspection: Can verify plan programmatically

## Future Enhancements

Possible improvements:
- [ ] Support for more requirement types (pip, npm, apt)
- [ ] Parallel execution of independent steps
- [ ] Rollback on failure
- [ ] Configuration file (want.toml)
- [ ] Better version checking
- [ ] Lock file for reproducibility
- [ ] Progress bars for long-running operations

## Comparison with Alternatives

### vs Direct mise
- ✅ Shows plan before execution
- ✅ Asks for confirmation
- ✅ Skips satisfied requirements
- ✅ Single command for multiple tools

### vs Shell scripts
- ✅ Declarative, not imperative
- ✅ Reusable requirement definitions
- ✅ JSON output for automation
- ✅ Built-in cycle detection

### vs Make/Task runners
- ✅ Simpler syntax for tool installation
- ✅ Better user interaction
- ✅ Focused on dependency management

## Conclusion

The `want` tool successfully implements all requirements from the problem statement:

1. ✅ Asks before using mise to install
2. ✅ Unified mechanism for all requirements
3. ✅ Installation plan as DAG
4. ✅ Presents plan to user
5. ✅ JSON output option

The implementation is:
- **Complete**: All requirements met
- **Tested**: 11 tests, all passing
- **Documented**: Extensive docs and examples
- **Extensible**: Easy to add new features
- **User-friendly**: Clear output and interaction

Ready for use!
