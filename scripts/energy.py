#!/usr/bin/env python3
"""10 ms dB energy map, speech islands, silent gaps, dips.

usage:
  energy.py map     [--wav src16k.wav] [--out db.npy]
  energy.py islands [--db db.npy] [--thr -29] [--min-gap 0.12] [--min-island 0.05] [--json islands.json]
  energy.py gaps    [--db db.npy] [--thr -29] [--min-gap 0.10]
  energy.py view    T [T ...]       # ASCII envelope +-0.7 s around each time (' ' <-50 '.' <-40 ':' <-32 '+' <-25 '#')
  energy.py dips    S-E [S-E ...]   # local minima below --dip-thr (default -24 dB) inside a range = cut candidates

Frame = 10 ms (hop 160 @16 kHz). Default silence threshold -29 dB worked on iPhone selfie audio;
use --thr auto (noise floor + 12 dB, clamped to [-45,-22]) for noisier/quieter sources.
"""
import argparse
import json
import os
import sys

import numpy as np

HOP = 160
FPS = 100


def build_map(wav):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ecv_common import load_wav
    a = load_wav(wav)
    n = len(a) // HOP
    fr = a[: n * HOP].reshape(n, HOP)
    return 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)


def resolve_thr(db, thr):
    if str(thr) == "auto":
        floor = np.percentile(db, 10)
        return float(np.clip(floor + 12, -45, -22))
    return float(thr)


def silent_runs(db, thr, min_gap):
    s = db < thr
    runs, i, n = [], 0, len(s)
    min_fr = int(round(min_gap * FPS))
    while i < n:
        if s[i]:
            j = i
            while j < n and s[j]:
                j += 1
            if j - i >= min_fr:
                runs.append((i / FPS, j / FPS))
            i = j
        else:
            i += 1
    return runs


def islands(db, thr, min_gap, min_island):
    runs = silent_runs(db, thr, min_gap)
    total = len(db) / FPS
    out, prev = [], 0.0
    for a, b in runs:
        if a - prev > min_island:
            out.append((round(prev, 2), round(a, 2)))
        prev = b
    if total - prev > min_island:
        out.append((round(prev, 2), round(total, 2)))
    return out


def view(db, t, w=0.7):
    i0, i1 = max(0, int((t - w) * FPS)), int((t + w) * FPS)
    s = "".join(" " if d < -50 else "." if d < -40 else ":" if d < -32 else "+" if d < -25 else "#" for d in db[i0:i1])
    return f"{t:7.2f} {i0 / FPS:7.2f}|{s}|"


def dips(db, s, e, thr=-24):
    sd = db[int(s * FPS): int(e * FPS)]
    return [(round(s + i / FPS, 2), int(sd[i])) for i in range(2, len(sd) - 2)
            if sd[i] <= sd[i - 2: i + 3].min() and sd[i] < thr]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["map", "islands", "gaps", "view", "dips"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--wav", default="src16k.wav")
    ap.add_argument("--db", default="db.npy")
    ap.add_argument("--out", default=None)
    ap.add_argument("--thr", default="-29")
    ap.add_argument("--min-gap", type=float, default=None)
    ap.add_argument("--min-island", type=float, default=0.05)
    ap.add_argument("--dip-thr", type=float, default=-24)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    if a.cmd == "map":
        db = build_map(a.wav)
        np.save(a.out or a.db, db)
        print(f"saved {a.out or a.db}: {len(db)} frames ({len(db) / FPS:.2f}s), "
              f"median {np.median(db):.1f} dB, p10 {np.percentile(db, 10):.1f} dB, auto-thr {resolve_thr(db, 'auto'):.1f}")
        return
    db = np.load(a.db)
    thr = resolve_thr(db, a.thr)
    if a.cmd == "islands":
        isl = islands(db, thr, a.min_gap or 0.12, a.min_island)
        for x, y in isl:
            print(f"{x:7.2f}-{y:7.2f}  ({y - x:5.2f}s)")
        print(f"# {len(isl)} islands, thr {thr:.1f} dB", file=sys.stderr)
        if a.json:
            json.dump(isl, open(a.json, "w"))
    elif a.cmd == "gaps":
        print(" ".join(f"{x:.2f}-{y:.2f}" for x, y in silent_runs(db, thr, a.min_gap or 0.10)))
    elif a.cmd == "view":
        for t in a.args:
            print(view(db, float(t)))
    elif a.cmd == "dips":
        for r in a.args:
            s, e = map(float, r.split("-"))
            print(r, "dips", dips(db, s, e, a.dip_thr))


if __name__ == "__main__":
    main()
