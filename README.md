# Editor Cut Video

Công cụ + skill để một bot **cắt thô** video talking-head tiếng Việt quay selfie. Kiểu video này người nói hay vấp, nói lại nhiều lần, bỏ dở câu. Công cụ cắt nó thành một bản đọc liền mạch, rồi bàn giao cho bot hậu kỳ.

- Nhận diện giọng nói: faster-whisper `medium` float32 beam 5, word timestamps.
- Map năng lượng 10 ms để tìm đảo lời nói (islands) và khoảng lặng. Mọi điểm cắt nằm trong khoảng lặng thật.
- Render: ffmpeg cắt chính xác từng frame, fade 15 ms, 1080x1920, loudnorm −14 LUFS. Sau đó tự kiểm tra (ffprobe, blackdetect, ebur128, transcribe lại output).

## Cài nhanh trên bot mới
```bash
sudo apt-get install -y ffmpeg            # nếu chưa có
git clone https://github.com/tuananhops/editor-cut-video.git ~/editor-cut-video
bash ~/editor-cut-video/scripts/setup.sh  # venv ~/.venv-ecv + faster-whisper, numpy, soundfile, gdown + model medium
```
Sau đó:
1. Dán `AGENT_PROMPT.md` vào phần mô tả / system prompt của bot.
2. Nạp `MEMORY.md` vào memory.
3. Thêm `skill/SKILL.md` vào thư viện skill.

**Yêu cầu:**
- Linux, Python ≥ 3.9, ffmpeg/ffprobe
- RAM ~4 GB trống cho `medium` f32 (large-v3 f32 cần nhiều hơn, xem SKILL)
- Khoảng 2 GB đĩa cho model

## Dùng
```bash
export S=~/editor-cut-video/scripts PY=~/.venv-ecv/bin/python
$PY $S/drive_download.py list "<PUBLIC_DRIVE_FOLDER_URL>"           # liệt kê, bỏ qua thư mục "Hoàn thiện"
$PY $S/drive_download.py fetch "<PUBLIC_DRIVE_FOLDER_URL>" -d raw --skip-existing

mkdir -p out/clip1 && cd out/clip1
$S/extract_audio.sh ../../raw/clip1.mp4        # src16k.wav
$PY $S/energy.py map && $PY $S/energy.py islands
$PY $S/transcribe.py full                      # transcript_source.json
$PY $S/transcribe.py islands                   # transcript từng take
$PY $S/transcribe.py ranges 52.3-57.0          # word timings + dips để chọn điểm cắt
# viết segs.txt: mỗi dòng "start end  # ghi chú" (giây, theo source)
$PY $S/assemble_check.py --segs segs.txt       # nghe thử (bằng ASR) từng mối nối
$S/render.sh ../../raw/clip1.mp4 segs.txt clip1_cut.mp4 --transcribe
$PY $S/segtable.py segs.txt transcript_islands.json   # bảng segment cho notes.md
```
Biến môi trường:
- `ECV_MODEL`: mặc định `medium`
- `ECV_CT`: mặc định `float32`
- `ECV_BEAM`: mặc định 5
- `ECV_THREADS`
- `ECV_PRESET`: `veryfast` nếu cần nhanh
- `ECV_CRF`: mặc định 20

## Pipeline
1. Tải video. 2. Trích wav 16k mono. 3. Transcribe full + từng island. 4. Chọn take cuối sạch nhất của mỗi câu, cắt trong khoảng lặng (pad 0.05–0.1 s), bỏ khoảng chết. 5. Kiểm tra mối nối. 6. Render + verify. 7. Viết notes.md (`templates/notes_template.md`). 8. Bàn giao ngay cho bot hậu kỳ, rồi làm video tiếp theo.

Chi tiết đầy đủ: [`skill/SKILL.md`](skill/SKILL.md).

## Cấu trúc
| Đường dẫn | Nội dung |
|---|---|
| `AGENT_PROMPT.md` | mô tả/persona dán cho bot mới |
| `MEMORY.md` | facts/preferences nạp vào memory |
| `skill/SKILL.md` | quy trình đầy đủ |
| `templates/notes_template.md` | mẫu notes.md |
| `scripts/setup.sh` | cài venv + model |
| `scripts/extract_audio.sh` | wav 16k mono |
| `scripts/energy.py` | map dB 10 ms, islands, gaps, view, dips |
| `scripts/transcribe.py` | full / islands / ranges / output (+ `--chunk` khi ít RAM) |
| `scripts/assemble_check.py` | transcribe các mảnh ghép để bắt chữ lọt |
| `scripts/render.py`, `scripts/render.sh` | render từ segs.txt + verify |
| `scripts/segtable.py` | bảng segment cho notes |
| `scripts/drive_download.py` | tải từ Google Drive public (gdown) |
| `scripts/ct2_f16_to_f32.py` | (tuỳ chọn) đổi model CT2 fp16 → fp32 |
| `examples/segs.sample.txt` | ví dụ segs.txt |

---

## English
**Editor Cut Video** helps a bot rough-cut raw Vietnamese selfie talking-head videos. The speaker usually has false starts, retakes and stutters. The bot keeps only the final clean take of each sentence, so the result reads as one fluent script. Every cut sits in a real silence. Pacing is tightened, then the clip is rendered at 1080x1920 with −14 LUFS loudness and verified. Each cut is handed to a post-production bot right away.

**Install:**
1. Run `git clone …`, then `bash scripts/setup.sh` (needs ffmpeg).
2. Paste `AGENT_PROMPT.md` into the bot persona.
3. Seed `MEMORY.md` into memory.
4. Add `skill/SKILL.md` as a skill.

The ASR defaults are faster-whisper `medium`, float32, beam 5, `vi`, with word timestamps. Never use int8 + beam 1 on Vietnamese. See the usage block above and `skill/SKILL.md` for the full workflow.
