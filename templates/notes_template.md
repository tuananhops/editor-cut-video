# <name> — cut notes (video i/N, batch <batch>)

- Source: `raw/<name>.mp4`, <codec> <W>x<H> <fps> fps, <dur> s, <size>
- Output: `<name>_cut.mp4`: H.264 <W>x<H> <fps> fps, crf 20 medium, AAC 192k, +faststart, **<dur> s**, <n> segments, <size> MB
- Loudness: <I> LUFS, true peak <TP> dBTP. blackdetect: <none/...>.
- Method: faster-whisper medium f32 beam 5 (full + per-island), 10 ms energy map, cuts in silences/dips (+0.05–0.1 s), 15 ms fades, loudnorm −14. Joins checked with assemble_check; output re-transcribed. <fixes made>
- Possible duplicate of: <none / name + reason>

## Segment list (source → output, s)
| # | source | output | content |
|---|---|---|---|
| 1 | 0.80–7.70 | 0.00–6.90 | … |

## Summary
<2–5 sentences: hook, main points, CTA>

## Clean transcript of output (Whisper errors corrected)
<full fluent text; unsure words marked (?)>

Uncertain words: "<whisper heard>" → <best guess> (?), listen at out ~<t> s; …

## Dropped
<src ranges + what was said: false starts, retakes, abandoned sentences (flag any idea that is lost)>

## Cuts to listen for (output times)
- **~<t> (src <a> → <b>) "…end | start…"**: <why risky: mid-sentence splice / takes far apart / tight cut>
