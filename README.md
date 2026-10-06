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

Re-run step 3 whenever videos are added. `/health` reports `missing_count: 0`
when the manifest and the files agree.

## Test

```powershell
.\.venv\Scripts\python.exe -m src.matcher           # algorithm + real-manifest self-test
.\.venv\Scripts\python.exe tools\eval_dataset.py    # coverage on eval/test_sentences.txt
.\.venv\Scripts\python.exe tools\eval_dataset.py --tts   # + spoken end-to-end (Windows TTS)
```

## Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 (never `file://` — the mic needs a secure context).

## Structure

See `plans/02_SPEC.md` §1.
