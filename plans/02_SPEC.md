# 02 · Frozen Spec — Phase 0

Single source of truth for every contract. Task files reference this; they never redefine it.
**If code and this file disagree, the code is wrong.** If you decide to change a contract, change it *here first*, then in code.

---

## 0. Scope lock

**IN:** push-to-talk recording · faster-whisper `base.en` int8 CPU · exact longest-n-gram lookup over a 5-entry table · fingerspelling for names only · sequential HTML5 playback · debug panel · latency CSV.

**OUT, and say so on the deck:** VAD/streaming · sentence-transformers · FAISS · similarity thresholds · ISLTranslate · clip blending · avatars · ISL grammar · non-manual markers.

---

## 1. Repo layout

```
project/
├── .venv/                      gitignored
├── data/
│   ├── manifest.csv            COMMITTED
│   ├── clips/                  GITIGNORED  (licensed video)
│   └── alphabet/               GITIGNORED  (licensed video)
├── src/
│   ├── __init__.py
│   ├── asr.py
│   ├── matcher.py
│   ├── fingerspell.py
│   └── api.py
├── frontend/
│   └── index.html              one file, inline CSS + JS
├── eval/
│   ├── sample.wav              your voice, the demo sentence — COMMITTED
│   ├── test_utterances.txt     6 lines — COMMITTED
│   └── results.csv             COMMITTED (it is your evidence)
├── plans/                      this folder
├── preprojectdocs/             existing
├── requirements.txt
├── requirements.lock.txt
├── .gitignore
└── README.md
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
data/clips/
data/alphabet/
uploads/
*.webm
```

**`eval/results.csv` is NOT gitignored.** It is the evidence behind your Initial Results slide.

**Licensing rule:** ISLRTC video is never committed. `manifest.csv` carries the source URL for every clip so the dataset is reconstructible from the repo without redistributing it. Put this on a slide — examiners notice, and it is a free mark.

---

## 2. `data/manifest.csv`

```
id,phrase,ngram_len,source_url,local_path,duration_ms,license,notes
hello,hello,1,<url>,data/clips/hello.mp4,1400,ISLRTC,
thank_you,thank you,2,<url>,data/clips/thank_you.mp4,1800,ISLRTC,
sorry,sorry,1,<url>,data/clips/sorry.mp4,1300,ISLRTC,
please,please,1,<url>,data/clips/please.mp4,1500,ISLRTC,
name,name,1,<url>,data/clips/name.mp4,1200,ISLRTC,
```

- `phrase` is already lowercase and space-separated. The matcher keys on it directly.
- `ngram_len` must equal `len(phrase.split())`. Loader asserts this — a mismatch is a data bug that would otherwise surface as a silent non-match.
- `duration_ms` is informational until real clips land; update it then.
- `local_path` is repo-relative POSIX. See §7 for how it becomes a URL.

Adding a word later = **one CSV row plus one video file.** Nothing else. Say this out loud in the demo; it is the answer to "why only five words".

---

## 3. `src/asr.py`

```python
transcribe(audio_path: str) -> dict
# {"text": str, "language": str, "asr_ms": int, "model": "base.en"}
```

Config, non-negotiable:

| Param | Value | Why |
|---|---|---|
| model | `base.en` | English-only, ~145 MB, CPU-viable |
| `device` | `"cpu"` | No CUDA on this machine |
| `compute_type` | `"int8"` | ~3–4× faster on CPU; the accuracy cost is irrelevant for 5 words |
| `beam_size` | `1` | Greedy. Speed over accuracy, deliberately. |
| `language` | `"en"` | Skips language detection, saves ~100 ms |
| `initial_prompt` | `"Mothishwaran"` | Prompt conditioning to bias the decoder toward the out-of-vocabulary name |

**On `initial_prompt`:** this is the legitimate fix for Whisper mangling your name, and it is a good viva answer — you conditioned the decoder on a domain prior rather than post-hoc string-patching. If it still mishears, that is *also* fine: it demonstrates exactly why the fingerspelling fallback exists. Do not let this cost you more than 15 minutes.

Implementation notes:
- **Module-level lazy singleton.** Load the model once, reuse it. Reloading per request adds seconds and would wreck your latency table.
- Join segment texts with a space, then `.strip()`.
- `asr_ms` measured with `time.perf_counter()` around the transcribe call only — not around model load.
- CLI entry point `python -m src.asr <path.wav>` prints the dict. This is the Block 1 proof *and* it is what forces the model download.

---

## 4. `src/matcher.py`

