# 12 · Risks, cut lines, hard rules

Read this at every decision point. Its whole job is to make the "should I keep going or move on" call *before* you are tired enough to make it badly.

---

## Hard rules — these are not negotiable when the sprint gets tight

1. **Stop coding tonight.** Whatever state it is in. Tomorrow is worth ~90% of the marks and it is not a coding day.
2. **~30% of remaining time on the demo, ~70% on LR + PPT + viva.** If that ratio inverts you lose marks, even if the demo gets better.
3. **The backup recording is non-negotiable.** [07_TASK_capture_backup.md](07_TASK_capture_backup.md). It is the only task with no recovery path.
4. **Never claim more than the system does.** Spec §10. Overclaiming loses more than an honest limitation ever will.
5. **No video files in git.** Ever.
6. **Every number on a slide traces to a row in `eval/results.csv`.**
7. **You write every PPT bullet.** AI-written sentences are plagiarism under your rubric.

---

## Risk register

| Risk | Likelihood | Mitigation | Cut line |
|---|---|---|---|
| venv built on Python 3.13, faster-whisper won't install | **High** | `py -V:3.11 -m venv .venv`; verify `--version` inside the venv | Stop and fix. Everything is downstream. |
| Model download slow or fails | Medium | Forced early by the Block 1 proof; verify offline with wifi off | If the download fails, switch to `tiny.en` (~75 MB) and say so |
| Clips don't arrive from teammate | **High** | Manifest-first design; `/health` shows what's missing | Drop `sorry` + `please`, demo 3 words, show the manifest |
| ffmpeg missing → clips untrimmed | High | Route 3 in [08_DATA_clips.md](08_DATA_clips.md) — use them as-is | Accept longer clips. Cosmetic only. |
| Whisper mangles "Mothishwaran" | **High** | `initial_prompt="Mothishwaran"`; `SPELL_ALIASES` if it fails consistently | **Feature, not bug.** It is exactly why fingerspelling exists — say so in the demo. Cap: 15 min. |
| `file://` frontend → no microphone | Medium | Always `http://127.0.0.1:8000` | Instant fix once you know. This file is where you will remember. |
| Missing `python-multipart` → 500 on upload | Medium | It is in `requirements.txt` | 2-minute fix |
| Stutter or black flash between clips | Medium | Preload gate + A/B double buffer | **Cap 1 hour.** Accept the flicker. Nobody has ever lost a mark to a 100 ms gap. |
| Fingerspelling ~10 s feels like a hang | Medium | Trim clips to 500 ms, or `playbackRate = 1.25` | Narrate over it. Know the number before you present. |
| Mic fails in the review room | Medium | **The backup video** | Non-negotiable. Do it tonight. |
| Laptop swap / projector kills audio device | Medium | Backup video on phone + cloud | Same |
| A citation is wrong in the IEEE list | Medium | Verify every one — **ask me, I have web search** | Do this tonight |
| Fonts wrong inside diagram shapes | **High** | 15-minute sweep at the end | Explicitly in the rubric. Cheapest mark on the board. |
| Running out of time tomorrow | High | Priority order below | — |

---

## Drop order — memorise this

When something has to go, it goes in this order. Do not improvise a different order at 11pm.

1. `sorry` and `please` clips → 3-word demo. Show the manifest, say the pipeline is word-count agnostic, and demonstrate it by pointing at the CSV.
2. The A/B double buffer → single video element with `src` swapping. Visible flicker, works fine.
3. The debug panel's finer details → keep transcript, coverage and end-to-end latency; drop the rest.
4. The 6-utterance eval → report on the demo sentence only, **and say that you did**.
5. Papers 9 and 10 (wav2vec 2.0, Sentence-BERT) → 8-paper LR.
6. The second diagram (matcher logic) → pipeline diagram only.

**Never drop:** the backup recording · the literature review · the viva prep · the avatar-reception paper · the "what we will never claim" slide.

---

## Decision points

**Tonight, 3 hours in.** Is the API returning a plan for `eval/sample.wav`?
No → skip the A/B buffer, take the single-element player, get *something* playing. A rough demo tonight beats a good one tomorrow.

**Tonight, before you sleep.** Is the backup video recorded?
No → **do it now**, even if the demo is imperfect. Record what works. An imperfect recorded demo is infinitely better than a perfect unrecorded one.

**Tomorrow, midday.** Are 10 papers verified and noted?
No → cut to 8, move to the deck. The deck is worth more than papers 9 and 10.

**Tomorrow, 5pm.** Is the deck complete?
No → finish the deck, cut viva prep to the three drill items only. A complete deck with rushed viva prep beats an incomplete deck.

**Tomorrow, 8pm.** Have you run the demo cold on the presentation laptop?
No → **do it now.** This has killed more reviews than any bug.

---

## What actually loses marks — ranked

1. Not presenting (deck incomplete)
2. Overclaiming, then being caught in the viva
3. Weak viva answers on **course fundamentals** — MFCC, WER, Nyquist. Not on your project.
4. Missing or fabricated references
5. Font non-compliance
6. Demo failing live — **fully insured by the backup video**

Note where the demo sits. It is sixth, and it is the only one on the list you can eliminate entirely with twenty minutes of work tonight.

Which is the whole argument of this plan: **the demo is the fun part, not the marks.** Finish it, insure it, and get to the deck.
