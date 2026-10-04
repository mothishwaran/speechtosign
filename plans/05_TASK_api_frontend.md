# 05 · Block 3 — API + Frontend

**Budget: ~1.5 hours.** Contracts: [02_SPEC.md](02_SPEC.md) §6, §7, §8.
Highest-risk block in the sprint. Build the API first and verify it with `/health` and a file upload **before** writing a single line of frontend JS — debugging both halves at once is what turns 1.5 hours into 4.

---

## Part A — `src/api.py` (~40 min)

Per spec §7.

Order of work:

1. **App + lifespan model preload.** Call `asr.get_model()` on startup so no request pays the load cost. Uvicorn should print something like `model loaded in 2100ms` before it says `Application startup complete`.
2. **`GET /health`** — spec §7. Include `missing_clips` by stat-ing every `local_path` in the manifest plus the 10 alphabet files. Build this second; it is your debugging tool for the rest of the block.
3. **Static mounts.** `/data` → `data/`, then `/` → `frontend/` with `html=True`. **Mount `/` last** — mounting root first swallows every other route.
4. **`POST /translate`** — save upload to `uploads/{run_id}.wav`, `asr.transcribe`, `matcher.match`, prefix clip paths with `/`, append the `translate` row, return the §7 shape.
5. **`POST /log_frame`** — append the `frame` row. Six lines.
6. **CSV append helper** — write the header only when the file does not exist; open in `"a"` with `newline=""` (Windows will otherwise give you blank lines between rows).

Verify with no browser involved:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```
```powershell
Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json -Depth 4
curl.exe -F "audio=@eval/sample.wav" -F "client_t0=0" http://127.0.0.1:8000/translate
```

Second command must return the full JSON plan for the golden sentence. **Do not start Part B until it does.**

---

## Part B — `frontend/index.html` (~50 min)

One file, inline CSS and JS, no build step, no CDN.

### 1 · Recording and the WAV encoder

This is the piece with no room for improvisation — see [01_ENVIRONMENT.md](01_ENVIRONMENT.md) for why it exists.

```
button press   -> getUserMedia({audio: {channelCount:1, echoCancellation:true}})
                  -> new MediaRecorder(stream)  [device-native rate, let it choose]
button press   -> stop; clientT0 = Date.now()   <-- capture FIRST, before any work
                  -> Blob -> arrayBuffer
                  -> new AudioContext().decodeAudioData()
                  -> OfflineAudioContext(1, ceil(dur*16000), 16000) -> startRendering()
                  -> encodeWAV(float32, 16000)   // 44-byte RIFF header + PCM16
                  -> FormData{audio: wavBlob, client_t0: clientT0} -> POST /translate
```

`encodeWAV` is ~40 lines: RIFF/WAVE/fmt /data header, then `Math.max(-1, Math.min(1, s)) * 0x7FFF` per sample into an `Int16Array`. Standard, well-known code — write it once and do not touch it again.

**Do not set `sampleRate: 16000` in the `getUserMedia` constraint and assume it worked.** Chrome commonly ignores it. The `OfflineAudioContext` resample is what actually guarantees 16 kHz, and "why 16 kHz" is a near-certain viva question — you want the true answer.

### 2 · Preload gate

For every clip URL in the plan, create a `<video preload="auto">` and wait for `canplaythrough`. `Promise.all` across all of them, each raced against a ~4 s timeout so one missing file cannot hang the demo. Show `Preloading n/N` in the state line. Only then start playback.

This gate is what makes the demo look smooth. It is also the answer to "how did you handle the stutter" — you didn't paper over it, you eliminated the cause.

### 3 · A/B double-buffered playback

Two `<video>` elements stacked in the same box, one visible at a time.

```
A plays clip n   |   B already has clip n+1 loaded
A fires 'ended'  ->  swap visible, B.play(), load clip n+2 into A
```

Simpler alternative if you fall behind: one element, swap `src` on `ended`. It works, it just visibly flickers. **Budget 20 minutes for A/B; if it fights you, take the single element and move on.** A flicker costs you nothing at the review; an unfinished frontend costs you the demo.

### 4 · `t2` and `/log_frame`

Listen for the **`playing`** event on the first clip — not the resolution of `play()`, which fires before a frame is on screen. On `playing`:

```js
const e2e = Date.now() - clientT0;
fetch('/log_frame', {method:'POST', headers:{'Content-Type':'application/json'},
                     body: JSON.stringify({run_id, e2e_ms: e2e})});
```

Show `e2e` in the debug panel. This number goes straight onto your Initial Results slide.

### 5 · Debug panel

Big and readable — you present by pointing at it.

- transcript, verbatim, large type
- token chips, colour-coded: **`sign` green · `spell` amber · `uncovered` grey**. Include a small legend; the examiner will not otherwise know what the colours mean.
- `Coverage: 57.1%  (4 sign · 1 spell · 2 uncovered · 7 total)`
- `ASR 850ms · Match 1ms · Server 910ms · End-to-end 1340ms`
- state line: `Idle → Recording → Transcribing → Preloading 3/15 → Playing 4/15 → Done`

### 6 · Missing-clip handling

`console.error` the exact path, mark the chip with a red outline, **skip and continue the queue.** The queue must never stall on a missing file — spec §8. Test this deliberately: rename one clip, confirm the rest still plays.

---

## Proof of done

Open **`http://127.0.0.1:8000`** — never `file://`.

- [ ] Mic permission prompt appears; button toggles Record ⇄ Stop
- [ ] Speaking the demo sentence yields the correct transcript in the panel
- [ ] Clips play **in order**: hello → thank_you → name → m,o,t,h,i,s,h,w,a,r,a,n
- [ ] No black flash between clips (or a known, accepted flicker if you took the fallback)
- [ ] Coverage shows `57.1%`
- [ ] All four timings are populated and plausible
- [ ] `eval/results.csv` gains a `translate` row **and** a matching `frame` row
- [ ] Renaming a clip → console error + demo continues
- [ ] Whole flow survives a hard browser refresh

---

## Traps, in the order they will bite you

1. `file://` → no mic. **Always `http://127.0.0.1:8000`.**
2. Mounting `/` before the API routes → every endpoint 404s.
3. Missing `python-multipart` → cryptic 500 on upload.
4. `client_t0` captured after WAV encoding → your latency number is quietly wrong (too low).
5. Using `play().then()` as `t2` → also quietly wrong (too low). Use the `playing` event.
6. CSV opened without `newline=""` on Windows → blank line between every row.
7. Autoplay policy: the first `play()` must descend from a user gesture. It does here, because everything is downstream of the button press — do not add a `setTimeout` between the gesture and the first `play()` or you will break that chain.
