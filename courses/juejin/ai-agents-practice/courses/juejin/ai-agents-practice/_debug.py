#!/usr/bin/env python3
"""Debug code block state transitions."""
import os

DIR = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(DIR, "10. 第八章：LangGraph 单 Agent 图实战——路由、循环与质量闭环.md")

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

in_code = False
count = 0
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if stripped.startswith("```"):
        prev_state = in_code
        count += 1
        if in_code:
            in_code = False
        else:
            in_code = True
        action = "CLOSE" if prev_state else "OPEN"
        print(f"Line {i}: marker #{count}, {action}: {repr(stripped[:40])}")

print(f"\nTotal markers: {count}, final in_code: {in_code}")
