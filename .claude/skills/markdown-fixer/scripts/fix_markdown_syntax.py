#!/usr/bin/env python3
"""Fix common markdown syntax issues: blockquotes, tables, numbered lists.

Usage:
    python fix_markdown_syntax.py <directory-or-file>
    python fix_markdown_syntax.py --check <directory-or-file>   (verify only, no changes)

Fixes:
1. Blockquote: >\n\ncontent  ->  > content
2. Table: add missing separator row + ensure closing | on each row
3. Numbered list: N.\n\ncontent  ->  N. content
"""

import os
import re
import glob
import sys


def split_code_blocks(text):
    """Split text into segments, marking which are inside code blocks."""
    segments = []
    lines = text.split("\n")
    in_code = False
    current = []

    for line in lines:
        if line.strip().startswith("```"):
            if in_code:
                current.append(line)
                segments.append(("\n".join(current), True))
                current = []
                in_code = False
            else:
                if current:
                    segments.append(("\n".join(current), False))
                    current = []
                current.append(line)
                in_code = True
        else:
            current.append(line)

    if current:
        segments.append(("\n".join(current), in_code))

    return segments


def fix_blockquotes(text):
    """Fix blockquote pattern: >\n\ncontent -> > content"""
    return re.sub(
        r'^>\s*\n\n([^\n]+)\n',
        r'> \1\n',
        text,
        flags=re.MULTILINE,
    )


def fix_numbered_lists(text):
    """Fix numbered list pattern: N.\n\ncontent -> N. content"""
    return re.sub(
        r'^(\d+)\.\s*\n\n([^\n]+)\n',
        r'\1. \2\n',
        text,
        flags=re.MULTILINE,
    )


def fix_tables(text):
    """Fix markdown tables: add separator row and ensure closing |."""
    lines = text.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if (line.lstrip().startswith("|")
                and i + 1 < len(lines)
                and lines[i + 1].lstrip().startswith("|")):
            table_rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                table_rows.append(lines[i])
                i += 1

            parsed_rows = []
            for row in table_rows:
                stripped = row.strip()
                if not stripped.endswith("|"):
                    stripped = stripped + " |"
                parsed_rows.append(stripped)

            has_separator = (
                len(parsed_rows) >= 2
                and re.match(r'^\|[\s:|-]+\|$', parsed_rows[1])
                and "-" in parsed_rows[1]
            )

            if has_separator:
                fixed_rows = parsed_rows
            else:
                header = parsed_rows[0]
                col_count = header.count("|") - 1
                if col_count < 1:
                    col_count = 1
                separator = "| " + " | ".join(["---"] * col_count) + " |"
                fixed_rows = [parsed_rows[0], separator] + parsed_rows[1:]

            result.extend(fixed_rows)
        else:
            result.append(line)
            i += 1

    return "\n".join(result)


def process_file(filepath, check_only=False):
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()

    segments = split_code_blocks(original)
    fixed_segments = []
    changes = {"blockquote": 0, "table": 0, "numbered_list": 0}

    for content, is_code in segments:
        if is_code:
            fixed_segments.append(content)
            continue

        before = len(re.findall(r'^>\s*\n\n[^\n]+\n', content, flags=re.MULTILINE))
        content = fix_blockquotes(content)
        changes["blockquote"] += before - len(
            re.findall(r'^>\s*\n\n[^\n]+\n', content, flags=re.MULTILINE))

        before = len(re.findall(r'^\d+\.\s*\n\n[^\n]+\n', content, flags=re.MULTILINE))
        content = fix_numbered_lists(content)
        changes["numbered_list"] += before - len(
            re.findall(r'^\d+\.\s*\n\n[^\n]+\n', content, flags=re.MULTILINE))

        before_table = content
        content = fix_tables(content)
        if content != before_table:
            changes["table"] += 1

        fixed_segments.append(content)

    result = "\n".join(fixed_segments)

    if result != original and not check_only:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(result)
        return changes
    elif check_only:
        total = sum(changes.values())
        return changes if total > 0 else None
    return None


def main():
    check_only = "--check" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        print("Usage: python fix_markdown_syntax.py <directory-or-file> [--check]")
        sys.exit(1)

    target = args[0]
    if os.path.isdir(target):
        files = sorted(glob.glob(os.path.join(target, "*.md")))
    else:
        files = [target]

    total = {"blockquote": 0, "table": 0, "numbered_list": 0}
    modified = 0

    for filepath in files:
        changes = process_file(filepath, check_only)
        if changes:
            modified += 1
            for k in total:
                total[k] += changes[k]
            status = "ISSUES" if check_only else "FIXED"
            print(f"  {status}: {os.path.basename(filepath)}")
        else:
            print(f"  OK: {os.path.basename(filepath)}")

    if check_only:
        print(f"\nIssues found: {sum(total.values())} in {modified} files")
    else:
        print(f"\nFixed {modified} files: {total['blockquote']} blockquotes, "
              f"{total['table']} tables, {total['numbered_list']} numbered lists")


if __name__ == "__main__":
    main()
