# Speech → Indian Sign Language (Phase 0)

Retrieval-based speech-to-ISL demo. Speech → faster-whisper → longest-n-gram
lookup over the ISLRTC dictionary (~3,400 phrases) → sequential playback of
real ISLRTC signer clips, with fingerspelling as a names-only fallback.

Not translation. See `plans/02_SPEC.md` §10 for what this system does not do.

## Setup (once per machine)

```powershell
py -V:3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
```

### Optional: NVIDIA GPU

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-gpu.txt
```

`src/asr.py` uses the GPU automatically when it is available and falls back
to CPU otherwise (force with `$env:SPEECH_ISL_DEVICE = "cpu"` or `"cuda"`).
`/health` shows which one is in use. Measured on an RTX 4050 laptop: ASR
~0.15–0.25 s per sentence on GPU vs ~1.6 s on CPU (plugged in; ~3 s on battery).

## Dataset

Videos are never committed (ISLRTC licensing). `data/manifest.csv` is, and
points at files under `data/_source/isl_dictionary/` (gitignored).

1. Download the [ISL Dictionary Drive folder](https://drive.google.com/drive/folders/1U-Pr4r1-cupgNOOq9NH_uTsQnPSVEKco).
   Drive splits large folders into several ~2 GB zips — extract **all** parts.
2. Extract so the letter folders sit directly in `data/_source/isl_dictionary/`
   (`.../isl_dictionary/A/`, `.../isl_dictionary/Numbers/`, ...).
3. Rebuild the manifest (probes every clip, transcodes the few that browsers
   can't play into `data/_derived/`, applies `data/aliases.csv`):

```powershell
.\.venv\Scripts\python.exe tools\build_manifest.py
```

**Missing words? Fetch single clips from Drive** instead of re-downloading
zips (the full folder is ~15,000 videos / ~250 GB). Needs a free Google API
key with the Drive API enabled (no billing), stored only on your machine:
`setx GOOGLE_API_KEY "AIza..."`, then reopen the terminal.

```powershell
.\.venv\Scripts\python.exe tools\drive_sync.py index                      # list Drive (names only)
.\.venv\Scripts\python.exe tools\drive_sync.py missing --words boy,doctor # preview + size
.\.venv\Scripts\python.exe tools\drive_sync.py download --words boy,doctor
```

Re-run step 3 whenever videos are added.

### Signs fetched from Google Drive on demand (`src/drive_fetch.py`)

`data/drive_manifest.csv` (committed, built by `tools/build_manifest.py` from the
Drive index) lists ~3,000 more dictionary signs that are on the ISLRTC Drive but not
on this machine. When a sentence needs one, the **server** downloads just that clip
(a few seconds; the page says so), checks it is a real sign (≤ 30 s, else rejected and
remembered), transcodes it if needed, and caches it — next time it plays instantly.
The chip shows ☁. Needs `GOOGLE_API_KEY` (see Dataset above); without it those words
are simply uncovered. To pre-download common ones before a demo:
`python tools/drive_sync.py download --words-file <list>`, then rebuild the manifest.

### Live speech analysis (in the page)

While recording, the page shows the waveform, a scrolling spectrogram (FFT 2048,
0–5 kHz), and the pitch track from our own normalised-autocorrelation F0 tracker
(70–400 Hz, octave-error guard), with short-time energy, zero-crossing rate and a
voiced / unvoiced / silent indicator; after stopping, the median F0 and voiced ratio.
It runs entirely in the browser on the microphone stream and never blocks recording.

### Correcting a misheard sentence

Under the transcript, the **"Sign this text"** box takes a typed or corrected sentence and runs
the same signing pipeline (`POST /translate_text`) — useful when speech recognition mishears a
short phrase. Typed runs are logged with note `typed` and excluded from ASR analysis.

### Noise reduction, questions, ISL word order, numbers

- **Noise reduction** (`src/denoise.py`, UI switch, off by default): our own spectral
  subtraction before Whisper. `tools/noise_study.py` (200 unseen-speaker utterances, white and
  babble noise, 20–0 dB): it raises SNR (+4–7 dB on white noise) but slightly *raises* Whisper's
  WER in 15 of 18 conditions, hence off by default; the fine-tuned model is the robust part
  (white 5 dB: 44.9 % → 34.5 % WER vs stock) — see notebook § 14B.8.
- **Question detection** (`src/isl_order.py`): question word first, verb first, or "?".
  The final pitch movement (`src/prosody.py`, semitones) is measured and shown as evidence;
  `tools/question_study.py` showed on Svarah that it is a weak cue for read Indian English,
  so it does not decide (notebook § 14B.9).
- **ISL word order** (UI switch, **off** by default so signs follow the spoken order): time words first, negation last, question
  word last — inside each sentence. The debug panel shows the ISL gloss
  (e.g. *Where is the hospital?* → HOSPITAL WHERE).
- **Numbers**: *25* → TWENTY FIVE, *7:30* → SEVEN THIRTY; digit by digit when a word
  (forty, eighty, ninety) has no sign.

### How words become signs (`src/matcher.py`)

Each word is resolved in this order; the debug panel colours each type:

| type | meaning | example |
|---|---|---|
| sign | exact dictionary phrase (longest n-gram first), or an inflected form of one | "thank you", "books" → book |
| similar | a **reviewed** synonym's sign — counted separately | "physician" → doctor |
| related | no sign or synonym: the closest **more general** sign (WordNet parent), labelled; UI switch, **off** by default | "puppy" → dog, "cottage" → house |
| spell | fingerspelled: a name, or any word with no sign locally or on Drive (UI switch, **on** by default; ~1 s per letter) | "Mothishwaran", "about" |
| omitted | not signed in ISL (articles, forms of *be*, *to*, *of*) | "is", "the" |
| uncovered | no sign available — dropped | |

Reported: `coverage` (signs / all words, the Phase 0 definition),
`content_coverage` (signs / words ISL signs), and the same plus synonyms.

Curated data files (all committed, all human-editable):
- `data/aliases.csv` — words the dictionary files under a combined name (`Hard_Difficult.mp4`).
- `data/synonyms.csv` — generated by `tools/build_synonyms.py` (WordNet, needs `requirements-tools.txt`).
  Word forms are used unless `review=reject`; synonyms only when `review=ok`.
  Reviewed for English meaning; worth a spot-check by an ISL user.
- `data/trims.csv` — cuts of long "(Explanation)" videos down to the sign. Used only
  when `verified_by` is filled in: the sign sits inside continuous signing, so a
  person who knows ISL must pick the times (`tools/contact_sheet.py` shows frames). `/health` reports `missing_count: 0`
when the manifest and the files agree.

## Test

```powershell
.\.venv\Scripts\python.exe -m src.matcher           # algorithm + real-manifest self-test
.\.venv\Scripts\python.exe tools\eval_dataset.py    # coverage on eval/test_sentences.txt
.\.venv\Scripts\python.exe tools\eval_dataset.py --tts   # + spoken end-to-end (Windows TTS)
```

## Fine-tuning Whisper on Indian-accented English (optional, GPU)

Data: [Svarah](https://huggingface.co/datasets/ai4bharat/Svarah) (AI4Bharat,
CC BY 4.0, 9.6 h, 117 speakers), re-split **by speaker** so test voices are
never trained on. The split is recorded in `eval/svarah_speaker_split.csv`.

```powershell
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu126
.\.venv\Scripts\python.exe -m pip install -r requirements-train.txt
.\.venv\Scripts\hf.exe auth login                 # accept the dataset terms on its page first
.\.venv\Scripts\python.exe -m tools.train.data    # download + extract + speaker split
.\.venv\Scripts\python.exe -m tools.train.train --run base_en_svarah
.\.venv\Scripts\python.exe -m tools.train.export  # -> models/whisper-base-en-svarah (int8, committed)
.\.venv\Scripts\python.exe -m tools.train.evaluate base.en models/whisper-base-en-svarah
```

Result (16 held-out speakers): **~13.2% → 11.3% WER** (two runs), 14/16 speakers
improved. Details in `models/whisper-base-en-svarah/README.md`. The app
uses the fine-tuned model automatically; `$env:SPEECH_ISL_MODEL = "base.en"`
switches back to stock.

**Continuing someone else's training:** checkpoints are saved every 200 steps
to `checkpoints/<run>/last/` (gitignored; share the folder via Drive or the
Hugging Face Hub). Put it in the same place and add `--resume` — model,
optimizer, LR schedule, step and RNG state all continue exactly.

## Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 (never `file://` — the mic needs a secure context).

## Structure

See `plans/02_SPEC.md` §1.