```python
match(text: str) -> dict
# {
#   "normalized": str,
#   "plan": [{"token": str, "type": "sign"|"spell"|"uncovered", "clips": [str]}],
#   "coverage": float,
#   "counts": {"total": int, "sign": int, "spell": int, "uncovered": int},
#   "match_ms": int
# }
```

### Tokenisation — the part the brief left ambiguous

The brief says *"unmatched tokens that were capitalised mid-sentence get type `spell`."* Taken literally that breaks on your own demo sentence: `"Hello, thank you. My name is Mothishwaran."` — **`My` is capitalised and is not at index 0**, so a naive rule fingerspells `M-Y`. Resolved rule:

1. Split raw text on whitespace → `raw[]`, punctuation still attached.
2. `sentence_initial[i]` is true when `i == 0` **or** `raw[i-1]` ends with one of `. ? ! : ;`
3. `orig[i]` = `raw[i]` stripped of leading/trailing punctuation — **casing preserved**.
4. `norm[i]` = `orig[i]` lowercased, non-alphanumerics removed except the apostrophe.
5. Drop any token whose `norm` is empty.

### Matching

Greedy longest-n-gram, left to right, over `norm[]`. At each position try 3-gram, then 2-gram, then 1-gram against the manifest `phrase` set. First hit wins; advance by that many tokens. This is what makes `thank you` beat a bare `you`.

For an unmatched token at position `i`:
- `orig[i][0].isupper()` **and not** `sentence_initial[i]` → `type: "spell"`, `clips = fingerspell.spell(orig[i])`, `token = orig[i]` (original casing, so the debug panel reads properly)
- otherwise → `type: "uncovered"`, `clips = []`

**Never fingerspell an ordinary unknown word.** Spelling out every miss produces unreadable output and would be a false claim about the system's ability. Logging it as uncovered is the honest choice and is what gives you a real coverage number to report. This is viva question #15 — know why.

### Coverage — define it once, defend it forever

```
coverage = (tokens consumed by sign matches) / (total tokens)
```

`spell` and `uncovered` both count as **not covered**. Report `counts` alongside so the split is visible.

Coverage is **lexicon hit rate, not accuracy and not correctness**. It says what fraction of the utterance the sign inventory could address. It says nothing about whether the output is grammatical ISL — it isn't, and you say so. Viva question #18.

### Golden test case — assert on this exactly

Input: `"Hello, thank you. My name is Mothishwaran."`

| token | type | note |
|---|---|---|
| hello | sign | |
| thank you | sign | bigram beats unigram — the whole point of the algorithm |
| my | uncovered | sentence-initial capital, correctly not spelled |
| name | sign | |
| is | uncovered | |
| Mothishwaran | spell | capitalised, mid-sentence, not sentence-initial |

`total = 7` (`thank you` consumes 2) · `sign = 4` · `spell = 1` · `uncovered = 2`
**`coverage = 4/7 = 0.571`**

That 57.1% is a real number off a real utterance. It goes on the Initial Results slide as-is. Do not round it up and do not apologise for it — a system that honestly reports 57% coverage on a 5-word lexicon reads as competent. One that claims 100% reads as a lie.

### Self-test, no `tests/` directory

`if __name__ == "__main__":` block with assertions on the golden case plus: empty string, punctuation-only input, `"thank you"` alone, an all-uncovered sentence, and a lone capitalised word at index 0 (must be `uncovered`, not `spell`). Print `OK` and the plan table. Run with `python -m src.matcher`. **Screenshot the passing output — it is a deck asset.**

### Block 4 contingency, not upfront work

If testing shows Whisper *consistently* produces one specific mangling of your name, add:

```python
SPELL_ALIASES = {"motishwaran": "Mothishwaran"}   # normalized -> canonical spelling
```

applied to `spell`-typed tokens only. Add this **only if** you observe it repeatedly. Do not pre-build it.

---

## 5. `src/fingerspell.py`

```python
spell(word: str) -> list[str]
# "Mothishwaran" -> ["data/alphabet/m.mp4", "data/alphabet/o.mp4", ...]
```

Lowercase, drop every non `a-z` character, map each letter to `data/alphabet/{letter}.mp4`.

**Timing reality check.** `Mothishwaran` is 12 letters. At ~800 ms per clip that is ~9.6 s of fingerspelling on top of ~4.4 s of signs — a **~14 second** demo playback. That is long enough to feel like a hang in a review room.

Mitigation, in order of preference:
1. Trim alphabet clips to ~500 ms → total drops to ~10 s. Comfortable.
2. Set `playbackRate = 1.25` on alphabet clips only, in the frontend. One line.
3. Say "and it fingerspells the rest" and let it run — it is genuinely impressive to watch.

