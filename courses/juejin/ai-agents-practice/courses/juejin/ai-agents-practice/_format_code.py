#!/usr/bin/env python3
"""Format code blocks in markdown files using prettier.

Extracts TSX/JSX/TS/TSC/JSON code blocks from markdown files,
formats them with prettier, and replaces the original blocks.
"""

import os
import re
import glob
import json
import subprocess
import tempfile
import shutil

DIR = os.path.dirname(os.path.abspath(__file__))

# Map markdown language tags to prettier parsers and file extensions
LANG_MAP = {
    "tsx": ("typescript", ".tsx"),
    "jsx": ("babel", ".jsx"),
    "ts": ("typescript", ".ts"),
    "tsc": ("typescript", ".ts"),
    "json": ("json", ".json"),
}


def parse_code_blocks(filepath):
    """Parse a markdown file and return list of code blocks.

    Returns list of (start_line, end_line, language, content) tuples.
    start_line and end_line are 0-indexed line numbers in the file.
    """
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
                # Closing marker
                content = "".join(lines[block_start + 1:i])
                blocks.append((block_start, i, block_lang, content))
                in_code = False
            else:
                # Opening marker
                block_lang = stripped[3:].strip()  # Remove ``` prefix
                block_start = i
                in_code = True

    return blocks


def main():
    # Find all markdown files
    md_files = sorted(glob.glob(os.path.join(DIR, "*.md")))

    # Collect all code blocks that need formatting
    all_blocks = []  # List of (filepath, start_line, end_line, lang, content)

    for filepath in md_files:
        if filepath.endswith("index.md"):
            continue
        blocks = parse_code_blocks(filepath)
        for start, end, lang, content in blocks:
            if lang in LANG_MAP:
                all_blocks.append((filepath, start, end, lang, content))

    print(f"Found {len(all_blocks)} code blocks to format")

    if not all_blocks:
        print("No code blocks to format")
        return

    # Create temp directory for code blocks
    tmp_dir = tempfile.mkdtemp(prefix="md_format_")

    try:
        # Write each code block to a temp file
        file_map = {}  # temp_file -> (filepath, start, end, lang)
        temp_files = []

        for idx, (filepath, start, end, lang, content) in enumerate(all_blocks):
            parser, ext = LANG_MAP[lang]
            temp_file = os.path.join(tmp_dir, f"block_{idx:05d}{ext}")
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(content)
            file_map[temp_file] = (filepath, start, end, lang)
            temp_files.append(temp_file)

        # Run prettier on all temp files at once
        print("Running prettier...")
        result = subprocess.run(
            ["npx", "--yes", "prettier", "--write", "--no-error-on-unmatched-pattern"] + temp_files,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=tmp_dir,
        )

        if result.returncode != 0:
            print(f"prettier stderr: {result.stderr[:500]}")

        # Read formatted files and replace in markdown
        formatted_count = 0
        failed_count = 0

        # Group blocks by file for replacement
        file_blocks = {}  # filepath -> list of (start, end, lang, formatted_content)

        for temp_file in temp_files:
            filepath, start, end, lang = file_map[temp_file]
            try:
                with open(temp_file, "r", encoding="utf-8") as f:
                    formatted = f.read()

                original_content = None
                for fpath, s, e, l, c in all_blocks:
                    if fpath == filepath and s == start and e == end:
                        original_content = c
                        break

                if formatted != original_content:
                    if filepath not in file_blocks:
                        file_blocks[filepath] = []
                    file_blocks[filepath].append((start, end, lang, formatted))
                    formatted_count += 1
                else:
                    pass  # No changes needed
            except Exception as e:
                failed_count += 1
                print(f"  Failed to read formatted file {temp_file}: {e}")

        # Replace code blocks in each file
        for filepath, blocks in file_blocks.items():
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Sort blocks by start line in reverse order to not mess up indices
            blocks.sort(key=lambda x: x[0], reverse=True)

            for start, end, lang, formatted in blocks:
                # Reconstruct the code block
                new_lines = [f"```{lang}\n"]
                new_lines.append(formatted)
                if not formatted.endswith("\n"):
                    new_lines.append("\n")
                new_lines.append("```\n")

                # Replace lines from start to end (inclusive)
                lines[start:end + 1] = new_lines

            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(lines)

            print(f"  Updated: {os.path.basename(filepath)} ({len(blocks)} blocks)")

        print(f"\nSummary: {formatted_count} blocks formatted, {failed_count} failed")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
