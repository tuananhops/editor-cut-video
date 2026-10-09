#!/usr/bin/env python3
"""Markdown segment table for notes.md: src in/out -> output in/out + text (from word timings).

usage: segtable.py segs.txt [transcript_source.json | transcript_islands.json]
Text = words whose midpoint falls inside the segment (raw Whisper text: correct it by hand in notes).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ecv_common import read_segs  # noqa: E402

segs = read_segs(sys.argv[1])
words = []
if len(sys.argv) > 2:
    for s in json.load(open(sys.argv[2], encoding="utf-8")):
        words += s.get("words", [])
    words.sort(key=lambda w: w["start"])
print("| # | source | output | content |\n|---|---|---|---|")
t = 0.0
for i, (s, e) in enumerate(segs, 1):
    txt = " ".join(w["word"] for w in words if s <= (w["start"] + w["end"]) / 2 <= e)
    print(f"| {i} | {s:.2f}–{e:.2f} | {t:.2f}–{t + e - s:.2f} | {txt} |")
    t += e - s
print(f"\nTotal output: {t:.2f}s, {len(segs)} segments")