Do 1 if the clips arrive trimmed, else 2. Either way, **know the number before you present**, so you can narrate over it instead of standing in silence.

Unique letters needed: **M O T H I S W A R N** — 10 files, not 26. The other 16 are cut.

---

## 6. `eval/results.csv`

Append-only, two row types, joined on `run_id`.

```
row_type,run_id,timestamp,transcript,n_total,n_sign,n_spell,n_uncovered,coverage,asr_ms,match_ms,server_ms,e2e_ms,note
```

- `row_type=translate` — written by `/translate`. `e2e_ms` blank.
- `row_type=frame` — written by `/log_frame` when the client renders the first video frame. Only `run_id` and `e2e_ms` populated.

Append-only means a crash mid-demo cannot corrupt earlier rows. Header written once, on first create.

### The three timestamps

| | Where | When |
|---|---|---|
| `t0` | client | recording stopped |
| `t1` | server | response sent |
| `t2` | client | **first video frame actually rendered** |

Report **`e2e_ms = t2 − t0`** as end-to-end latency. Both are client-clock, so there is no clock-skew problem — which is precisely why t0 is measured on the client and shipped to the server rather than being taken at request arrival.

`t2` uses the `playing` event on the first video element, not `play()` returning. `play()` resolves before a frame is on screen; reporting that would flatter your number and it would be wrong.

---

## 7. `src/api.py`

FastAPI. Serves the API, the frontend, and the clips from one origin — so CORS is a non-issue and `getUserMedia` gets a secure context.

```python
app.mount("/data", StaticFiles(directory="data"), name="data")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")   # mount LAST
```

`CORSMiddleware` with `allow_origins=["*"]` stays in anyway — it costs one import and saves you if you ever open the page from a second port.

**Path → URL rule:** `matcher` returns repo-relative POSIX paths (`data/clips/hello.mp4`). `api` prefixes `/` to produce browser URLs (`/data/clips/hello.mp4`), which resolve against the `/data` mount. Convert in `api.py` only; the matcher stays filesystem-oriented and independently testable.

### `POST /translate`
multipart: `audio` (file, `audio/wav` expected) · `client_t0` (string, epoch ms)

```json
{
  "run_id": "a3f1...",
  "transcript": "Hello, thank you. My name is Mothishwaran.",
  "normalized": "hello thank you my name is mothishwaran",
  "plan": [
    {"token": "hello",        "type": "sign",      "clips": ["/data/clips/hello.mp4"]},
    {"token": "thank you",    "type": "sign",      "clips": ["/data/clips/thank_you.mp4"]},
    {"token": "my",           "type": "uncovered", "clips": []},
    {"token": "name",         "type": "sign",      "clips": ["/data/clips/name.mp4"]},
    {"token": "is",           "type": "uncovered", "clips": []},
    {"token": "Mothishwaran", "type": "spell",     "clips": ["/data/alphabet/m.mp4", "..."]}
  ],
  "coverage": 0.571,
  "counts": {"total": 7, "sign": 4, "spell": 1, "uncovered": 2},
  "timings": {"asr_ms": 0, "match_ms": 0, "server_ms": 0}
}
```

Writes the uploaded audio to `uploads/{run_id}.wav`, transcribes, matches, appends the `translate` row, returns.

### `POST /log_frame`
JSON `{"run_id": str, "e2e_ms": int}` → appends the `frame` row → `{"ok": true}`. Six lines. That is the entire justification for having a second endpoint.

### `GET /health`
```json
{"ok": true, "model_loaded": true, "manifest_rows": 5,
 "missing_clips": ["data/clips/sorry.mp4"], "alphabet_present": 10}
```

Free diagnostic, and it is the fastest way to answer "is the demo ready" without speaking into a microphone. Screenshot it for the deck.

**Model preload on startup.** Load the Whisper model in a FastAPI lifespan handler. If the first request pays the load cost, your first latency row is a 4-second outlier and your latency table becomes a lie you then have to explain.

---

## 8. `frontend/index.html`

One file. Inline CSS and JS, no build step, no CDN.

**Record** — push-to-talk. Press to start, press to stop. `MediaRecorder` at device rate; on stop, decode → resample to 16 kHz mono via `OfflineAudioContext` → encode PCM16 WAV → POST with `client_t0 = Date.now()` captured **at stop**, before any encoding work.

**Preload before playing.** Build a `<video>` for every clip in the plan with `preload="auto"`, wait for `canplaythrough` on all of them, *then* start. Race each wait against a ~4 s timeout so one missing file cannot hang the demo forever.

