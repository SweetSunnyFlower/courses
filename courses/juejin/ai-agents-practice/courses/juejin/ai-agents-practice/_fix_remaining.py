#!/usr/bin/env python3
"""Fix remaining markdown issues in file 10 that weren't caught due to nested code blocks."""
import os
import re

DIR = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(DIR, "10. 第八章：LangGraph 单 Agent 图实战——路由、循环与质量闭环.md")

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

original = content

# Fix blockquote: >\n\ncontent -> > content
content = re.sub(
    r'^>\s*\n\n([^\n]+)\n',
    r'> \1\n',
    content,
    flags=re.MULTILINE,
)

# Fix numbered list: N.\n\ncontent -> N. content
content = re.sub(
    r'^(\d+)\.\s*\n\n([^\n]+)\n',
    r'\1. \2\n',
    content,
    flags=re.MULTILINE,
)

if content != original:
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed remaining issues in file 10")
else:
    print("No changes needed")
