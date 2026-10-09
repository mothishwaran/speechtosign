# 14 · Phase 1 evidence pack — numbers and figures only

Same rule as [10_PPT_BLUEPRINT.md](10_PPT_BLUEPRINT.md): **no sentence here is meant for a
slide.** This is the evidence you write *from* — every number has its source file so you can
re-check it before you present and defend it in the viva.

Figures: `eval/figures/` (exported from the executed notebook; re-export by re-running it).

---

## Where each piece of evidence goes (rubric map from file 10)

| Rubric section | Evidence | Source |
|---|---|---|
| Dataset | Table D1, D2 | `data/manifest.csv`, `eval/svarah_speaker_split.csv` |
| Methodology | Table M1 (resolution order) — draw it as a flowchart yourself | `src/matcher.py`, notebook § 14B.2 |
| Results | Tables R1–R4, figures 09–11 | `eval/*.csv`, notebook § 14B |
| Analysis / failure cases | List F | notebook § 14B.4, § 14B Findings |
| Pending work | Table P | notebook § 16 |

---

## D1 · Sign dictionary

| Item | Value |
|---|---|
| Videos in the ISLRTC Drive folder | 15,462 (~250 GB) |
| Videos on this machine | ~5,600 (grows as Drive clips are fetched on demand) |
| Manifest phrases (local) | 4,068 (67 of them hand-checked aliases) |
| More phrases fetchable from Drive on demand | 2,740 (total vocabulary ~6,800) |
| Skipped: > 30 s | 1,256 |
| Skipped: "(Explanation)" > 8 s | 35 |
| Skipped: Hindi / regional compilations | 3 / 9 |
| Transcoded for the browser (HEVC, MPEG-4 Pt 2, MPEG-2) | 12 |
| Extra spoken words: inflected forms | 929 |
| Extra spoken words: synonyms proposed / approved / rejected | 174 / 124 / 50 |
| Related (more general) signs generated / rejected in review / in use | 782 / 203 / 579 |
| Licence handling | videos never committed; manifest + Drive URL committed |

## D2 · Svarah (ASR fine-tuning data) — AI4Bharat, CC BY 4.0

| Split | Speaker groups | Utterances | Hours |
|---|---|---|---|
| train | 84 | 5,342 | 7.61 |
| dev | 15 | 694 | 0.99 |
| test | 16 | 620 | 1.02 |

Split is by speaker (demographic profile). File-name prefixes are **not** speakers: ~2,900
distinct prefixes vs 117 speakers.

## M1 · Word resolution order (for your methodology diagram)

`longest phrase` → `name → fingerspell` → `ISL-omitted` → `inflected form` →
`reviewed synonym` → `related (switch, off)` → `fingerspell (on)` → `uncovered`
(dictionary lookup checks this laptop first, then Google Drive)

## R1 · ASR on 16 unseen Indian-accented speakers (Svarah test split)

| Model | Run 1 | Run 2 |
|---|---|---|
| base.en (stock) | 13.12% | 13.32% |
| fine-tuned (base.en + Svarah) | 11.30% | 11.27% |

Speakers improved 14/16 · paired bootstrap 2000/2000 · worst speaker 53.8% → 41.0% ·
run-to-run spread ±0.2 (temperature fallback) · figures 10, 11 · `eval/asr_svarah_test*.csv`

## R2 · Training

| Item | Value |
|---|---|
| Hardware / time | RTX 4050 Laptop 6 GB / 69 min |
| Steps / epochs / batch / lr | 1,002 / 3 / 16 / 1e-5 |
| Dev WER: step 0 → best (step 600) | 11.84% → 8.95% |
| Exported model size (int8) | 76.4 MB |
| Curve | figure 10 · `eval/train_log_base_en_svarah.csv` |

## R3 · Coverage (text) — figure 09

| Sentence set | All words | ISL-signed | + synonyms |
|---|---|---|---|
| Phase 0 demo sentence (Review 1) | 57.1% | — | — |
| same sentence now | 85.7% | 85.7% | 85.7% |
| everyday (20) | 74.0% | 86.5% | 86.5% |
| **held-out (20, never tuned on)** | **53.9%** | **66.3% local · 67.1% with Drive** | **72.3%** |

