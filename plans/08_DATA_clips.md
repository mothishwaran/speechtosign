# 08 · Stream A — Clips, manifest, teammate brief

**Runs in parallel with Blocks 1–4. Do Block 0 first, then start coding without waiting.**

The code is built against `manifest.csv`, not against the files — so the pipeline can be finished and tested before a single video exists. `/health` will tell you exactly which files are still missing. **Never let clip sourcing block a coding block.**

---

## Block 0 · Message the teammate — 10 minutes, right now

Send verbatim:

> Need 5 ISL clips from the ISLRTC dictionary: **hello, thank you, sorry, please, name**. Plus alphabet clips for these letters only: **M O T H I S W A R N**. Trim each to just the sign, no intro/outro. Export MP4 H.264, 640x480, 25fps, no audio track. Name them lowercase: `hello.mp4`, `thank_you.mp4`, `m.mp4` etc. Also paste me the source URL for each. Need them by tonight.

Then start [03_TASK_scaffold_asr.md](03_TASK_scaffold_asr.md) immediately. **If no reply in an hour, do it yourself — budget 90 minutes.**

15 files total: 5 signs + 10 letters. Not 26 letters — the other 16 are cut from scope.

---

## Where the clips come from

ISLRTC Indian Sign Language Dictionary — ~10,000 terms, all signed by Deaf signers, distributed via the ISLRTC website, YouTube, Google Drive and DIKSHA. There is also a Government of India Open Data catalogue entry.

**Record the exact source URL for every single clip.** It goes into `manifest.csv`. Without it your dataset is not reconstructible and your licensing story falls apart — and both of those are things you are claiming on a slide.

---

## Target format — and what to do when you can't hit it

Ideal: MP4 / H.264 · 640×480 · 25 fps · no audio track · trimmed to the sign only.

**`ffmpeg` is not installed on this machine** (see [01_ENVIRONMENT.md](01_ENVIRONMENT.md)). Three routes:

**Route 1 — teammate delivers trimmed.** Best. Costs you nothing.

**Route 2 — install ffmpeg.** `winget install Gyan.FFmpeg`, open a *new* terminal, verify `ffmpeg -version`. Then per clip:
```powershell
ffmpeg -i raw.mp4 -ss 00:00:01.5 -t 00:00:01.6 -an -vf scale=640:480 -r 25 -c:v libx264 -preset fast data/clips/hello.mp4
```
`-an` strips audio. `-ss`/`-t` are your trim points.

**Route 3 — don't trim.** Download, rename, use as-is. Untrimmed clips have intro/outro padding, so the demo runs longer and looks less polished — but **it works**, and a working untrimmed demo beats a polished one that isn't ready. Take this route the moment trimming threatens the schedule.

Browsers play essentially any MP4/H.264. Uniform resolution is cosmetic; mismatched sizes make the player box resize between clips, which looks scrappy but does not break anything. Fix it with CSS if you care: `object-fit: contain` on a fixed-size container.

---

## `data/manifest.csv`

Exactly the columns in [02_SPEC.md](02_SPEC.md) §2:

```
id,phrase,ngram_len,source_url,local_path,duration_ms,license,notes
hello,hello,1,<url>,data/clips/hello.mp4,1400,ISLRTC,
thank_you,thank you,2,<url>,data/clips/thank_you.mp4,1800,ISLRTC,
sorry,sorry,1,<url>,data/clips/sorry.mp4,1300,ISLRTC,
please,please,1,<url>,data/clips/please.mp4,1500,ISLRTC,
name,name,1,<url>,data/clips/name.mp4,1200,ISLRTC,
```

Write it in Block 1 with `source_url` as `TBD`; fill the URLs when clips land. **`ngram_len` must equal the word count of `phrase`** — the loader asserts this.

Alphabet clips need no manifest row. `fingerspell.py` derives paths by convention: `data/alphabet/{letter}.mp4`.

---

## Licensing — a free mark, do not skip it

- **Never commit video files.** `data/clips/` and `data/alphabet/` are gitignored.
- Commit `manifest.csv` with every source URL, so the dataset is reconstructible without redistributing it.
- ISLTranslate is CC-BY-NC — non-commercial, attribution required. **You are not touching ISLTranslate before Review 1**, but the licence still belongs on the dataset slide because it constrains Phase 1.
- ISLRTC terms of use must be checked before any public hosting. "Academic use" is not the same as "free to redistribute", and knowing that distinction is viva question #17.

State the manifest-not-video approach on a slide. It takes one line and it reads as someone who has thought about data governance rather than someone who downloaded a folder.

---

## Verify before you sleep

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json -Depth 4
```

`missing_clips` empty and `alphabet_present: 10` means Stream A is done.

- [ ] 5 sign clips in `data/clips/`, exact filenames from the manifest
- [ ] 10 alphabet clips in `data/alphabet/`, lowercase single-letter names
- [ ] Every clip opens and plays
- [ ] All 5 `source_url` values filled in
- [ ] `git status` shows **no** video files

---

## If clips do not arrive

Drop in this order — from [12_RISKS.md](12_RISKS.md):

1. **`sorry` and `please`.** Demo with 3 words. Show the manifest and say the pipeline is word-count agnostic — adding a word is one CSV row plus one file. This is true, it is demonstrable on screen, and it lands better than an apology.
2. **Alphabet clips.** Fingerspelling falls back to showing the letter *sequence* in the debug panel with a placeholder in the video box. You lose the visual, you keep the architecture, and you can still explain the fallback path.

**Do not** substitute AI-generated or avatar signing. It is not valid ground truth, the reception literature is explicitly against it, and an examiner who spots it will take the whole project less seriously. If you have no clip, you have no clip — say so.
