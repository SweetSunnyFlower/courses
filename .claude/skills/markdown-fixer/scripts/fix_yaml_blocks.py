#!/usr/bin/env python3
"""Fix YAML code blocks in markdown files by adding proper indentation.

Usage:
    python fix_yaml_blocks.py <directory-or-file>

Uses a stack-based heuristic to add 2-space indentation to flattened YAML.
Also fixes key:value -> key: value (missing space after colon).

Note: For complex YAML (Docker Compose, GitHub Actions), manual fixing
may be more reliable. This script handles common patterns like:
- Simple key-value nesting (config files)
- Front matter with metadata blocks
- List items under parent keys
"""

import os
import re
import sys
import glob


def fix_yaml_content(content):
    """Fix YAML indentation using a stack-based approach."""
    lines = content.split("\n")
    result = []
    indent_stack = []  # Stack of (key, level) for container keys

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "---":
            result.append(line)
            continue

        # Fix key:value -> key: value
        if ":" in stripped and not stripped.startswith("-"):
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                key = parts[0]
                value = parts[1]
                if (value and not value.startswith(" ")
                        and not value.startswith("\n")
                        and not value.startswith("{")
                        and not value.startswith("[")
                        and not value.startswith(">")
                        and not value.startswith("|")
                        and not value.startswith("&")
                        and not value.startswith("*")
                        and not key.startswith("#")):
                    stripped = f"{key}: {value}"

        if stripped.startswith("- "):
            indent = (indent_stack[-1][1] + 2) if indent_stack else 2
            result.append(" " * indent + stripped)
            continue

        if ":" in stripped:
            key = stripped.split(":")[0].strip()
            has_value = bool(stripped.split(":", 1)[1].strip()) if ":" in stripped else False

            # Check if this key should dedent
            top_level_keys = {
                "services", "version", "volumes", "networks", "llm", "retrieval",
                "tools", "features", "name", "on", "jobs", "dimensions", "gate",
                "metadata", "allowed-tools", "description", "license",
                "compatibility", "module", "author",
            }
            while indent_stack and key in top_level_keys and indent_stack[-1][1] > 0:
                if indent_stack[-1][0] in top_level_keys:
                    indent_stack.pop()
                else:
                    break

            current_indent = (indent_stack[-1][1] + 2) if indent_stack else 0
            result.append(" " * current_indent + stripped)

            if not has_value:
                indent_stack.append((key, current_indent))
        else:
            result.append(stripped)

    return "\n".join(result)


def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_code = False
    lang = ""
    block_start = 0
    changes = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                if lang == "yaml":
                    content = "".join(lines[block_start + 1:i])
                    fixed = fix_yaml_content(content)
                    if fixed != content:
                        changes.append((block_start, i, lang, fixed))
                in_code = False
            else:
                lang = stripped[3:].strip()
                block_start = i
                in_code = True

    if changes:
        changes.sort(key=lambda x: x[0], reverse=True)
        for start, end, lang, fixed in changes:
            new_lines = [f"```{lang}\n", fixed]
            if not fixed.endswith("\n"):
                new_lines.append("\n")
            new_lines.append("```\n")
            lines[start:end + 1] = new_lines

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return len(changes)
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("Usage: python fix_yaml_blocks.py <directory-or-file>")
        sys.exit(1)

    target = args[0]
    if os.path.isdir(target):
        files = sorted(glob.glob(os.path.join(target, "*.md")))
    else:
        files = [target]

    total = 0
    for filepath in files:
        count = process_file(filepath)
        if count > 0:
            print(f"  Fixed {count} YAML blocks in {os.path.basename(filepath)}")
            total += count

    print(f"\nTotal YAML blocks fixed: {total}")


if __name__ == "__main__":
    main()
