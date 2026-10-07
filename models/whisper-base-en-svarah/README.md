# whisper-base-en-svarah

Whisper `base.en` fully fine-tuned on Indian-accented English, exported to
CTranslate2 (int8 weights) for faster-whisper. `src/asr.py` loads this folder
automatically when it exists; set `SPEECH_ISL_MODEL=base.en` to compare with
the stock model.

## Data
[Svarah](https://huggingface.co/datasets/ai4bharat/Svarah) — AI4Bharat,
CC BY 4.0. 6,656 utterances, 9.6 h, 117 speakers from across India.
Re-split **by speaker** (demographic profile, see `tools/train/data.py`);
the assignment is in `eval/svarah_speaker_split.csv`.

| split | utterances | hours | speakers |
|---|---|---|---|
| train | 5,342 | 7.61 | 84 |
| dev | 694 | 0.99 | 15 |
| test | 620 | 1.02 | 16 |

## Training
`python -m tools.train.train --run base_en_svarah` — 3 epochs, batch 16,
AdamW lr 1e-5, linear warmup 100 steps, fp16 autocast, one RTX 4050 Laptop
GPU (6 GB), 69 min. Best dev checkpoint (step 600 of 1002) exported.
Curve: `eval/train_log_base_en_svarah.csv`.

| step | dev WER |
|---|---|
| 0 (stock) | 11.84% |
| 200 | 9.77% |
| 400 | 9.14% |
| **600** | **8.95%** ← exported |
| 800 | 9.24% |
| 1002 | 8.98% |

## Result on the held-out test speakers
Decoded exactly as the app does (faster-whisper, greedy, `language=en`,
same initial prompt); WER after Whisper's English text normalizer.

| model | test WER, run 1 | test WER, run 2 |
|---|---|---|
| base.en (stock) | 13.12% | 13.32% |
| **whisper-base-en-svarah** | **11.30%** | **11.27%** |

About −14% relative. The two runs differ because faster-whisper's default
temperature fallback re-decodes hard segments with random sampling (the app
decodes the same way); run-to-run spread is ~±0.2 points, an order of magnitude
below the improvement. Run 2's transcriptions are in
`eval/asr_svarah_test_hyps.csv`, from which the notebook (§ 14B.5) recomputes
every figure below.

- 14 of 16 test speakers improved; the two that got worse moved by <1 point.
- Largest gains on the hardest speakers (53.8% → 41.0%, 19.6% → 10.6%).
- Paired bootstrap over utterances: fine-tuned better in 2000/2000 resamples.

## Known behaviour
- Keeps casing and punctuation (Svarah transcripts are cased), so the
  matcher's name fingerspelling still works.
- Tends to drop the final full stop and writes "Goodnight" as one word;
  `data/aliases.csv` maps the one-word greetings to their signs.
- Synthetic US voice (Windows TTS, 20 app sentences): 0 recognition errors
  apart from those two spelling habits.