Spoken (TTS through `/translate`): everyday 74.0% / WER 2.0% · held-out 55.1% / WER 2.4% ·
clips served 76/76 and 68/68 · `eval/dataset_eval*.csv`

## R4 · Latency (same 4.4 s sentence)

| Configuration | ASR |
|---|---|
| Phase 0 laptop, CPU (Review 1) | ~826 ms median |
| CPU, on battery | ~3,100 ms |
| CPU, plugged in | ~1,600 ms |
| GPU fp16 | ~150–250 ms |
| Matching (3,855 phrases) | 0–1 ms |

## N · New in Phase 1b (7 Oct) — Drive on demand, related signs, live analysis

| Item | Value | Source |
|---|---|---|
| Fresh Drive clip, first use (3.3 MB) | ~5–6 s on this connection; then instant from cache | `src/drive_fetch.py` |
| Same new sign requested 3× at once | 1 download, 2 cache hits (per-file lock) | concurrency test |
| Pitch tracker on synthetic voices 110–330 Hz | within ~1 Hz; white noise → unvoiced | page JS, notebook § 14B.7 |
| Demo recording (`eval/sample.wav`) | median F0 93 Hz, voiced 41 % of frames | figure 12 |
| ZCR voiced vs unvoiced-but-loud | ~2,100 /s vs ~3,100 /s | notebook § 14B.7 |
| Browser test (Chrome, fake mic) | live F0/energy/voicing updated, Drive ☁ chips, related chip, 0 JS errors | — |

## S · Speech processing studies (8 Oct) — figure 13, notebook § 14B.8–14B.9

**Noise robustness** — 200 utterances, 16 unseen speakers, `eval/noise_study.csv`

| Condition | stock | stock + SS | fine-tuned | fine-tuned + SS |
|---|---|---|---|---|
| clean | 13.1% | 13.6% | 11.0% | 11.9% |
| white 10 dB | 28.3% | 28.8% | 25.4% | 24.5% |
| white 5 dB | 44.9% | 43.9% | 34.5% | 36.5% |
| white 0 dB | 67.7% | 73.6% | 55.6% | 59.8% |
| babble 10 dB | 22.2% | 25.8% | 21.1% | 21.3% |
| babble 5 dB | 41.5% | 47.4% | 36.8% | 39.8% |
| babble 0 dB | 88.2% | 95.1% | 92.2% | 88.5% |

SS = spectral subtraction (`src/denoise.py`). SNR gain: white +3.7 to +7.1 dB, babble +0.4 to
+0.9 dB (`eval/noise_study_snr.csv`). WER worse with SS in 15 of 18 conditions → off by default.

**Question detection** — Svarah, 387 questions + 387 statements, `eval/question_study.csv`

| Item | Value |
|---|---|
| Median final pitch movement | yes/no −0.3 st · wh −2.6 st · statements −2.2 st |
| Pitch alone, unseen speakers | balanced accuracy 66.5 % (threshold −0.5 st, set on train speakers) |
| App detector (word order + "?"), unseen | 79/85 questions, 1/70 statements wrongly flagged |
| Same with "?" removed | 61/85 questions, 1/70 statements wrongly flagged |

**ISL order / numbers** — examples (notebook § 14B.9)

| English | Played as |
|---|---|
| Where is the hospital? | HOSPITAL WHERE |
| I go to school tomorrow. | TOMORROW GO SCHOOL |
| I never eat rice. | EAT RICE NEVER |
| I am 25 … Meet me at 7:30. | TWENTY FIVE … MEET SEVEN THIRTY |

## L · Live-testing fixes (9 Oct) — notebook § 14B.10

| Item | Value | Source |
|---|---|---|
| Alphabet clip timing bug | 45 frames stamped as 0.03 s → re-timed to 1.5 s at 30 fps | `tools/split_alphabet.py` |
| Fingerspelling default | 1.5× (≈1 s per letter); 0.75×–2.0× in the page | `frontend/index.html` |
| "cricket match" (2.9 s recording) | fine-tuned "Trickier to match", stock "To the cat match", small.en "Couldn't get the match" | `uploads/` |
| Two-model confidence selection, 620 test utts | 11.25 % vs 11.30 % (fine-tuned alone) — not adopted | `eval/asr_two_model_selection.json` |
| Correction box | typed sentence → same pipeline, logged as "typed" | `/translate_text` |

