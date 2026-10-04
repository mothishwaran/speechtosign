# 10 · PPT Blueprint — structure only

**Budget: ~3 hours, Tuesday afternoon. Do this one with me, live.**

---

## Why there are no bullets in this file

Your rubric treats AI-generated sentences as plagiarism. So this file contains **slide budget, rubric mapping, and the question each slide must answer** — and no sentence that could be pasted onto a slide. That is a deliberate constraint, not an oversight.

What I do in the session: walk the rubric with you, ask what you are committing to, push back where a claim outruns the evidence, and check the numbers against `results.csv`.

What you do: **write every word.** In your own phrasing, in your own voice, because you have to defend all of it out loud twenty-four hours later.

**Bring to the session:** `eval/results.csv`, your 8 screenshots, your 10 verified references, and your three gaps. Without those the session cannot produce anything real.

---

## Rubric map — 20 slides maximum

| Rubric item | Marks | Slides | The question this section must answer |
|---|---|---|---|
| Introduction & Background + Literature Review | 2 | 5–6 | What is the problem, why does ISL specifically matter, and what has the field already done? |
| Gaps Identified | 1 | 1–2 | What does the literature *not* do — traceable to your own citations? |
| Objectives + Dataset description | 2 | 3 | What exactly are you committing to build, and on what data, at what licence? |
| Methodology (flow diagram) | 2 | 2–3 | How does audio become video? Show it, do not describe it in prose. |
| Initial Results & Analysis | 2 | 2–3 | What did you measure, what did the numbers say, and what broke? |
| Pending work + Interim Conclusion + IEEE References | 1 | 3 | What is left, what do you honestly claim today, and where is the evidence? |

---

## Slide-by-slide — what each one is *for*

**Title.** Project, your name, roll, class, course code, guide, date.

**1–2 · Problem & motivation.** Why speech→ISL. Who it is for. Ground it in India specifically — this is why you chose ISL over the better-resourced ASL, and that choice needs a reason before the LR arrives.

**3–5 · Literature review.** Grouped by theme per [09_LITERATURE_REVIEW.md](09_LITERATURE_REVIEW.md), as a table: paper · what it establishes · relevance to you. Never a flat list — the grouping is the argument.

**6 · Gaps.** Three, each pointing at a citation from the previous slides. A gap without a reference is an opinion.

**7 · Objectives.** Numbered. **These become promises** — the final review will be marked against them. We will pressure-test each one in the session: can you actually deliver it, and how would you show that you did?

**8–9 · Dataset.** ISLRTC (what you used), ISLTranslate (Phase 1 primary, CC-BY-NC), iSign (expansion). Scale, licence, role for each. Then the manifest-not-video point: source URLs committed, video files never redistributed.

**10–11 · Methodology.** Two diagrams. Pipeline block schematic; matcher logic. See the diagram spec below.

**12 · Implementation.** Component table: what each module does, what it is built on, why. Include the deliberate choices — int8, greedy beam, exact match over embeddings — because each one is a viva question you get to pre-answer.

**13–15 · Initial results.** Screenshots 1–3 from [07_TASK_capture_backup.md](07_TASK_capture_backup.md). Latency table with median **and range**. Coverage table across the 6 utterances. **One failure case, deliberately included.**

**16 · What we will never claim.** Spec §10. Keep this slide from your feasibility deck — it is your strongest.

**17 · Pending work.** Phases 1–4. Also a promise. Also pressure-tested in the session.

**18 · Interim conclusion.** What is genuinely working today, in the smallest honest terms.

**19–20 · References.** IEEE format, numbered by order of first citation in the deck.

---

## The two diagrams

**Diagram 1 — pipeline.** Left to right, one box per stage:

```
Mic → MediaRecorder → 16 kHz mono WAV → faster-whisper base.en (int8, CPU)
    → normalise + tokenise → longest-n-gram lookup over manifest
    → [sign | spell | uncovered] → clip queue → preload → sequential playback
```

Annotate the branch. The three-way split is the whole intellectual content of the system and it is what "Methodology" is asking you to show.

**Diagram 2 — matcher logic.** A flowchart of the greedy loop: position `i` → try 3-gram → 2-gram → 1-gram → hit? emit `sign`, advance by n → miss? capitalised and not sentence-initial? → `spell` : `uncovered` → advance by 1.

This diagram earns marks because it shows a real algorithm rather than a black box, and because it is the thing you can walk an examiner through line by line.

**Font compliance — the cheapest mark on the board.** Times New Roman or Calibri in **every text box, including inside every diagram shape**. It is explicitly in the rubric. If you build diagrams in draw.io or PowerPoint shapes, check every single box — draw.io defaults to Helvetica and will silently cost you the mark. Budget 15 minutes at the end for a sweep.

---

## What I will push you on in the session

Have positions ready:

1. **Objectives** — you are writing promises. What is the final review actually being marked against?
2. **Pending work** — Phase 1 is embeddings + ISLTranslate. Realistic in the remaining weeks, or are you overcommitting on a slide?
3. **The coverage number.** 57.1% on a 5-word lexicon. How do you frame that so it reads as honest measurement rather than a weak result? (There is a good answer. We will find your version of it.)
4. **"Why only five words?"** — near-certain question. Your answer has to be about the pipeline being word-count agnostic and demonstrably so, not an apology.
5. **The gap between what the deck claims and what `results.csv` supports.** I will check these against each other. Every number on a slide must trace to a row in that file.
6. **Whether anything on the deck implies translation.** Watch the verbs — "translate", "convert", "interpret" all overclaim. Spec §10.

---

## Hard rules

- 20 slides maximum
- Single-line bullets — no paragraphs on slides
- Every number traceable to `eval/results.csv`
- Every claim traceable to a citation or a screenshot
- Times New Roman or Calibri everywhere, diagrams included
- Backup video **embedded**, not linked
- **You write every bullet**
