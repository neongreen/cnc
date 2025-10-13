# Want Tool - Quick Start Guide

Get started with the `want` tool in 5 minutes.

## Installation

The `want` tool is part of the `cnc` package. Install it with:

```bash
# Using pip (requires Python 3.13+)
pip install -e .

# Or run directly as a module
python -m cnc.want [options] [tools...]
```

## Basic Usage

### Install a single tool

```bash
want node
```

This will:
1. Check if `node` is already installed
2. Show you a plan
3. Ask for confirmation
4. Install using `mise` if you confirm

### Install multiple tools

```bash
want node python deno
```

### Install specific versions

```bash
want node@20.0.0 python@3.13
```

## Common Options

### See what would happen (dry run)

```bash
want --dry-run node python
```

Output:
```
Installation plan (2 step(s)):

  1. Install tool: node
  2. Install tool: python
```

### Get JSON output (for scripts)

```bash
want --json node python
```

Output:
```json
{
  "steps": [
    {
      "requirement": {
        "type": "tool",
        "tool_name": "node",
        "version": "latest",
        "satisfied": false
      },
      "dependencies": []
    },
    ...
  ],
  "total_steps": 2,
  "unsatisfied_steps": 2
}
```

### Skip confirmation prompt

```bash
want --yes node python
```

or

```bash
want -y node python
```

## Examples

### Set up a development environment

```bash
# Install all your dev tools at once
want node@20.0.0 python@3.13 uv pnpm watchexec fd dprint
```

### Use in a script

```bash
#!/bin/bash
set -e

# Install required tools without prompts
want -y node pnpm

# Then use them
pnpm install
pnpm run build
```

### Check before installing

```bash
# First, see what will happen
want --dry-run node python deno

# If looks good, install
want node python deno
```

## What Gets Installed?

The `want` tool uses [mise](https://mise.jdx.dev/) for tool installation.

Supported tools include:
- **Languages**: node, python, ruby, go, rust, etc.
- **Build tools**: make, cmake, ninja, etc.
- **Dev tools**: watchexec, fd, ripgrep, etc.
- **Package managers**: pnpm, yarn, etc.

See [mise registry](https://mise.jdx.dev/registry.html) for full list.

## Comparison with Direct Installation

### Before (manual)
```bash
mise install node@20.0.0
mise install python@3.13
mise install deno
```

- No overview of what will be installed
- No confirmation
- Manual one-by-one installation

### After (want)
```bash
want node@20.0.0 python@3.13 deno
```

- Shows full plan
- Asks for confirmation
- Single command for multiple tools
- Skips already-installed tools

## Common Workflows

### New project setup

```bash
# Clone repo
git clone https://github.com/user/project
cd project

# Install all required tools
want -y node@20 python@3.13 uv pnpm

# Install dependencies
pnpm install
uv sync
```

### Updating tools

```bash
# Install latest versions
want node python
```

### CI/CD Integration

```yaml
# .github/workflows/build.yml
- name: Install tools
  run: |
    want --yes node@20.0.0 python@3.13
```

## Troubleshooting

### "mise not found"

Make sure `mise` is installed and in your PATH:
```bash
curl https://mise.run | sh
```

### Tool already installed

If a tool is already installed, `want` will skip it:
```
✓ 1 requirement(s) already satisfied
```

### Wrong version installed

Specify the exact version you want:
```bash
want node@20.0.0
```

## Next Steps

- Read the [README](../src/cnc/want/README.md) for detailed documentation
- See [examples](.) for more advanced usage
- Check [workflow guide](want_workflow.md) for complete workflows
- Read [architecture](ARCHITECTURE.md) to understand internals

## Getting Help

```bash
want --help
```

For more examples:
```bash
python examples/complete_demo.py
```