**Playback — A/B double buffer.** Two stacked `<video>` elements. While A plays clip *n*, B is already loaded with clip *n+1*; on A's `ended`, swap visibility and play B, then load *n+2* into A. This removes the black flash and the stutter properly. A single element with `src` swapping visibly hiccups, and that hiccup is the thing people notice in a demo.

**Missing clip:** `console.error` with the exact path, skip it, mark that token as errored in the debug panel, keep going. **The queue must never stall on a missing file.** This directly implements the brief's "fail gracefully with a clear console message".

**Debug panel** — this is the demo's real evidence, not decoration:
- transcript, verbatim
- every token as a chip, colour-coded: `sign` green · `spell` amber · `uncovered` grey
- coverage as a percentage plus the raw `counts`
- `asr_ms`, `match_ms`, `server_ms`, `e2e_ms`
- a state line: Idle / Recording / Transcribing / Preloading / Playing

Make the panel big and readable. It is what you point at while presenting, and it is Deck Screenshot #2.

---

## 9. `eval/test_utterances.txt`

Six lines. Read each aloud in Block 4.

```
Hello, thank you. My name is Mothishwaran.
Hello.
Thank you.
Sorry.
Please.
My name is Mothishwaran.
```

Line 1 is the demo sentence and the only one you rehearse for performance. Lines 2–5 prove single-word retrieval. Line 6 isolates the fingerspelling path so you can time it separately.

---

## 10. Things this system genuinely cannot do — memorise, then say it first

Stated plainly before an examiner asks, this reads as mastery. Extracted when caught out, it reads as a hole in the work.

- It is **not translation.** It is constrained lexical retrieval into a 5-entry inventory.
- **Word order is English.** ISL has its own grammar; concatenating clips in English order is linguistically wrong and is not claimed to be otherwise.
- **No non-manual markers** — facial expression, head tilt, mouthing. These carry grammatical meaning in ISL and none of it survives clip concatenation.
- **No co-articulation.** Real signing blends transitions between signs; hard cuts between clips do not.
- **Unknown words are dropped, not guessed.** Coverage reports exactly how much was dropped.
- **Fingerspelling is a fallback, not natural output.** Deaf signers do not fingerspell everything.
- Whisper is a **known-good component being used, not a contribution.** The contribution is the retrieval pipeline and its honest evaluation.

---

## 11. Phase 1 amendments (October 2026)

Sections 1–10 are the Phase 0 contract as frozen for Review 1. These amendments supersede them
where they conflict; the code follows these.

**§1 / §2 · Data layout.** Dictionary videos live in `data/_source/isl_dictionary/` (gitignored,
the Drive folder as extracted); `data/manifest.csv` is generated by `tools/build_manifest.py`
and its `local_path` points there (or to `data/_derived/` for transcoded/trimmed clips).
`data/clips/` is no longer used. Curated, committed inputs: `data/aliases.csv`,
`data/synonyms.csv` (`tools/build_synonyms.py`), `data/trims.csv`. Alphabet clips
(`data/alphabet/a–z.mp4`) are committed.

**§3 · ASR.** Model = `models/whisper-base-en-svarah` (fine-tuned, committed) when present,
else `base.en`; override with `SPEECH_ISL_MODEL`. Device = CUDA float16 when available, else
CPU int8; override with `SPEECH_ISL_DEVICE`. `transcribe()` additionally returns `"device"`.

**§4 · Matcher.** `match(text, spell_unknown=False)`. Token types, resolved in this order:
`sign` (longest n-gram; also inflected forms from `synonyms.csv`, with `"means"`),
`spell` (name; `"why": "name"`), `omitted` (`matcher.ISL_OMITTED`), `similar` (reviewed synonym,
`"means"`), `spell` (`"why": "unknown"`, only when `spell_unknown`), `uncovered`.
Return adds `content_coverage` (signs ÷ non-omitted tokens) and
`content_coverage_with_similar`; `counts` adds `similar` and `omitted`. `coverage` keeps its
Phase 0 definition. Golden case (§4): coverage unchanged at 4/7; `is` is now `omitted`, so
`uncovered = 1`, `omitted = 1`.

**§6 · Results CSV.** Columns appended (old rows are migrated with blanks, never edited):
`n_omitted, content_coverage, n_similar, speaker`. `note` also records the ASR model/device,
`spell_unknown`, and `encode_error=<reason>` when the browser WAV path failed.

