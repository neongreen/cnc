# Want Tool - Architecture

This document describes the architecture and design of the `want` tool.

## Overview

```
┌─────────────────┐
│   User Input    │
│  want node py   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│      CLI Parser             │
│  • Parse tool specs         │
│  • Parse options (--json)   │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Requirement Objects       │
│  • ToolRequirement(node)    │
│  • ToolRequirement(python)  │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Installation Plan         │
│  • Add steps                │
│  • Track dependencies       │
│  • Validate (cycle check)   │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Satisfaction Check        │
│  • Check which steps        │
│    are already satisfied    │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│    Display Plan             │
│  • Human-readable or JSON   │
│  • Show only unsatisfied    │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   User Confirmation         │
│  • Show summary             │
│  • Ask for approval         │
│  (skip if --yes or --json)  │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│    Execute Plan             │
│  • Run mise commands        │
│  • Show progress            │
│  • Handle errors            │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────┐
│     Success     │
│ ✓ All installed │
└─────────────────┘
```

## Module Structure

```
src/cnc/want/
├── __init__.py          # Package initialization
├── __main__.py          # Entry point for python -m cnc.want
├── cli.py               # Command-line interface
├── plan.py              # Installation plan management
├── requirements.py      # Requirement types and base classes
└── README.md            # Module documentation
```

## Core Components

### 1. Requirements System

All requirements inherit from `Requirement` base class:

```python
class Requirement(ABC):
    def is_satisfied(self) -> bool: ...
    def to_dict(self) -> dict: ...
    def get_description(self) -> str: ...
```

Implemented types:
- **ToolRequirement**: Tools installed via mise
- **CommandRequirement**: Shell commands to execute
- **FileRequirement**: Files that must exist

This provides a **unified mechanism** for all requirement types.

### 2. Installation Plan

The `InstallationPlan` class manages:
- **Step ordering**: List of requirements in execution order
- **Dependencies**: DAG of dependencies between steps
- **Validation**: Cycle detection to ensure valid DAG
- **Satisfaction checking**: Filters out already-satisfied steps
- **Display**: Both human-readable and JSON formats

Key features:
```python
plan = InstallationPlan()
idx = plan.add_step(requirement, dependencies=[...])  # Returns step index
plan.get_unsatisfied_steps()  # Returns only unsatisfied steps
plan.display()  # Human-readable format
plan.to_json()  # JSON format
plan.execute()  # Run the plan
```

### 3. Dependency Graph (DAG)

Dependencies are tracked as indices into the steps list:
```python
steps = [
    Step(req=ToolRequirement("node"), deps=[]),      # idx=0
    Step(req=ToolRequirement("pnpm"), deps=[0]),     # idx=1, depends on 0
    Step(req=CommandRequirement(...), deps=[0,1]),   # idx=2, depends on 0,1
]
```

Cycle detection uses DFS to ensure no circular dependencies.

### 4. CLI Interface

The CLI provides:
- **Positional arguments**: Tool specifications (tool[@version])
- **Flags**:
  - `--json`: Output plan as JSON instead of executing
  - `--yes, -y`: Skip confirmation prompt
  - `--dry-run`: Show plan without executing

## Design Principles

### 1. Declarative Over Imperative

Users specify **what** they want, not **how** to get it:
```bash
# Declarative (want)
want node python deno

# vs Imperative (manual)
mise install node
mise install python
mise install deno
```

### 2. Transparency

Always show the plan before execution:
- List all steps that will be performed
- Show dependencies between steps
- Indicate which steps are already satisfied

### 3. Safety

- Require user confirmation by default
- Check if requirements are already satisfied
- Validate dependency graph (no cycles)
- Provide dry-run mode

### 4. Extensibility

Easy to add new requirement types:
1. Create a new class inheriting from `Requirement`
2. Implement `is_satisfied()`, `to_dict()`, `get_description()`
3. Add execution logic to `InstallationPlan.execute()`

### 5. Unified Interface

All requirements use the same interface:
- Same satisfaction checking mechanism
- Same display mechanism
- Same JSON serialization
- Same dependency tracking

This makes it easy to:
- Add new requirement types
- Compose requirements
- Automate with scripts

## Data Flow

### Installation Flow

1. **Parse**: CLI parses arguments → list of tool specs
2. **Create**: Create ToolRequirement objects
3. **Plan**: Add to InstallationPlan with dependencies
4. **Check**: Check which requirements are satisfied
5. **Display**: Show plan (human or JSON)
6. **Confirm**: Ask user for approval (unless --yes or --json)
7. **Execute**: Run installation steps
8. **Report**: Show progress and results

### JSON Output Flow

1. **Parse**: Same as installation flow
2. **Create**: Same as installation flow
3. **Plan**: Same as installation flow
4. **Check**: Same as installation flow
5. **Output**: Call `plan.to_json()` and print
6. **Exit**: No execution, just output

## Extension Points

### Adding New Requirement Types

```python
from cnc.want.requirements import Requirement

class MyRequirement(Requirement):
    def is_satisfied(self) -> bool:
        # Check if requirement is satisfied
        return ...
    
    def to_dict(self) -> dict:
        # Serialize to dict for JSON
        return {"type": "my_requirement", ...}
    
    def get_description(self) -> str:
        # Human-readable description
        return f"My requirement: ..."
```

### Adding New Installation Backends

Currently uses `mise`, but could be extended:
- Python packages via `pip` or `uv`
- Node packages via `npm` or `pnpm`
- System packages via `apt`, `brew`, etc.

## Error Handling

- **Invalid dependencies**: Raises ValueError with helpful message
- **Cycles detected**: Raises ValueError when adding step
- **Missing tools**: Shows error during execution
- **User cancellation**: Exits cleanly with message

## Testing Strategy

Tests cover:
1. Requirement satisfaction checking
2. Plan creation and step ordering
3. Dependency tracking
4. Cycle detection
5. JSON serialization
6. CLI argument parsing
7. Display formatting

All tests run without actual installation (mocked).
