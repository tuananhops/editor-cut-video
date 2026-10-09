#!/usr/bin/env python3
"""Transcribe assembled pieces in isolation to catch leaked syllables / repeats at joins.

usage:
  assemble_check.py "S-E,S-E[,S-E...]" ["S-E,S-E" ...]     # arbitrary piece lists
  assemble_check.py --segs segs.txt [--ctx 2.5]            # every join i|i+1: last ctx s of i + first ctx s of i+1
  assemble_check.py --segs segs.txt --all                  # whole assembly, one pass (like the final render)

Pieces are concatenated with 15 ms fades (like the render) and 0.5 s padding.
Read the text: a stray word/syllable at a join => nudge the cut into the silent gap or use the cleaner take.
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ecv_common import SR, load_model, load_wav, read_segs, tr_kwargs  # noqa: E402

FADE = int(0.015 * SR)


def piece(a, s, e):
    x = a[int(s * SR): int(e * SR)].copy()
    if len(x) > 2 * FADE:
        r = np.linspace(0, 1, FADE, dtype=np.float32)
        x[:FADE] *= r
        x[-FADE:] *= r[::-1]
    return x


def check(model, a, parts, kw):
    pad = np.zeros(SR // 2, np.float32)
    x = np.concatenate([pad] + [piece(a, s, e) for s, e in parts] + [pad])
    r, _ = model.transcribe(x, **kw)
    return " ".join(z.text.strip() for z in r)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("specs", nargs="*")
    ap.add_argument("--wav", default="src16k.wav")
    ap.add_argument("--segs")
    ap.add_argument("--ctx", type=float, default=2.5)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--model")
    ap.add_argument("--ct")
    ap.add_argument("--beam")
    ap.add_argument("--threads")
    a = ap.parse_args()

    audio = load_wav(a.wav)
    model = load_model(a.model, a.ct, a.threads)
    kw = tr_kwargs(a.beam, words=False)
    jobs = []
    for spec in a.specs:
        jobs.append((spec, [tuple(map(float, p.split("-"))) for p in spec.split(",")]))
    if a.segs:
        segs = read_segs(a.segs)
        if a.all:
            jobs.append(("ALL", segs))
        else:
            out_t = 0.0
            for i in range(len(segs) - 1):
                (s1, e1), (s2, e2) = segs[i], segs[i + 1]
                out_t += e1 - s1
                parts = [(max(s1, e1 - a.ctx), e1), (s2, min(e2, s2 + a.ctx))]
                jobs.append((f"join {i + 1}|{i + 2} out~{out_t:.2f}s src {e1:.2f}->{s2:.2f}", parts))
    for label, parts in jobs:
        print(f"{label} | {check(model, audio, parts, kw)}", flush=True)


if __name__ == "__main__":
    main()
