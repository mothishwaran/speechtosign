# Speech → Indian Sign Language (Phase 0)

Retrieval-based speech-to-ISL demo. Speech → faster-whisper → longest-n-gram
lookup over a 5-entry manifest → sequential playback of real ISLRTC signer
clips, with fingerspelling as a names-only fallback.

Not translation. See `plans/02_SPEC.md` §10 for what this system does not do.

## Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 (never `file://` — the mic needs a secure context).

## Structure

See `plans/02_SPEC.md` §1.
