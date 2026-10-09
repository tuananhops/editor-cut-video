"""Shared helpers for the editor-cut-video pipeline."""
import json
import os
import subprocess

SR = 16000


def load_wav(path):
    import soundfile as sf
    a, sr = sf.read(path, dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
    if sr != SR:
        raise SystemExit(f"{path}: expected 16 kHz mono wav (got {sr} Hz). Use extract_audio.sh")
    return a


def load_model(name=None, compute_type=None, threads=None):
    """Default = medium / float32 (best quality-speed for Vietnamese).
    Env overrides: ECV_MODEL, ECV_CT, ECV_THREADS."""
    from faster_whisper import WhisperModel
    name = name or os.environ.get("ECV_MODEL", "medium")
    ct = compute_type or os.environ.get("ECV_CT", "float32")
    thr = int(threads or os.environ.get("ECV_THREADS", max(1, min(8, (os.cpu_count() or 4) // 2))))
    return WhisperModel(name, device="cpu", compute_type=ct, cpu_threads=thr)


def tr_kwargs(beam=None, words=True):
    return dict(language=os.environ.get("ECV_LANG", "vi"),
                beam_size=int(beam or os.environ.get("ECV_BEAM", 5)),
                word_timestamps=words,
                condition_on_previous_text=False,
                vad_filter=False)


def seg_to_dict(seg, offset=0.0, **extra):
    d = {"start": round(seg.start + offset, 3), "end": round(seg.end + offset, 3), "text": seg.text.strip()}
    d.update(extra)
    if seg.words:
        d["words"] = [{"start": round(w.start + offset, 3), "end": round(w.end + offset, 3),
                       "word": w.word.strip(), "p": round(w.probability, 3)} for w in seg.words]
    return d


def read_segs(path):
    """segs.txt: one 'start end [comment]' per line (seconds, source time). '#' starts a comment."""
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        p = line.split()
        s, e = float(p[0]), float(p[1])
        if e <= s:
            raise SystemExit(f"bad segment {line!r}: end <= start")
        out.append((s, e))
    return out


def probe(path):
    """Return dict: width, height (display, rotation applied), fps (string), duration."""
    j = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height,r_frame_rate,codec_name:stream_side_data=rotation:stream_tags=rotate:format=duration",
        "-of", "json", path]))
    st = j["streams"][0]
    w, h = st["width"], st["height"]
    rot = 0
    for sd in st.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    rot = rot or int(st.get("tags", {}).get("rotate", 0) or 0)
    if abs(rot) % 180 == 90:
        w, h = h, w
    return {"width": w, "height": h, "fps": st["r_frame_rate"], "codec": st.get("codec_name"),
            "duration": float(j["format"]["duration"])}


def dump_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
