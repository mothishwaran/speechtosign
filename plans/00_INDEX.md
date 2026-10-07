# Review 1 — Plans Index

**Owner:** Mothishwaran (Roll 41, AIE-A) · **Course:** Speech Processing 22AIE450
**Today:** Mon 17 Aug 2026 · **Review:** Wed 19 Aug 2026
**Status:** Phase 0 not started. Working dir contains only `preprojectdocs/`.

---

## Phase 1 status — October 2026

Phase 0 below is the Review 1 record and is unchanged. Since then (details: notebook § 14B,
contracts: `02_SPEC.md` § 11):

| Area | Result |
|---|---|
| Dictionary | ~3,850 phrases from the ISLRTC dictionary (`tools/build_manifest.py`, `tools/drive_sync.py`) |
| ASR | Whisper `base.en` fine-tuned on Svarah: **~13.2% → 11.3% WER** on 16 unseen Indian-accented speakers; GPU ~0.2 s |
| Matching | inflected forms, reviewed synonyms, ISL-omitted words, optional fingerspelling |
| Coverage (held-out sentences) | 53% of all words · **65% of words ISL signs** · 71% with synonyms |
| Still open | real-voice tests with more speakers · ISL word order · trims of explanation videos by an ISL user |

---

## 📓 The project notebook

**[`Speech_to_ISL_Project.ipynb`](../Speech_to_ISL_Project.ipynb)** — the complete project in one
document: problem, 10 verified papers with links, research gaps, full speech-processing theory
with computed figures, every module explained, evaluation, limitations, IEEE references.

Executed end to end — 53 cells, 0 errors, 8 embedded figures. Rebuild with:

```powershell
.\.venv\Scripts\python.exe tools\build_notebook.py
.\.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=speech-isl Speech_to_ISL_Project.ipynb
```

Source of truth is `tools/build_notebook_part{1,2,3}.py` — edit those, not the .ipynb.

---

## How to use this folder

`REVIEW_1_PLAN.md` and the 48-hour sprint doc are the *strategy*. This folder is the *executable version*.

Execution order — hand Sonnet one file at a time:

| # | File | What it is | Who executes |
|---|---|---|---|
| 01 | [01_ENVIRONMENT.md](01_ENVIRONMENT.md) | Verified machine facts + setup commands | **Do this first, before any task file** |
| 02 | [02_SPEC.md](02_SPEC.md) | Frozen contracts — data shapes, function signatures, golden test case | Reference. Never re-derive; read it. |
| 03 | [03_TASK_scaffold_asr.md](03_TASK_scaffold_asr.md) | Block 1 — repo skeleton + `asr.py` | Sonnet |
| 04 | [04_TASK_matcher_fingerspell.md](04_TASK_matcher_fingerspell.md) | Block 2 — `matcher.py` + `fingerspell.py` | Sonnet |
| 05 | [05_TASK_api_frontend.md](05_TASK_api_frontend.md) | Block 3 — `api.py` + `frontend/index.html` | Sonnet |
| 06 | [06_TASK_metrics_hardening.md](06_TASK_metrics_hardening.md) | Block 4 — timing log + 6 runs + fixes | Sonnet |
| 07 | [07_TASK_capture_backup.md](07_TASK_capture_backup.md) | Blocks 5–6 — backup video + deck screenshots | **You. Manual. Non-negotiable.** |
| 08 | [08_DATA_clips.md](08_DATA_clips.md) | Stream A — clips, manifest, teammate brief | You + teammate, parallel to 03–06 |
| 09 | [09_LITERATURE_REVIEW.md](09_LITERATURE_REVIEW.md) | Tomorrow AM — 10-paper worksheet | You (I can verify citations, see below) |
| 10 | [10_PPT_BLUEPRINT.md](10_PPT_BLUEPRINT.md) | Tomorrow PM — rubric map + discussion agenda | **You + me together. No bullets written here by design.** |
| 11 | [11_VIVA_PREP.md](11_VIVA_PREP.md) | Tomorrow PM — question bank + answer skeletons | You, out loud |
| 12 | [12_RISKS.md](12_RISKS.md) | Risk register, drop order, hard rules | Read at every decision point |
| 13 | [13_RUNBOOK_blocks_4_5_6.md](13_RUNBOOK_blocks_4_5_6.md) | **Runbook for the manual blocks** — order, exact steps, shot list | **You. ~50 min. Start here now.** |
| 14 | [14_PHASE1_EVIDENCE.md](14_PHASE1_EVIDENCE.md) | **Phase 1 evidence pack** — every number with its source, figures, failure cases, viva questions. No slide text, by design. | You, for the next review's slides |

