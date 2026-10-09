---
name: editor-cut-video
description: Rough-cut raw Vietnamese talking-head (selfie) videos full of false starts, retakes and stutters into one fluent take (keep the last clean take of each sentence, cut in silent gaps, loudnorm, 1080x1920), then hand each cut off to the post-production editor bot with transcript + notes. Use when asked to "cắt thô", "rough cut", "cắt video", "bỏ đoạn nói vấp/nói lại", or to process a batch of raw clips (local folder or public Google Drive folder) for the editor bot.
---

# Editor Cut Video — rough-cut skill

Scripts: https://github.com/tuananhops/editor-cut-video (`scripts/`). One-time setup:
```bash
git clone https://github.com/tuananhops/editor-cut-video.git ~/editor-cut-video
bash ~/editor-cut-video/scripts/setup.sh            # venv ~/.venv-ecv, faster-whisper, numpy, soundfile, gdown, model 'medium'
export S=~/editor-cut-video/scripts PY=~/.venv-ecv/bin/python
```

## 0. Input
- Raw Vietnamese talking-head selfie videos. Usually iPhone 1728x3072 59.94 fps HEVC or H.264, sometimes 720p. The speaker improvises, so expect many false starts, repeated takes, stutters and mid-sentence restarts.
- Public Google Drive folder: `$PY $S/drive_download.py list <FOLDER_URL>` (gdown `download_folder(skip_download=True)`), then `fetch <FOLDER_URL> -d raw/ --skip-existing` or `id <FILE_ID> -d raw/ -n name.mp4`. Skip subfolders like **"Hoàn thiện"** (= finished). That is the default.
- Before cutting, compare the new list with videos already delivered. **Flag possible duplicates** (same duration/size/opening line) to the user and the editor bot.
- Work dir per video: `out/<name>/` (name = slug of the file name).

## 1. Audio + transcription
```bash
cd out/<name>
$S/extract_audio.sh ../../raw/<name>.mp4            # -> src16k.wav (16 kHz mono)
$PY $S/energy.py map                                # -> db.npy (10 ms dB map)
$PY $S/transcribe.py full                           # -> transcript_source.json
$PY $S/transcribe.py islands                        # -> transcript_islands.json (one pass per speech island = per take)
```
- Best quality/speed: **faster-whisper `medium`, compute_type `float32`, beam_size 5, language `vi`, word_timestamps, condition_on_previous_text off**. These are the script defaults.
- `large-v3` float32 is the most accurate but slow, and it gets OOM-killed on a 16 GB shared box. Workaround: `ECV_THREADS=4 CT2_USE_MKL=0 $PY $S/transcribe.py full --model large-v3 --chunk 22` (20–25 s chunks split at silences).
- **Never use int8 + beam 1 on Vietnamese.** It hallucinates and skips about half the speech.
- On a busy box, use `nice -n 10` and 2–4 threads (`ECV_THREADS`).

## 2. Map takes
- `$PY $S/energy.py islands` lists the speech islands. `gaps` lists the silent gaps (default thr −29 dB, `--thr auto` for odd sources).
- Read `transcript_islands.json` side by side with the full transcript. Group the islands into sentences and their takes.

## 3. Choose segments → `segs.txt`
`segs.txt` has one `start end  # note` line per segment, in source seconds and output order.
- Keep **only the final clean take** of each sentence, so the result reads as **one fluent script**.
- **Never drop meaningful content.** You may splice mid-sentence across takes, or reorder slightly, only to keep content. Drop abandoned sentences but **list them in notes** (and flag any that carry an idea the cut loses).
- Every cut goes in a **real silent gap/dip** with **0.05–0.1 s padding**. Trim dead air for snappy pacing.
- To get exact cut points:
  - `$PY $S/transcribe.py ranges 52.3-57.0 ...` gives word timings and energy dips.
  - `$PY $S/energy.py view 52.8 56.4` shows an ASCII envelope (`' '` < −50, `.` < −40, `:` < −32, `+` < −25, `#` speech).

## 4. Check joins before rendering
```bash
$PY $S/assemble_check.py --segs segs.txt            # every join: last 2.5 s of seg i + first 2.5 s of seg i+1
$PY $S/assemble_check.py "84.50-85.04,85.20-87.00"   # any custom piece list
```
- Fix leaked syllables, such as a stray word from the next take or a clipped last word. Nudge cut points into the gap, or use the cleaner take. Re-check after each fix.

## 5. Render + verify
```bash
$S/render.sh ../../raw/<name>.mp4 segs.txt <name>_cut.mp4 --transcribe   # ECV_PRESET=veryfast if in a hurry
```
- The render does:
  - ffmpeg trim/atrim + concat filter (frame-accurate re-encode), 15 ms afade in/out per segment
  - lanczos scale to 1080x1920 vertical (1920x1080 horizontal), keeping the source fps
  - libx264 crf 20 preset medium, AAC 192k 48 kHz, +faststart, loudnorm I=−14 TP=−1.5 LRA=11
- It verifies:
  - ffprobe; duration must equal the sum of the segments
  - blackdetect: 0 intervals
  - ebur128: about −14 LUFS, true peak ≤ about −1.5
  - output re-transcribed to `transcript_output.json`
- **Read the output transcript.** There must be no repeated words, half words or stray syllables. If there are, fix `segs.txt` and re-render.

## 6. Deliverables (`out/<name>/`)
- `<name>_cut.mp4`, `transcript_source.json`, `transcript_output.json`, `notes.md` (use `templates/notes_template.md`):
  - source info (file, codec, resolution, fps, duration, size) and output info (resolution, fps, duration, segment count, size, loudness, black frames, method)
  - segment table: src in/out → output in/out + text (start with `$PY $S/segtable.py segs.txt transcript_islands.json`, then correct the text)
  - short content summary
  - **clean corrected transcript** with Whisper misspellings fixed; unsure words marked **(?)** with output timestamps
  - dropped takes (src ranges + what was said)
  - **cuts to listen for** with output timestamps and why
- Never invent transcript words. If unsure, write your best guess plus (?) and ask for a listen.

Common Whisper misspellings in this domain:

| Whisper | Correct |
|---|---|
| ANZ | A đến Z |
| Inbook | Inbox |
| lền tảng | nền tảng |
| hiệu nhân | thương hiệu cá nhân |
| A2 / EI | AI |
| Cod | Claude |
| Chatsby | ChatGPT |
| Group / Grub | Grok |
| ủng cáo | quảng cáo |
| AI dần / AIZEN | AI agent |
| fan bếp | fanpage |
| Gia Lô | Zalo |
| len bit | landing page |

## 7. Handoff + batch rules
- **As soon as each video is cut, send it to the post-production editor bot.** Include:
  - path to the cut
  - transcript files and notes.md
  - summary and clean transcript
  - unsure words
  - cuts to listen for
  - duplicate flags
- Then continue straight to the next video. **Process the whole batch continuously** without waiting between videos.
- Speed: aim for about 4–6 min per video, but **quality wins**. Share CPU/RAM politely with other jobs: `nice`, 2–4 threads, one heavy model at a time, never kill other people's processes.
- When account usage reaches **80%**, stop all running tasks and tell the user.
- Cleanup: keep `src16k.wav`/`db.npy` until the editor bot confirms, then they may be deleted. Never commit media to git.
