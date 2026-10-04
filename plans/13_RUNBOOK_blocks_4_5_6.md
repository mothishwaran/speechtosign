# 13 · Runbook — Blocks 4, 5, 6

Everything automatable is built. What remains needs your microphone, your voice and your screen.
**Total time: about 50 minutes.** Work top to bottom, do not reorder.

Server is running at **http://127.0.0.1:8000** — hard-refresh (**Ctrl+Shift+R**) before you start.

---

## Order matters — read this first

Do **Block 5 (the backup recording) before Block 4**, even though the numbers are lower.

Block 4 produces numbers you could regenerate tomorrow. Block 5 needs a *working demo on a working laptop* — a state you may not be able to reproduce. Insure the thing that cannot be recovered, first.

---

## BLOCK 5 · Backup recording — 20 min · non-negotiable

Start `Win + Alt + R` (Xbox Game Bar). One unbroken take.

**What to capture, in order:**
1. Terminal with uvicorn running (`model loaded`, `Application startup complete`)
2. Browser at `http://127.0.0.1:8000`
3. Press Record → say **"Hello, thank you. My name is Mothishwaran."** → press Stop
4. Debug panel filling in — transcript, chips, coverage, timings
5. All clips playing through, fingerspelling included
6. Slow pan across the final debug panel so numbers are readable on pause

**Narrate while recording.** If the mic dies in the room, the video has to carry the demo alone. Beats to hit — your words, not scripted:

- what the system is (constrained retrieval, not translation)
- what you are about to say
- as `hello` / `thank you` / `name` play: these are real ISL clips from the ISLRTC dictionary
- as fingerspelling starts: the name is out-of-vocabulary, so it falls back to fingerspelling
- **call out that Whisper truncated it to "Mothish"** — say it before anyone notices it
- close on coverage and end-to-end latency

**Three copies, tonight:** laptop Desktop as `demo_backup.mp4` · **phone** · cloud with the share link opened and checked. The failure you are insuring against is *the laptop*.

Tomorrow: embed it in the deck as a **file**, not a link. Linked media breaks on a different machine.

---

## BLOCK 4 · The six runs — 15 min

The dropdown under the Record button tags each run automatically, so the CSV is self-labelling and you never have to remember which row was which.

For each of the six: **pick the utterance in the dropdown → Record → read it aloud exactly → Stop → wait for playback to finish.**

```
u1   Hello, thank you. My name is Mothishwaran.
u2   Hello.
u3   Thank you.
u4   Sorry.
u5   Please.
u6   My name is Mothishwaran.
```

Then leave the dropdown on **u1** and run it **5 more times back to back without touching the terminal.** Consecutive stability is what predicts surviving the review room; one good run predicts nothing.

Then:

```powershell
.\.venv\Scripts\python.exe tools\analyze_results.py
```

That prints all three deck tables — latency (median + range), coverage per utterance, and an ASR accuracy check against the expected text. **Screenshot that output.**

`eval/results.csv` was cleared for this; the 17 earlier ad-hoc runs are archived in `eval/results_dev.csv`.

---

## BLOCK 6 · Screenshots — 15 min

Save into `docs/screenshots/` with descriptive names (`debug_panel_coverage.png`, not `Screenshot 2026-08-17.png`).

| # | Shot | Slide |
|---|---|---|
| 1 | Browser mid-playback, sign visible + debug panel | Initial Results |
| 2 | Debug panel close-up — transcript, chips, coverage, 4 timings | **Best single asset** |
| 3 | `analyze_results.py` output (all three tables) | Initial Results |
| 4 | `eval/results.csv` open in Excel | Evidence of measurement |
| 5 | `python -m src.matcher` printing `OK` | Methodology — components tested |
| 6 | `http://127.0.0.1:8000/health` JSON | Methodology |
| 7 | `data/manifest.csv` in Excel, licence column visible | Dataset + licensing |
| 8 | **A failure case** — say `"Queen, give her a hug."` → 0% coverage | Initial Results |
| 9 | `tools/verify.png` — the 26-letter verification sheet | Dataset / methodology |

**Shot 8 is not optional.** A results section showing only successes reads as unexamined. One that shows a failure and explains it reads as engineering — and it hands you the honest answer before an examiner has to dig for it.

Capture with `Win + Shift + S`. Crop tight, no desktop clutter, browser zoom high enough to be legible when projected.

---

## Then stop coding

```powershell
git add -A
git commit -m "Phase 0: speech to ISL retrieval demo with evaluation"
```

Check `git status` shows no video files staged.

---

## Findings already in hand for the limitations slide

Both observed, not predicted — you can say "we measured this":

1. **Whisper truncates "Mothishwaran" to "Mothish"** — 6 for 6, always identically. `initial_prompt` conditioning did not rescue it. The system then fingerspells M-O-T-H-I-S, which is *correct for what the ASR heard*. Clean demonstration of where the real error boundary sits.
2. **`match_ms` is 0–1 ms while `asr_ms` is ~700–900 ms.** End-to-end latency is entirely ASR-bound; retrieval is free at this lexicon size. Knowing your own bottleneck is exactly what "Initial Results & Analysis" is asking for.
3. **The browser WAV encoder never succeeds** — every upload took the raw-container fallback. Resampling to 16 kHz mono still happens, but in `faster_whisper.decode_audio` via PyAV, server-side. **Do not claim browser-side resampling.** `results.csv` now logs which path ran.
