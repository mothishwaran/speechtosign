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
| Videos downloaded locally | 5,388 |
| Manifest phrases | 3,855 (67 of them hand-checked aliases) |
| Skipped: > 30 s | 1,253 |
| Skipped: "(Explanation)" > 8 s | 35 |
| Skipped: Hindi / regional compilations | 3 / 9 |
| Transcoded for the browser (HEVC, MPEG-4 Pt 2, MPEG-2) | 11 |
| Extra spoken words: inflected forms | 624 |
| Extra spoken words: synonyms proposed / approved / rejected | 111 / 82 / 29 |
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
`reviewed synonym` → `fingerspell switch (off)` → `uncovered`

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
| **held-out (20, never tuned on)** | **53.4%** | **65.4%** | **70.6%** |

Spoken (TTS through `/translate`): everyday 74.0% / WER 2.0% · held-out 53.7% / WER 2.4% ·
clips served 76/76 and 68/68 · `eval/dataset_eval*.csv`

## R4 · Latency (same 4.4 s sentence)

| Configuration | ASR |
|---|---|
| Phase 0 laptop, CPU (Review 1) | ~826 ms median |
| CPU, on battery | ~3,100 ms |
| CPU, plugged in | ~1,600 ms |
| GPU fp16 | ~150–250 ms |
| Matching (3,855 phrases) | 0–1 ms |

## F · Failure cases and negative results (pick at least one for the results slides)

| # | What | Evidence |
|---|---|---|
| F1 | Embeddings: Monday→Tuesday, husband→wife at cosine 0.87 | notebook § 14B.4 |
| F2 | Loose WordNet pass: million→billion, decade→ten, acid→zen | `data/synonyms.csv` (review column) |
| F3 | Speaker-leak near miss in the Svarah split | D2 note, Finding 7 |
| F4 | "how" exists only as a 19 s explanation video | `data/trims.csv` |
| F5 | Fine-tuned model writes "Goodnight" as one word | `data/aliases.csv` |
| F6 | 2/16 speakers got slightly worse after fine-tuning | figure 11 |

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
2. Same sentence with the fingerspell switch on.
3. `/health` JSON showing `asr_device: cuda`, 3,855 rows, 0 missing.
4. Debug panel ASR row reading "… ms · whisper-base-en-svarah on CUDA".

## Questions to be ready for (answer them in your own words)

- Why is coverage on the held-out set lower than on the everyday set?
- Why report three coverage figures instead of one?
- Why was WordNet chosen over sentence embeddings, given the plan said embeddings?
- How do you know the 13.2 → 11.3 improvement is not noise?
- How did you make sure no test speaker was in training?
- Why are "is" and "the" not counted as failures — is that hiding something?
- What would a Deaf user still find wrong with the output?