---

## Three environment findings that change the plan

Detail in [01_ENVIRONMENT.md](01_ENVIRONMENT.md). Summary:

1. **Your default Python is 3.13.5, not 3.11.** `faster-whisper`/`ctranslate2` wheel support on 3.13 is not something to gamble a 48-hour sprint on. Python 3.11 *is* installed. **Build the venv on 3.11 explicitly.** This is the single most likely way to lose two hours today.
2. **`ffmpeg` is not on PATH.** Consequence: audio is converted to 16 kHz mono WAV **in the browser** with the Web Audio API before upload, so the server never needs a decoder. This is not a workaround — it is the more robust design, and it removes an entire failure class. Clip *trimming* still wants ffmpeg; that lives in Stream A and has its own fallback.
3. **`git` and `node` are present; the project dir is not a git repo yet.** `git init` is part of Block 1.

---

## Deviations from the sprint brief — deliberate, each justified

| Sprint brief said | Plan says | Why |
|---|---|---|
| Python 3.11 | Python 3.11 **via `py -V:3.11`**, not the default interpreter | Default is 3.13; the brief's assumption doesn't hold on this machine |
| MediaRecorder at 16 kHz mono | Record at device rate, **resample to 16 kHz mono WAV client-side** | `sampleRate: 16000` in `getUserMedia` is routinely ignored by Chrome. Resampling is the only way to actually get 16 kHz. |
| One endpoint | `/translate` + a 6-line `/log_frame` + `/health` | t2 (first frame rendered) happens on the client *after* the response. There is no honest way to log true end-to-end latency with one endpoint. `/health` is free and is a deck screenshot. |
| Frontend as a separate file to open | FastAPI **serves** `frontend/` and `data/` | `file://` breaks `getUserMedia` in Chrome. Serving from `http://127.0.0.1:8000` kills the CORS problem and the mic-permission problem at once. |
| No `tests/` | No `tests/` — assertions live in `if __name__ == "__main__"` inside `matcher.py` | Satisfies the Block 2 proof at zero extra files, and the passing output is a deck screenshot |

---

## Ratio rule — the thing that decides your marks

**~30% of remaining time on the demo. ~70% on LR + PPT + viva.**
Demo feeds 2 marks. The deck and viva are the other ~90%. If you are still coding tomorrow afternoon, you have already lost more than the demo could ever win.

**Hard stop: stop coding tonight, in whatever state it is in.**

---

## One thing I can do that the original plan assumed impossible

`REVIEW_1_PLAN.md` §6 says *"I cannot search the web from here."* In this session I **can** — I have web search and fetch. So the 10 citations in [09_LITERATURE_REVIEW.md](09_LITERATURE_REVIEW.md) do not have to stay unverified guesses.

**Ask me to verify them and I will return real authors, venues, years and DOIs.** That converts ~1 hour of your Tuesday morning into ~5 minutes and removes the risk of a wrong citation in an IEEE reference list, which is exactly the kind of thing an examiner spot-checks. Do this tonight while the demo bakes, not tomorrow.

---

## Status board — update as you go

| Block | Task | Status |
|---|---|---|
| 0 | Teammate messaged for clips | ☐ **you send this** |
| 1 | venv + scaffold + `asr.py` proof | ✅ done — Python 3.11 venv, model cached, transcribes correctly offline |
| 2 | `matcher.py` + `fingerspell.py` self-test passing | ✅ done — golden case verified: coverage 0.571, 4 sign/1 spell/2 uncovered |
| 3 | `api.py` + frontend, clips play in sequence | ✅ **done and confirmed live** — 13 real browser runs, e2e 896–1793 ms |
| — | Data: 6 sign clips + 26 alphabet clips | ✅ done — `/health` fully green, 0 missing |
| 4 | `results.csv` has 6 structured runs | ◐ 13 ad-hoc runs logged; **still need the 6 test utterances read in order** |
| 5 | **Backup video recorded** | ☐ **you do this, non-negotiable** |
| 6 | Deck screenshots captured | ☐ **you do this** |
| — | 10 papers, IEEE list built | ☐ ask me to verify citations — I have web search |
| — | PPT drafted (together) | ☐ tomorrow, together |
| — | Viva bank rehearsed **out loud** | ☐ |
| — | Font compliance sweep | ☐ |

**Server is currently running** at `http://127.0.0.1:8000` (started in Block 3 testing). Open it in Chrome to try the real thing.
