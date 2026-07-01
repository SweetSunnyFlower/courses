---
name: markdown-fixer
description: >
  Fix common markdown syntax issues and format code blocks in markdown files.
  Use this skill whenever the user mentions fixing markdown, markdown syntax errors,
  broken tables, broken blockquotes, malformed numbered lists, code block indentation,
  or wants to clean up and format markdown files. Also use it when the user says their
  markdown "looks wrong" or "renders incorrectly" or when code blocks inside markdown
  have lost their indentation. This skill handles: blockquotes with content on the wrong
  line, tables missing separator rows or closing pipes, numbered lists with split
  numbers and content, and code blocks (TSX/JSX/TS/JSON/YAML/Python) missing proper
  indentation.
---

# Markdown Fixer

Fix common markdown syntax issues and format code blocks that have lost their indentation.

## When to use

Use this skill when markdown files have syntax issues that cause incorrect rendering. The most common scenarios are:

1. **Blockquotes**: `>` on its own line with content in the next paragraph — renders as an empty quote followed by plain text
2. **Tables**: Missing the `|---|---|` separator row after the header, or missing closing `|` on rows — renders as plain text instead of a table
3. **Numbered lists**: Number on one line, content on the next paragraph — renders as empty list items
4. **Code blocks**: Code inside ` ``` ` blocks has lost all indentation — very common after content extraction or conversion tools strip whitespace

## How to fix

### Step 1: Run the syntax fixer script

This fixes blockquotes, tables, and numbered lists in one pass:

```bash
python <skill-path>/scripts/fix_markdown_syntax.py <directory-or-file>
```

The script processes each `.md` file and fixes three issue types:

- **Blockquotes**: Pattern `>\n\ncontent` becomes `> content`
- **Tables**: Adds missing `|---|---|` separator rows and closing `|` on each row
- **Numbered lists**: Pattern `1.\n\ncontent` becomes `1. content`

It automatically skips content inside code blocks (between ` ``` ` markers) to avoid modifying code examples.

### Step 2: Format code blocks with prettier

For TSX/JSX/TS/JSON code blocks that have lost indentation, use prettier to reformat them:

```bash
python <skill-path>/scripts/format_code_blocks.py <directory-or-file>
```

This script:
- Extracts all code blocks with language tags `tsx`, `jsx`, `ts`, `tsc`, `json`
- Writes them to temporary files
- Runs `npx prettier --write` on all of them at once (one npx call for efficiency)
- Reads the formatted results back and replaces the original code blocks
- Skips blocks that prettier can't parse (incomplete code, mixed-language content) — these stay unchanged

### Step 3: Fix YAML code blocks

YAML blocks need special handling because prettier can't infer the intended nesting structure from flattened YAML. Two approaches:

**For simple YAML** (config files, front matter): Run the YAML fixer which adds 2-space indentation based on key nesting:

```bash
python <skill-path>/scripts/fix_yaml_blocks.py <directory-or-file>
```

**For complex YAML** (Docker Compose, GitHub Actions): Manual fixing is more reliable. The key rules:
- Top-level keys at column 0: `services:`, `version:`, `jobs:`, etc.
- Nested keys indented 2 spaces under their parent
- List items indented 2 spaces under their parent key, prefixed with `- `
- Fix `key:value` to `key: value` (add space after colon)

### Step 4: Fix Python code blocks

Python blocks (5 or fewer in most projects) are best fixed manually since Python's indentation is semantically meaningful and can't be reliably auto-detected from flattened code. The general approach:

- Function/class bodies: indent 4 spaces
- Nested blocks: add 4 spaces per level
- List/dict literals that span multiple lines: indent contents 4 spaces from the opening bracket

### Step 5: Verify fixes

After running the fixers, check for remaining issues:

```bash
# Check for remaining lone blockquote markers
grep -rn '^>$' <directory>/*.md

# Check for remaining broken numbered lists
grep -rn '^[0-9]\+\.$' <directory>/*.md

# Check for tables missing separators (run the verification in the script)
python <skill-path>/scripts/fix_markdown_syntax.py --check <directory>
```

## Edge cases

- **Nested code blocks in "Prompt" sections**: Some markdown files contain long code blocks that themselves include ` ``` ` markers (e.g., a Prompt showing markdown examples). The simple toggle-based code block detection may get confused by these. If the syntax fixer skips content that should be fixed, check whether the file has an odd number of ` ``` ` markers — this indicates a nested code block issue. In that case, run the fixer with `--no-code-block-skip` to apply fixes everywhere (safe for blockquotes and numbered lists, which rarely appear inside code).

- **Mermaid diagrams**: These use their own syntax and should not be formatted. The scripts skip `mermaid` code blocks.

- **Bash blocks**: Usually contain single-line commands that don't need indentation. The scripts skip `bash` code blocks.

## File organization

```
markdown-fixer/
├── SKILL.md                          (this file)
└── scripts/
    ├── fix_markdown_syntax.py        (blockquotes, tables, numbered lists)
    ├── format_code_blocks.py         (TSX/JSX/TS/JSON via prettier)
    └── fix_yaml_blocks.py            (YAML indentation)
```
