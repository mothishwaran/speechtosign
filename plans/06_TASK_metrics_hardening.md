# 06 · Block 4 — Timing, six runs, hardening

**Budget: ~1 hour. Hard stop.** Contracts: [02_SPEC.md](02_SPEC.md) §6, §9.

This block turns a thing that works once into evidence you can put on a slide. It is also where the temptation to keep coding is strongest. **Set a timer.**

---

## 1 · Verify the CSV is real (10 min)

Run the demo sentence once and open `eval/results.csv`. Confirm:

- header written exactly once
- one `translate` row and one `frame` row sharing a `run_id`
- `coverage` is `0.571`, not `0` and not `1`
- `e2e_ms` is populated on the `frame` row and is larger than `server_ms` (it must be — it includes network, preload and render)

If `e2e_ms` is *smaller* than `server_ms`, `client_t0` is being captured in the wrong place. Fix that before collecting anything, or every number you present is wrong.

---

## 2 · Six runs (20 min)

Read `eval/test_utterances.txt` aloud, one run each. Speak at a normal pace, in the room you will present in if you can.

```
Hello, thank you. My name is Mothishwaran.     <- the demo sentence
Hello.
Thank you.
Sorry.
Please.
My name is Mothishwaran.
```

Then run the demo sentence **5 more times back to back without touching the terminal.** That consecutive-run stability is what actually predicts whether it survives the review room; a single successful run predicts nothing.

Note per run: did the transcript come out right, did all clips play, anything visually wrong.

---

## 3 · The numbers for the deck (10 min)

From `results.csv`, compute by hand — six rows does not warrant pandas:

| Metric | Where it goes |
|---|---|
| median and range of `asr_ms` | Initial Results |
| median `match_ms` | Initial Results — will be ~0–1 ms, and that is a *finding*: retrieval is free, ASR dominates |
| median and range of `e2e_ms` | Initial Results — headline number |
| coverage per utterance | Initial Results, the coverage table |
| transcript errors out of 6 | your honest ASR accuracy statement |

**Report the median with the range, never a lone best-case number.** "1.3 s median, 1.1–1.8 s over 6 runs" is a measurement. "1.1 s" is a claim, and it invites the question you do not want.

That `match_ms ≈ 0` result is worth one sentence on the slide: with a 5-entry lexicon, lookup cost is negligible and end-to-end latency is ASR-bound. It shows you understand where your own bottleneck is, which is exactly what "Initial Results & Analysis" is asking for.

---

## 4 · Fix the top three failures only (20 min)

Rank what actually broke across the six runs. Fix three. Leave the rest.

Likely candidates and their pre-decided fixes:

| Symptom | Fix | Cap |
|---|---|---|
| Name mis-transcribed consistently, same way every time | add `SPELL_ALIASES` per spec §4 | 10 min |
| Name mis-transcribed differently each time | **do not fix.** Say it in the demo — it is why fingerspelling exists | 0 min |
| Fingerspelling drags | `playbackRate = 1.25` on alphabet clips | 5 min |
| Gap or flash between clips | verify preload gate actually awaited; else accept it | 10 min |
| First run slower than the rest | model preload not firing on startup — check the lifespan handler | 10 min |
| Mic not picked up | close other Chrome tabs holding the device | 2 min |

**Anything not on this list, write down and do not fix.** An honest limitations slide is worth more marks than a silent fix, and "here is what broke and here is what I would do about it" is a genuinely strong thing to say in a viva.

---

## 5 · Freeze

```powershell
git add -A
git commit -m "Phase 0: speech to ISL retrieval demo, 5-word lexicon"
```

Confirm `git status` shows no video files staged. Then **stop coding.** Whatever state it is in.

---

## Proof of done

- [ ] `eval/results.csv` holds ≥ 12 rows (6 runs × 2 row types)
- [ ] Demo sentence ran 5 consecutive times with no terminal intervention
- [ ] Median and range noted for `asr_ms` and `e2e_ms`
- [ ] Coverage recorded per utterance
- [ ] Top 3 failures fixed; the rest written down for the limitations slide
- [ ] Committed, no video in the repo

Go straight to [07_TASK_capture_backup.md](07_TASK_capture_backup.md). **Do not skip it — it is the one item on the whole board with no recovery path.**