**§7 · API.** `/translate` accepts `spell_unknown`, `speaker`, `encode_error`; the response adds
`content_coverage`, `content_coverage_with_similar`, per-token `why`/`means`, and
`asr: {model, device}`. Clip URLs are percent-encoded. `/health` adds `asr_model`,
`asr_device`, `missing_count`, `alphabet_expected`. New `GET /eval_sentences` (ids from
`src/eval_sets.py`: `u1–u6`, `s01–s20`, `h01–h20`).

**§9 · Evaluation.** Sentence sets: `eval/test_utterances.txt` (Phase 0), `eval/test_sentences.txt`
(everyday), `eval/test_sentences_heldout.txt` (held-out — never used for tuning; quote these).
Real-voice scoring per speaker: `tools/analyze_results.py`. ASR on unseen speakers:
`tools/train/evaluate.py`. Results are in the notebook, § 14B.

**§10 · Limitations.** Still all true except "5-entry inventory" (now ~3,850 phrases) — see the
notebook's § 15 for the current list.

### 11.1 · Amendments — 7 October 2026 (Drive on demand, related signs, live analysis)

**Drive on demand.** `data/drive_manifest.csv` (committed; generated by `build_manifest.py`
from the Drive index) maps phrases to Drive file ids for signs not on disk. `match()` takes
`use_drive=True`: a Drive phrase becomes a `sign` entry with a `"drive"` key; `/translate`
downloads each needed file once (`src/drive_fetch.py`, per-file lock), rejects clips > 30 s
(remembered in `data/_derived/drive_rejected.csv`), transcodes non-H.264, and marks the entry
`source: "drive"`. A failed fetch downgrades the entry to `uncovered` with the reason, and counts
are recomputed with `matcher.score(plan)`. Every entry now carries `n_words`.

**Related signs.** `data/synonyms.csv` gains `kind = related` (WordNet hypernym, ≤ 2 levels,
nouns only, most-attested sense, vague parents excluded); used unless `review = reject`.
`match(..., use_related=True)`; type `related` with `"means"`; `counts.related`;
`content_coverage_with_related`. `/translate` accepts `use_related`.

**Results CSV** appends `n_related, drive_ms`. **Response** adds per-token `source`,
`drive_status`, and `timings.drive_ms`. **/health** adds `drive: {fetchable_phrases, api_key}`.

**Live analysis** is client-side only (no API change): waveform, spectrogram, normalised
autocorrelation F0 with octave guard, short-time energy, ZCR.

### 11.2 · Amendments — 8 October 2026 (noise, questions, ISL order, numbers)

**ASR.** `asr.transcribe(audio, denoise=False)` accepts a path or a 16 kHz float32 array;
`denoise=True` applies `src/denoise.spectral_subtract` first and reports `denoise_ms`.

**Prosody.** `src/prosody.final_rise(audio16k)` → `{voiced_ratio, median_f0, final_rise_st,
rising}`; threshold from `eval/question_threshold.json` (set by `tools/question_study.py`).
Reported, not decisive.

**Matcher.** Plan entries gain `sent` (sentence index) and `sent_q` (sentence ended with "?").
Numbers: `number_signs(token, manifest)` → list of dictionary phrases (spoken reading, else
digit by digit); a number becomes one `sign` entry with several clips and `means`.

**ISL order.** `src/isl_order.detect_question(transcript, plan)` → `{type: wh|yesno|None,
sentence, evidence}`; `reorder(plan)` → `(play order as plan indices, rules applied)`;
`gloss(plan, order)`.

**API.** `/translate` accepts `use_isl_order` (default 1) and `denoise` (default 0); response
adds `question` (with `pitch`), `isl: {enabled, order, rules, gloss}`, `timings.denoise_ms`.
The UI plays clips in `isl.order`. Results CSV appends `question, final_rise_st, isl_rules,
denoise`.

### 11.3 · Amendments — 9 October 2026 (defaults after live testing)

**Defaults.** `/translate`: `spell_unknown=1`, `use_related=0`, `use_isl_order=0`. Lookup order:
local phrase → Drive phrase (fetched) → number → name → omitted → form → synonym → related (if
on) → fingerspell (if on; a failed Drive fetch also falls back to fingerspelling) → uncovered.
`isl_order.reorder` never moves fingerspelled entries.

**New endpoint.** `POST /translate_text` (form: `text`, `spell_unknown`, `use_related`,
`use_isl_order`, `speaker`) runs the same pipeline without ASR; the results row note starts with
`typed` and `tools/analyze_results.py` excludes such rows.

**Clips.** Responses under `/data/` and the page carry `Cache-Control: no-cache`. Alphabet clips
are 45 frames at 30 fps (1.5 s); the page plays fingerspelling at 1.5× by default.
