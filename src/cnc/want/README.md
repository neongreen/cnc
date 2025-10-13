# Want - Declarative Dependency Management

`want` is a declarative tool for managing dependencies and tool installations. It creates an installation plan, presents it to the user for approval, and then executes it.

## Features

- **Declarative**: Specify what you want, not how to get it
- **Interactive**: Shows installation plan and asks for confirmation
- **Transparent**: Can output plans as JSON for inspection
- **Dependency-aware**: Supports dependencies between steps (DAG)
- **Safe**: Checks if requirements are already satisfied before attempting installation

## Installation

The `want` command is available when you install the `cnc` package:

```bash
pip install -e .
```

Or run it as a module:

```bash
python -m cnc.want [options] [tools...]
```

## Usage

### Basic Usage

Install a single tool:

```bash
want node
```

Install multiple tools:

```bash
want node python deno
```

Install specific versions:

```bash
want node@20.0.0 python@3.13
```

### Options

- `--json`: Output the installation plan as JSON instead of executing it
- `--yes`, `-y`: Automatically answer yes to all prompts
- `--dry-run`: Show what would be done without actually doing it

### Examples

#### Show installation plan without executing

```bash
want --dry-run node deno
```

#### Output plan as JSON

```bash
want --json node@20.0.0 python@3.13
```

Output:
```json
{
  "steps": [
    {
      "requirement": {
        "type": "tool",
        "tool_name": "node",
        "version": "20.0.0",
        "satisfied": false
      },
      "dependencies": []
    },
    {
      "requirement": {
        "type": "tool",
        "tool_name": "python",
        "version": "3.13",
        "satisfied": false
      },
      "dependencies": []
    }
  ],
  "total_steps": 2,
  "unsatisfied_steps": 2
}
```

#### Install without prompts

```bash
want --yes node deno
```

## How It Works

1. **Parse Requirements**: The tool parses your requested tools/dependencies
2. **Build Plan**: Creates an installation plan with dependencies resolved
3. **Check Satisfaction**: Checks which requirements are already satisfied
4. **Show Plan**: Displays the plan to the user
5. **Confirm**: Asks for user confirmation (unless `--yes` or `--json` is used)
6. **Execute**: Runs the installation steps using `mise`

## Architecture

The `want` tool consists of several modules:

- `requirements.py`: Defines requirement types (ToolRequirement, CommandRequirement, etc.)
- `plan.py`: Handles installation plan creation and execution
- `cli.py`: Command-line interface
- `__main__.py`: Entry point for running as a module

## Requirement Types

### ToolRequirement

Installs a tool using mise:

```python
from cnc.want.requirements import ToolRequirement
from cnc.want.plan import InstallationPlan

plan = InstallationPlan()
plan.add_step(ToolRequirement(tool_name="node", version="latest"))
```

### FileRequirement

Checks if a file exists:

```python
from cnc.want.requirements import FileRequirement

req = FileRequirement(path="/path/to/file")
```

### CommandRequirement

Executes a command:

```python
from cnc.want.requirements import CommandRequirement

req = CommandRequirement(
    command="npm install",
    description="Install npm dependencies"
)
```

## Integration with mise

The tool uses [mise](https://mise.jdx.dev/) for tool installation. Make sure mise is installed and available in your PATH before using `want` to install tools.

## Future Enhancements

- Support for more requirement types (package managers, system packages, etc.)
- Better dependency resolution with cycle detection
- Parallel execution of independent steps
- Rollback on failure
- Configuration file support (e.g., `want.toml`)
