# 03 · Block 1 — Scaffold + ASR

**Budget: ~1 hour.** Prereq: [01_ENVIRONMENT.md](01_ENVIRONMENT.md) setup done. Contracts: [02_SPEC.md](02_SPEC.md) §1, §3.

---

## Deliverables

1. `git init` in the project root
2. `.gitignore`, `requirements.txt`, `README.md` (10 lines is plenty)
3. Directory tree per spec §1, including empty `data/clips/`, `data/alphabet/`, `uploads/`
4. `data/manifest.csv` with 5 rows — `source_url` may be `TBD` until the teammate replies
5. `eval/test_utterances.txt` — the 6 lines from spec §9
6. `src/__init__.py` (empty) and `src/asr.py`
7. `eval/sample.wav` — **your own voice**, saying the demo sentence

## Getting `eval/sample.wav` without ffmpeg

Windows Voice Recorder saves `.m4a`, which is not what you want. Easiest reliable route — record and encode a real 16 kHz mono WAV with Python:

```powershell
.\.venv\Scripts\python.exe -m pip install sounddevice
```

Then a ~15-line script using `sounddevice.rec` at 16000 Hz, 1 channel, and the stdlib `wave` module to write it. Record yourself saying *"Hello, thank you. My name is Mothishwaran."* for 5 seconds.

`sounddevice` is a Block-1-only convenience — it is **not** in the runtime path and does not go in `requirements.txt`. If it gives you any trouble at all, skip it and get the WAV out of the browser in Block 3 instead. Do not burn 20 minutes here.

---

## `src/asr.py`

Per spec §3. Structure:

```python
_model = None                     # module-level singleton

def get_model():                  # lazy load, log load time once
    ...

def transcribe(audio_path: str) -> dict:
    # returns {"text", "language", "asr_ms", "model"}
    ...

if __name__ == "__main__":
    # python -m src.asr <path.wav>  -> pretty-print the dict
```

Config exactly as spec §3: `base.en`, `device="cpu"`, `compute_type="int8"`, `beam_size=1`, `language="en"`, `initial_prompt="Mothishwaran"`.

`asr_ms` wraps the transcribe call only, never the model load — otherwise the first number in your latency table is meaningless.

---

## Proof of done

```powershell
.\.venv\Scripts\python.exe -m src.asr eval\sample.wav
```

Prints something close to:

```
{'text': 'Hello, thank you. My name is Mothishwaran.',
 'language': 'en', 'asr_ms': 850, 'model': 'base.en'}
```

Acceptance:
- [ ] `hello`, `thank you` and `name` are transcribed correctly. **These three are what the demo depends on.**
- [ ] `asr_ms` is a plausible integer (roughly 400–2000 ms on CPU for ~5 s of audio)
- [ ] The model is cached — **re-run with wifi off and confirm it still works**
- [ ] `git status` shows no `.venv/`, no `data/clips/`, no `*.webm`

**The name being mangled is not a failure.** Note exactly what Whisper produced and carry on — spec §4 and §5 already handle it, and it is a genuinely good thing to have observed rather than assumed.

---

## Do not do here

Do not touch the matcher, the API, or the frontend. Do not add VAD. Do not try a larger model because `base.en` misheard your name — the latency cost is real and the fingerspelling fallback exists precisely for this.
