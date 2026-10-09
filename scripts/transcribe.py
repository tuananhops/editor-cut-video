#!/usr/bin/env python3
"""faster-whisper transcription with word timestamps (Vietnamese defaults).

Defaults (proven): model medium, float32, beam 5, language vi, word timestamps,
condition_on_previous_text off.  NEVER use int8 + beam 1 on Vietnamese (hallucinates/skips).

modes:
  transcribe.py full     [--wav src16k.wav] [--out transcript_source.json] [--chunk 0]
        whole file; --chunk 20..25 splits at silent gaps near that length (low RAM / large-v3)
  transcribe.py islands  [--wav ...] [--db db.npy] [--thr -29] [--out transcript_islands.json]
        one pass per speech island (0.5 s zero padding) -> clean per-take text + word timings
  transcribe.py ranges   S-E [S-E ...]  [--db db.npy]
        word timings (source time) + energy dips for each range, to pick exact cut points
  transcribe.py output   [--wav out16k.wav] [--out transcript_output.json]   (same as full)

options: --model medium|large-v3|small|<path>  --ct float32|int8  --beam 5  --threads N
env:     ECV_MODEL ECV_CT ECV_BEAM ECV_THREADS ECV_LANG.  For large-v3 on 16 GB shared box:
         ECV_THREADS=4 CT2_USE_MKL=0 transcribe.py full --model large-v3 --chunk 22
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ecv_common import SR, dump_json, load_model, load_wav, seg_to_dict, tr_kwargs  # noqa: E402
import energy  # noqa: E402

PAD = np.zeros(SR // 2, np.float32)  # 0.5 s


def chunk_bounds(db, total, target):
    """Split points near every `target` seconds, snapped to the quietest 10 ms frame within +-5 s."""
    b, t = [0.0], target
    while t < total - 3:
        i0, i1 = int(max(b[-1] + 3, t - 5) * 100), int(min(total, t + 5) * 100)
        cut = (i0 + int(np.argmin(db[i0:i1]))) / 100 if i1 > i0 else t
        b.append(cut)
        t = cut + target
    b.append(total)
    return b


def run(model, audio, offset, kw, log=True, **extra):
    segs, _ = model.transcribe(audio, **kw)
    res = []
    for s in segs:
        d = seg_to_dict(s, offset, **extra)
        res.append(d)
        if log:
            ws = " ".join(f"{w['word']}({w['start']:.2f})" for w in d.get("words", []))
            print(f"[{d['start']:.2f}-{d['end']:.2f}] {d['text']}  || {ws}", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["full", "islands", "ranges", "output"])
    ap.add_argument("ranges", nargs="*")
    ap.add_argument("--wav")
    ap.add_argument("--out")
    ap.add_argument("--db", default="db.npy")
    ap.add_argument("--thr", default="-29")
    ap.add_argument("--chunk", type=float, default=0)
    ap.add_argument("--model")
    ap.add_argument("--ct")
    ap.add_argument("--beam")
    ap.add_argument("--threads")
    a = ap.parse_args()

    wav = a.wav or ("out16k.wav" if a.mode == "output" else "src16k.wav")
    audio = load_wav(wav)
    total = len(audio) / SR
    model = load_model(a.model, a.ct, a.threads)
    kw = tr_kwargs(a.beam)

    if a.mode in ("full", "output"):
        out = a.out or ("transcript_output.json" if a.mode == "output" else "transcript_source.json")
        if a.chunk:
            db = np.load(a.db) if os.path.exists(a.db) else energy.build_map(wav)
            bounds = chunk_bounds(db, total, a.chunk)
        else:
            bounds = [0.0, total]
        res = []
        for s, e in zip(bounds[:-1], bounds[1:]):
            res += run(model, audio[int(s * SR): int(e * SR)], s, kw)
        dump_json(res, out)
        print(f"# saved {out} ({len(res)} segments, {total:.1f}s audio)", file=sys.stderr)

    elif a.mode == "islands":
        out = a.out or "transcript_islands.json"
        db = np.load(a.db) if os.path.exists(a.db) else energy.build_map(wav)
        isl = energy.islands(db, energy.resolve_thr(db, a.thr), 0.12, 0.05)
        res = []
        for x, y in isl:
            clip = np.concatenate([PAD, audio[int(x * SR): int(y * SR)], PAD])
            r = run(model, clip, x - 0.5, kw, log=False, island=[x, y])
            res += r
            print(f"{x:7.2f}-{y:7.2f} {' '.join(z['text'] for z in r)}", flush=True)
        dump_json(res, out)
        print(f"# saved {out} ({len(isl)} islands)", file=sys.stderr)

    elif a.mode == "ranges":
        db = np.load(a.db) if os.path.exists(a.db) else None
        for r in a.ranges:
            s, e = map(float, r.split("-"))
            clip = np.concatenate([PAD, audio[int(s * SR): int(e * SR)], PAD])
            segs = run(model, clip, s - 0.5, kw, log=False)
            ws = " ".join(f"{w['word']}[{w['start']:.2f}-{w['end']:.2f}]" for z in segs for w in z.get("words", []))
            print(r, "|", ws, flush=True)
            if db is not None:
                print("   dips", energy.dips(db, s, e), flush=True)


if __name__ == "__main__":
    main()
