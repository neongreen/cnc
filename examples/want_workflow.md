# Want Tool - Usage Workflow

This document demonstrates the typical workflow when using the `want` tool.

## Basic Workflow

### 1. Check what needs to be installed

First, see what the tool would do without actually doing it:

```bash
$ want --dry-run node python deno

✓ 1 requirement(s) already satisfied

Installation plan (2 step(s)):

  1. Install tool: python
  2. Install tool: deno
```

### 2. Output as JSON for inspection

Get a machine-readable representation of the installation plan:

```bash
$ want --json node python deno

{
  "steps": [
    {
      "requirement": {
        "type": "tool",
        "tool_name": "node",
        "version": "latest",
        "satisfied": true
      },
      "dependencies": []
    },
    {
      "requirement": {
        "type": "tool",
        "tool_name": "python",
        "version": "latest",
        "satisfied": false
      },
      "dependencies": []
    },
    {
      "requirement": {
        "type": "tool",
        "tool_name": "deno",
        "version": "latest",
        "satisfied": false
      },
      "dependencies": []
    }
  ],
  "total_steps": 3,
  "unsatisfied_steps": 2
}
```

### 3. Install with user confirmation

Run the installation and confirm when prompted:

```bash
$ want node python deno

✓ 1 requirement(s) already satisfied

Installation plan (2 step(s)):

  1. Install tool: python
  2. Install tool: deno

This will install 2 item(s) using mise.

Proceed with installation? [y/N] y

[1/2] Install tool: python
  Running: mise install python@latest
  ✓ Step 1 completed

[2/2] Install tool: deno
  Running: mise install deno@latest
  ✓ Step 2 completed

✓ Installation plan completed successfully!
```

### 4. Install without confirmation

Use the `-y` flag to skip the confirmation prompt:

```bash
$ want -y node@20.0.0 python@3.13

Installation plan (2 step(s)):

  1. Install tool: node@20.0.0
  2. Install tool: python@3.13

[1/2] Install tool: node@20.0.0
  Running: mise install node@20.0.0
  ✓ Step 1 completed

[2/2] Install tool: python@3.13
  Running: mise install python@3.13
  ✓ Step 2 completed

✓ Installation plan completed successfully!
```

## Advanced Workflow

### Setting up a development environment

```bash
# Check what needs to be installed for the project
$ want --dry-run uv watchexec fd dprint node@20.0.0

Installation plan (5 step(s)):

  1. Install tool: uv
  2. Install tool: watchexec
  3. Install tool: fd
  4. Install tool: dprint
  5. Install tool: node@20.0.0
```

### Programmatic Usage

You can also use `want` programmatically in Python scripts:

```python
from cnc.want.plan import InstallationPlan
from cnc.want.requirements import ToolRequirement

# Create a plan
plan = InstallationPlan()
plan.add_step(ToolRequirement(tool_name="node", version="20.0.0"))
plan.add_step(ToolRequirement(tool_name="python", version="3.13"))

# Show the plan
print(plan.display())

# Output as JSON
print(plan.to_json())

# Execute (with confirmation in CLI context)
# plan.execute()
```

## Integration with Scripts

You can integrate `want` into your setup scripts:

```bash
#!/bin/bash
set -e

# Install required tools
want -y node@20.0.0 python@3.13 uv pnpm

# Then run your setup commands
pnpm install
uv sync

echo "Development environment ready!"
```

## Comparison with Direct mise Usage

### Before (direct mise)
```bash
# User needs to install tools one by one
$ mise install node@20.0.0
$ mise install python@3.13
$ mise install deno
# No confirmation, no summary, tools installed immediately
```

### After (using want)
```bash
# User specifies what they want
$ want node@20.0.0 python@3.13 deno

# Tool shows plan and asks for confirmation
Installation plan (3 step(s)):
  1. Install tool: node@20.0.0
  2. Install tool: python@3.13
  3. Install tool: deno

This will install 3 item(s) using mise.

Proceed with installation? [y/N] y

# Then executes with progress feedback
```

## Benefits

1. **Declarative**: Specify what you want, not how to get it
2. **Transparent**: See the full plan before execution
3. **Safe**: Confirmation required by default
4. **Smart**: Skips already-satisfied requirements
5. **Flexible**: JSON output for automation, dry-run for testing
6. **Extensible**: Can be extended to support more requirement types
