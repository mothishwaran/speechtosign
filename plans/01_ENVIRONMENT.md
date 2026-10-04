# 01 · Environment — verified, not assumed

Everything below was checked on this machine on 17 Aug 2026. Do not re-check; do not assume otherwise.

---

## What is actually installed

| Thing | State | Consequence |
|---|---|---|
| Python 3.13.5 | Default on PATH | **Do not use it.** Wheel support for `ctranslate2` on 3.13 is not worth the risk today. |
| Python 3.11 | Installed at `C:\Users\mothi\AppData\Local\Programs\Python\Python311\python.exe`, reachable as `py -V:3.11` | **Use this.** |
| `ffmpeg` | **NOT on PATH** | Audio decode moves to the browser. See below. |
| `git` | `C:\Program Files\Git\cmd\git.exe` | Available; repo not yet initialised |
| `node` | `C:\Program Files\nodejs\node.exe` | Not needed — frontend is plain HTML/JS |
| `faster_whisper`, `fastapi` | Not installed | Block 1 installs them |
| Project dir | `d:\7thsem\speech_processing\project`, contains only `preprojectdocs/` | Clean slate |

---

## Setup — run exactly this, first, before any task file

```powershell
# from d:\7thsem\speech_processing\project
py -V:3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

**Use `.\.venv\Scripts\python.exe` directly throughout.** Do not rely on `Activate.ps1` — PowerShell ExecutionPolicy blocks it on many Windows 11 installs and debugging that is a pure waste of sprint time. If you want activation anyway:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Confirm you are on 3.11 before installing anything:

```powershell
.\.venv\Scripts\python.exe --version   # must print 3.11.x
```

---

## `requirements.txt` — do not pin versions upfront

```
faster-whisper
fastapi
uvicorn[standard]
python-multipart
```

Four lines. Install, then freeze what actually resolved:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip freeze > requirements.lock.txt
```

Commit both. `requirements.txt` is what you meant; `requirements.lock.txt` is what ran and is what makes the demo reproducible on the presentation laptop. Mention the lock file if asked about reproducibility — it is a cheap credibility point.

**`python-multipart` is not optional.** FastAPI raises an obscure runtime error on multipart uploads without it, and it is the classic 20-minutes-lost bug at 11pm.

---

## The ffmpeg situation — read this before writing any audio code

`faster-whisper` decodes audio through PyAV, which bundles its own FFmpeg libraries, so a *system* ffmpeg is not needed for transcription. That is the theory. **Do not build the sprint on it.**

The design instead guarantees the server never has to decode anything exotic:

```
mic → MediaRecorder (device-native rate, WebM/Opus)
    → AudioContext.decodeAudioData()      [browser decodes it]
    → OfflineAudioContext @ 16000 Hz      [browser resamples + downmixes to mono]
    → hand-written PCM16 WAV encoder      [~40 lines of JS]
    → POST as audio/wav
    → faster-whisper reads a plain 16 kHz mono WAV
```

Three things this buys you, all of which are worth stating in the viva:

1. No ffmpeg dependency anywhere in the runtime path.
2. **You actually get 16 kHz.** The `sampleRate: 16000` constraint on `getUserMedia` is advisory and Chrome commonly ignores it, handing you 44.1 or 48 kHz. Resampling in an `OfflineAudioContext` is the only way to be certain — and "why 16 kHz" is viva question #1, so you had better be right that you have it.
3. Uploads shrink, because a 3-second 16 kHz mono PCM16 WAV is ~96 KB.

The server still accepts non-WAV uploads and lets faster-whisper try. That is a fallback, not the plan.

**ffmpeg is still wanted for clip trimming** (Stream A). If you end up needing it: `winget install Gyan.FFmpeg`, new terminal, verify with `ffmpeg -version`. Do this **only** if the teammate does not deliver trimmed clips — see [08_DATA_clips.md](08_DATA_clips.md) for the no-ffmpeg fallback, which is: play the clips untrimmed and say so.

---

## Model download — do it in Block 1, not at demo time

`base.en` is roughly 145 MB, fetched from Hugging Face on first use and cached at:

```
C:\Users\mothi\.cache\huggingface\hub
```

The Block 1 proof step (`python -m src.asr <wav>`) forces that download. **That is the point of running it early.** Discovering it at 11pm on a hotel-grade connection, or in the review room with campus wifi, is how demos die.

Once cached it works fully offline. Verify that before you sleep:

```powershell
# after the model is cached, turn wifi off and re-run the proof
.\.venv\Scripts\python.exe -m src.asr eval\sample.wav
```

Being able to say *"it runs fully offline on CPU"* in the review is worth real credit. Being able to say it because you tested it with wifi off is worth more.

---

## Run command

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Then open **`http://127.0.0.1:8000`** in Chrome.

**Never open `frontend/index.html` as a file.** `file://` is not a secure context, `getUserMedia` refuses to hand over the mic, and you will spend the evening debugging a non-bug. `127.0.0.1` and `localhost` are treated as secure origins, so plain HTTP is fine.

---

## Environment gotchas, ranked by how much time each will cost you

1. Wrong Python — venv built on 3.13. **Check `--version` inside the venv.**
2. `file://` frontend — mic silently unavailable.
3. Missing `python-multipart` — cryptic 500 on upload.
4. Model download during the demo.
5. `Activate.ps1` blocked by ExecutionPolicy — sidestep it, use the interpreter path.
6. Chrome holding the mic from a previous tab — close stale tabs before the review.