## F · Failure cases and negative results (pick at least one for the results slides)

| # | What | Evidence |
|---|---|---|
| F1 | Embeddings: Monday→Tuesday, husband→wife at cosine 0.87 | notebook § 14B.4 |
| F2 | Loose WordNet pass: million→billion, decade→ten, acid→zen | `data/synonyms.csv` (review column) |
| F3 | Speaker-leak near miss in the Svarah split | D2 note, Finding 7 |
| F4 | "how" exists only as a 19 s explanation video | `data/trims.csv` |
| F5 | Fine-tuned model writes "Goodnight" as one word | `data/aliases.csv` |
| F6 | 2/16 speakers got slightly worse after fine-tuning | figure 11 |
| F7 | Pitch octave error: 330 Hz voice read as 82.5 Hz before the shortest-peak guard | § 14B.7 |
| F8 | "Related" via siblings would give dog→cat, man↔woman; first-listed WordNet sense gave chess→grass | § 14B.6 |
| F9 | Same Drive clip downloaded twice in one sentence (race) — found by the browser test | `src/api.py` |
| F10 | Spectral subtraction: higher SNR but higher WER in 15/18 conditions | § 14B.8 |
| F11 | Pitch as a question cue: 66.5 % alone; adds false alarms on top of word order | § 14B.9 |
| F12 | "When I was young…" first treated as a wh-question — fixed by requiring a verb or "?" | `src/isl_order.py` |
| F13 | Fingerspelling unreadable: letter clips 0.03 s long (timestamp bug) — found by a user, not by tests | § 14B.10 |
| F14 | Short phrase "cricket match" misheard by all three models; two-model combination no better | § 14B.10 |

## P · Still open

| Item | Needs |
|---|---|
| Real-voice WER for more speakers | people to record via the UI's speaker box |
| ISL word order (SOV, question words last) | rules or ISLTranslate [2] |
| Explanation-video trims, synonym spot-check | someone who knows ISL |
| Comprehensibility | evaluation with Deaf signers |

---

## Screenshots to capture yourself (app running at http://127.0.0.1:8000)

1. Debug panel on a held-out sentence showing all chip colours (sign / similar / omitted / uncovered).
2. A sentence with a word that exists nowhere (e.g. "How about you, my boy?" → H-O-W A-B-O-U-T YOU MY BOY).
3. `/health` JSON showing `asr_device: cuda`, 3,855 rows, 0 missing.
4. Debug panel ASR row reading "… ms · whisper-base-en-svarah on CUDA".
5. **Live analysis panel while speaking** — waveform, spectrogram and pitch track (speak slowly,
   rising intonation shows nicely as a question).
6. A sentence with a **new word fetched from Drive** (☁ chip, "Drive fetch: 1 sign(s) in … ms").
7. A sentence with a **related** chip, e.g. "My puppy sleeps in the cottage."
8. **ISL gloss line** for a question, e.g. "Where is the hospital?" → HOSPITAL WHERE + badge.
9. Debug rows **Question** and **Final pitch movement** for a yes/no question.

## Questions to be ready for (answer them in your own words)

- Why is coverage on the held-out set lower than on the everyday set?
- Why report three coverage figures instead of one?
- Why was WordNet chosen over sentence embeddings, given the plan said embeddings?
- How do you know the 13.2 → 11.3 improvement is not noise?
- How did you make sure no test speaker was in training?
- Why are "is" and "the" not counted as failures — is that hiding something?
- What would a Deaf user still find wrong with the output?
- How does autocorrelation find pitch, and why can it be off by an octave?
- Why is the zero-crossing rate higher for unvoiced sounds?
- Why not stream the videos straight from Google Drive into the browser?
- Why "more general" related signs and not "similar" ones like man for boy?
- Spectral subtraction raised SNR — why did it make Whisper worse?
- Why did fine-tuning on clean accented speech also help in noise?
- Why don't yes/no questions rise in this data, and why decide with word order instead of pitch?
- Why only three ISL order rules and not full subject-object-verb order?
- Why are signs played in spoken order by default, and when would you switch ISL order on?
- Why do very short phrases fail, and how does the correction box handle it honestly?
