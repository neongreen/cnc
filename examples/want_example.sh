#!/bin/bash
# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

# Example usage of the want tool

echo "=== Example 1: Install a single tool ==="
echo "$ want node"
echo ""

echo "=== Example 2: Install multiple tools with specific versions ==="
echo "$ want node@20.0.0 python@3.13 deno"
echo ""

echo "=== Example 3: Show plan without executing ==="
echo "$ want --dry-run node python"
echo ""

echo "=== Example 4: Output plan as JSON ==="
echo "$ want --json node python"
echo ""

echo "=== Example 5: Install without prompts ==="
echo "$ want --yes node python"
echo ""

echo "=== Example 6: Check what would be installed ==="
echo "$ want --json uv watchexec fd dprint"
echo ""
