#!/usr/bin/env python3
"""Format code blocks in markdown files using prettier.

Usage:
    python format_code_blocks.py <directory-or-file>

Extracts TSX/JSX/TS/TSC/JSON code blocks from markdown files,
formats them with prettier, and replaces the original blocks.
Also detects and formats no-language-tag blocks that contain valid JSON.
"""

import os
import re
import sys
import glob
import json
import subprocess
import tempfile
import shutil

LANG_MAP = {
    "tsx": ("typescript", ".tsx"),
    "jsx": ("babel", ".jsx"),
    "ts": ("typescript", ".ts"),
    "tsc": ("typescript", ".ts"),
    "json": ("json", ".json"),
}


def parse_code_blocks(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    blocks = []
    in_code = False
    block_start = 0
    block_lang = ""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                content = "".join(lines[block_start + 1:i])
                blocks.append((block_start, i, block_lang, content))
                in_code = False
            else:
                block_lang = stripped[3:].strip()
                block_start = i
                in_code = True
    return blocks


def try_format_json(content):
    try:
        data = json.loads(content.strip())
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    except (json.JSONDecodeError, ValueError):
        return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("Usage: python format_code_blocks.py <directory-or-file>")
        sys.exit(1)

    target = args[0]
    if os.path.isdir(target):
        files = sorted(glob.glob(os.path.join(target, "*.md")))
    else:
        files = [target]

    # Collect all code blocks that need prettier formatting
    all_blocks = []
    json_blocks = []  # No-language blocks containing valid JSON

    for filepath in files:
        blocks = parse_code_blocks(filepath)
        for start, end, lang, content in blocks:
            if lang in LANG_MAP:
                all_blocks.append((filepath, start, end, lang, content))
            elif lang == "":
                stripped = content.strip()
                if stripped.startswith("{") or stripped.startswith("["):
                    formatted = try_format_json(content)
                    if formatted is not None:
                        json_blocks.append((filepath, start, end, "", formatted))

    print(f"Found {len(all_blocks)} prettier-formattable blocks")
    print(f"Found {len(json_blocks)} JSON blocks (no language tag)")

    # Fix no-language JSON blocks first
    file_blocks = {}
    json_count = 0
    for filepath, start, end, lang, formatted in json_blocks:
        if filepath not in file_blocks:
            file_blocks[filepath] = []
        file_blocks[filepath].append((start, end, lang, formatted))
        json_count += 1

    if all_blocks:
        tmp_dir = tempfile.mkdtemp(prefix="md_format_")
        try:
            file_map = {}
            temp_files = []
            for idx, (filepath, start, end, lang, content) in enumerate(all_blocks):
                _, ext = LANG_MAP[lang]
                temp_file = os.path.join(tmp_dir, f"block_{idx:05d}{ext}")
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(content)
                file_map[temp_file] = (filepath, start, end, lang)
                temp_files.append(temp_file)

            print("Running prettier...")
            result = subprocess.run(
                ["npx", "--yes", "prettier", "--write",
                 "--no-error-on-unmatched-pattern"] + temp_files,
                capture_output=True, text=True, timeout=300, cwd=tmp_dir,
            )
            if result.returncode != 0 and result.stderr:
                # Prettier reports parse errors per-file but still formats valid ones
                pass

            prettier_count = 0
            for temp_file in temp_files:
                filepath, start, end, lang = file_map[temp_file]
                try:
                    with open(temp_file, "r", encoding="utf-8") as f:
                        formatted = f.read()
                    original = None
                    for fpath, s, e, l, c in all_blocks:
                        if fpath == filepath and s == start and e == end:
                            original = c
                            break
                    if formatted != original:
                        if filepath not in file_blocks:
                            file_blocks[filepath] = []
                        file_blocks[filepath].append((start, end, lang, formatted))
                        prettier_count += 1
                except Exception:
                    pass
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        prettier_count = 0

    # Write changes to files
    total_updated = 0
    for filepath, blocks in file_blocks.items():
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        blocks.sort(key=lambda x: x[0], reverse=True)
        for start, end, lang, formatted in blocks:
            new_lines = [f"```{lang}\n" if lang else "```\n"]
            new_lines.append(formatted)
            if not formatted.endswith("\n"):
                new_lines.append("\n")
            new_lines.append("```\n")
            lines[start:end + 1] = new_lines
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)
        total_updated += 1
        print(f"  Updated: {os.path.basename(filepath)}")

    print(f"\nFormatted: {prettier_count} code blocks (prettier), "
          f"{json_count} JSON blocks, {total_updated} files updated")


if __name__ == "__main__":
    main()
