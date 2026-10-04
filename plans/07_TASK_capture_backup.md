# 07 · Blocks 5–6 — Backup video + deck screenshots

**Budget: 40 minutes total. Tonight. Not tomorrow.**
This is the only task in the folder with **no recovery path**. Everything else can be redone tomorrow morning in a pinch. This cannot, because it needs a working demo on a machine that is currently working — and that is a state you may not be able to reproduce.

---

## Block 5 · Backup recording — 20 min, non-negotiable

Record a screen capture of a complete successful run.

**Windows:** `Win + Alt + R` starts Xbox Game Bar recording. Or use OBS if it is already installed — do not install anything new tonight.

Capture, in one unbroken take:

1. The terminal with uvicorn running, model-loaded line visible
2. Browser at `http://127.0.0.1:8000`
3. You pressing record, speaking *"Hello, thank you. My name is Mothishwaran."*, pressing stop
4. The debug panel filling in — transcript, chips, coverage, timings
5. **All clips playing through to the end**, fingerspelling included
6. A slow pan across the final debug panel so the numbers are readable when paused

**Narrate while you record.** A silent screen capture is much weaker as a fallback; if the mic dies in the room, you want a video that can carry the demo on its own.

Do a second take if the first has a stumble. Two takes maximum.

### Where it lives — all three, tonight

- [ ] Laptop, somewhere obvious: `demo_backup.mp4` on the Desktop
- [ ] **Phone** — AirDrop, WhatsApp to yourself, whatever is fastest
- [ ] Cloud — Drive or OneDrive, and **check the shareable link opens**

Three copies because the failure you are insuring against is *the laptop*. A backup that only exists on the machine that failed is not a backup.

### Also: embed it in the deck

Insert the video into the PowerPoint tomorrow **as an embedded file, not a link.** Linked media breaks the moment the deck is opened from a different path or a different machine, which is exactly what happens when you present from a lab computer.

---

## Block 6 · Deck screenshots — 20 min

Take these tonight. You will not want to boot the stack again tomorrow, and tomorrow is for marks, not for code.

| # | Shot | Goes on |
|---|---|---|
| 1 | Browser mid-playback — a sign clip visible, debug panel beside it | Initial Results |
| 2 | Debug panel close-up — transcript, colour-coded chips, coverage, all four timings | Initial Results — **your best single slide asset** |
| 3 | `eval/results.csv` open in Excel, several rows visible | Initial Results — this is your evidence of measurement |
| 4 | `matcher.py` self-test terminal output printing `OK` | Methodology — "components unit-tested" |
| 5 | `GET /health` JSON in the browser | Methodology or backup |
| 6 | `data/manifest.csv` in Excel, all 5 rows and the licence column | Dataset slide — and it makes the licensing point visually |
| 7 | Terminal at startup, model-loaded line | Optional, useful for the CPU/offline claim |
| 8 | A **failure case** — say, a sentence full of uncovered words showing 0% coverage | Initial Results. Deliberately include this. |

Shot 8 matters more than it looks. A results section that shows only successes reads as unexamined. One that shows a failure and explains it reads as engineering, and it hands you the honest answer to "what doesn't work" before the examiner has to ask.

**Capture:** `Win + Shift + S` (Snipping Tool). Save everything into `docs/screenshots/` with descriptive filenames — `debug_panel_coverage.png`, not `Screenshot 2026-08-17 234501.png`. Tomorrow-you has to find these fast.

Crop tight, no desktop clutter, no other tabs, and check the browser zoom is high enough that the text is readable when the slide is projected.

---

## Proof of done

- [ ] `demo_backup.mp4` plays start to finish with audio
- [ ] It exists on laptop **and** phone **and** cloud, cloud link verified
- [ ] 8 screenshots in `docs/screenshots/`, named descriptively
- [ ] Every screenshot is legible when scaled to slide size
- [ ] **You have stopped coding**

---

## The rule this task exists to enforce

Mic permissions, laptop swaps, a projector that renegotiates the display and kills the audio device, campus wifi, a dead battery, a Windows update at the worst possible moment. More demos die to these than to bad code, and none of them are things you can fix while an examiner watches.

Twenty minutes tonight converts "the demo failed" into "here it is running, and here is why the room's audio stack didn't cooperate." One of those costs marks. The other doesn't.
