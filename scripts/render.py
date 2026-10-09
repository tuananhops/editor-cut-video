#!/usr/bin/env python3
"""Render a rough cut from segs.txt (source times) and verify it.

usage: render.py SOURCE.mp4 segs.txt [-o NAME_cut.mp4] [--size auto|1080x1920|1920x1080]
                 [--crf 20] [--preset medium|veryfast] [--no-verify] [--transcribe]

- frame-accurate: trim/atrim + concat filter (re-encode), 15 ms afade in/out per segment
- scale (lanczos) to 1080x1920 vertical / 1920x1080 horizontal (auto from display aspect), pad if aspect differs
- keep source fps; libx264 crf 20 preset medium; AAC 192k 48 kHz; +faststart; loudnorm I=-14 TP=-1.5 LRA=11
- verify: ffprobe summary, duration vs segs, blackdetect, ebur128 (I / true peak), out16k.wav;
  --transcribe also writes transcript_output.json (medium f32 beam 5) for the repeat/partial-word check.
Writes the filter graph to fc.txt next to the output.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ecv_common import probe, read_segs  # noqa: E402

FADE = 0.015


def build_graph(segs, W, H):
    n = len(segs)
    L = [f"[0:v:0]scale={W}:{H}:flags=lanczos:force_original_aspect_ratio=decrease,"
         f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p,split={n}" + "".join(f"[s{i}]" for i in range(n)) + ";",
         f"[0:a:0]asplit={n}" + "".join(f"[t{i}]" for i in range(n)) + ";"]
    for i, (s, e) in enumerate(segs):
        d = e - s
        L.append(f"[s{i}]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}];")
        L.append(f"[t{i}]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS,"
                 f"afade=t=in:d={FADE},afade=t=out:st={max(0, d - FADE):.3f}:d={FADE}[a{i}];")
    L.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vo][ac];")
    L.append("[ac]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[ao]")
    return "\n".join(L)


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def verify(out, expect):
    p = probe(out)
    print(f"output: {p['width']}x{p['height']} {p['fps']} fps {p['codec']}, {p['duration']:.2f}s "
          f"(segments sum {expect:.2f}s), {os.path.getsize(out) / 1e6:.1f} MB")
    if abs(p["duration"] - expect) > 0.25:
        print("WARNING: duration differs from segment sum by >0.25 s")
    bd = sh(["ffmpeg", "-hide_banner", "-i", out, "-vf", "blackdetect=d=0.05:pix_th=0.10", "-an", "-f", "null", "-"]).stderr
    nb = bd.count("black_start")
    print(f"blackdetect: {nb} black interval(s)" + ("  <-- CHECK" if nb else ""))
    lo = sh(["ffmpeg", "-hide_banner", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    summ = lo[lo.rfind("Summary:"):]
    I = re.search(r"I:\s+(-?[\d.]+) LUFS", summ)
    P = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ)
    print(f"loudness: {I.group(1) if I else '?'} LUFS integrated, true peak {P.group(1) if P else '?'} dBTP (target -14 / <= -1.5)")
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("segs")
    ap.add_argument("-o", "--out")
    ap.add_argument("--size", default="auto")
    ap.add_argument("--crf", default=os.environ.get("ECV_CRF", "20"))
    ap.add_argument("--preset", default=os.environ.get("ECV_PRESET", "medium"))
    ap.add_argument("--threads", default=os.environ.get("ECV_FF_THREADS", "0"))
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--transcribe", action="store_true")
    a = ap.parse_args()

    segs = read_segs(a.segs)
    src = probe(a.source)
    for s, e in segs:
        if e > src["duration"] + 0.05:
            raise SystemExit(f"segment {s}-{e} beyond source duration {src['duration']:.2f}")
    if a.size == "auto":
        W, H = (1080, 1920) if src["height"] >= src["width"] else (1920, 1080)
    else:
        W, H = map(int, a.size.lower().split("x"))
    name = os.path.splitext(os.path.basename(a.source))[0]
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.segs)), f"{name}_cut.mp4")
    fc = os.path.join(os.path.dirname(os.path.abspath(out)), "fc.txt")
    open(fc, "w").write(build_graph(segs, W, H))
    total = sum(e - s for s, e in segs)
    print(f"source: {src['width']}x{src['height']} {src['fps']} fps {src['codec']}, {src['duration']:.2f}s -> "
          f"{len(segs)} segments, {total:.2f}s, {W}x{H}, crf {a.crf} {a.preset}")
    cmd = ["ffmpeg", "-v", "error", "-stats", "-y", "-i", a.source, "-filter_complex_script", fc,
           "-map", "[vo]", "-map", "[ao]", "-r", src["fps"], "-c:v", "libx264", "-crf", str(a.crf),
           "-preset", a.preset, "-threads", str(a.threads), "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-map_metadata", "-1", "-write_tmcd", "0",
           "-movflags", "+faststart", out]
    if subprocess.run(cmd).returncode != 0:
        raise SystemExit("ffmpeg failed")
    print(f"rendered {out}")
    if a.no_verify:
        return
    verify(out, total)
    wav = os.path.join(os.path.dirname(os.path.abspath(out)), "out16k.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-map", "0:a", "-ac", "1", "-ar", "16000", wav], check=True)
    if a.transcribe:
        here = os.path.dirname(os.path.abspath(__file__))
        tj = os.path.join(os.path.dirname(os.path.abspath(out)), "transcript_output.json")
        subprocess.run([sys.executable, os.path.join(here, "transcribe.py"), "output", "--wav", wav, "--out", tj], check=True)
        print("re-read transcript_output.json: look for repeated words, half words, stray syllables at joins")
    print("RENDER_DONE")


if __name__ == "__main__":
    main()
