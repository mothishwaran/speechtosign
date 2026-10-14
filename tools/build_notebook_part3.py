"""Cells: Whisper, normalisation, matching, fingerspelling, serving, eval, refs."""

from tools.build_notebook_part1 import CELLS


def md(t):
    CELLS.append(("markdown", t.strip("\n")))


def code(t):
    CELLS.append(("code", t.strip("\n")))


# ─────────────────────────────────────────── 7 WHISPER
md(r"""
---
# § 7 · Speech recognition with Whisper

## What Whisper is

An **encoder–decoder Transformer** [1]. Not CTC — this is a common exam question, so be sure of it.

```
 log-mel spectrogram (80 bins, 30 s padded window)
              │
              ▼
      ┌───────────────┐
      │    ENCODER    │  reads the whole audio, builds a representation
      └───────┬───────┘
              │ cross-attention
              ▼
      ┌───────────────┐
      │    DECODER    │  writes text one token at a time,
      └───────┬───────┘  each token conditioned on all previous ones
              ▼
        English text
```

**Training:** 680,000 hours of weakly-supervised multilingual audio. That scale — not a clever
architecture — is the paper's actual contribution, and it is why Whisper handles Indian-accented
English it was never specifically trained on.

## CTC vs encoder–decoder (know both)

| | CTC | Encoder–decoder (Whisper) |
|---|---|---|
| Alignment | Monotonic, frame-level, uses a blank symbol | Learned via attention |
| Output dependencies | Conditionally independent | Autoregressive — each token sees the previous |
| Streaming | Natural | Not natural |
| Accuracy | Lower | Higher |

## Our configuration, and the reasoning for each choice

| Setting | Value | Why |
|---|---|---|
| Model | `base.en` | English-only, ~145 MB, runs on CPU |
| `device` | `cpu` | No GPU on the target laptop |
| `compute_type` | `int8` | ~4× smaller, much faster on CPU |
| `beam_size` | `1` | Greedy decoding — speed over marginal accuracy |
| `language` | `en` | Skips language detection, saves ~100 ms |
| `initial_prompt` | `"Mothishwaran"` | Biases the decoder toward an out-of-vocabulary name |

### What int8 quantisation actually is

Weights are stored as **8-bit integers** instead of 32-bit floats. Four times smaller, and CPUs
run integer arithmetic much faster. The cost is **quantisation error** — a small accuracy loss.
For a 6-entry vocabulary that loss is irrelevant, and latency is what the demo is judged on. A
deliberate trade, not a default we inherited.

### On `initial_prompt` — a technique that did *not* work

Whisper accepts a text prompt to condition decoding. We prompt it with the name so it is more
likely to produce it. **We measured this and it failed** — see § 14. That negative result is
reported rather than hidden.
""")

code(r"""
# Loading the model takes a few seconds; transcription itself is fast.
from src import asr
import time

t0 = time.perf_counter()
model = asr.get_model()
print(f"model load: {(time.perf_counter()-t0)*1000:.0f} ms  (one-off, cached afterwards)")
""")

code(r"""
result = asr.transcribe("eval/sample.wav")

print("transcript :", result["text"])
print("language   :", result["language"])
print("model      :", result["model"])
print("asr_ms     :", result["asr_ms"], "ms")
""")

# ─────────────────────────────────────────── 8 NORMALISATION
md(r"""
---
# § 8 · Text normalisation and tokenisation

Whisper gives us punctuated, capitalised text:

> `"Hello, thank you. My name is Mothishwaran."`

Our dictionary is lowercase and unpunctuated. So we normalise — but **we cannot simply throw the
punctuation away**, and the reason is subtle and important.

## The trap: capitalisation tells us about names, but only sometimes

Our rule for detecting a proper noun is *"capitalised in the middle of a sentence"*.

Look what happens if we apply that naively to our own demo sentence:

| token | capitalised? | at index 0? | naive verdict | correct verdict |
|---|---|---|---|---|
| Hello | yes | yes | — | — |
| My | **yes** | **no** | **name → fingerspell M-Y** ❌ | ordinary word ✅ |
| Mothishwaran | yes | no | name → fingerspell ✅ | name → fingerspell ✅ |

`My` is capitalised because it **starts a new sentence** (the previous token ended with `.`), not
because it is a name. A naive implementation fingerspells **M-Y** and the demo looks broken.

## The fix

Track **sentence boundaries** before stripping punctuation. A token is *sentence-initial* if it
is the first token, **or** the previous token ended with `.` `?` `!` `:` `;`

We therefore keep three parallel arrays per token:

| array | content | used for |
|---|---|---|
| `orig` | original casing, punctuation stripped | name detection, display |
| `norm` | lowercase, alphanumeric only | dictionary lookup |
| `sentence_initial` | boolean | suppressing the false name detection |
""")

code(r"""
from src.matcher import _tokenize

text = "Hello, thank you. My name is Mothishwaran."
orig, norm, sent_init = _tokenize(text)

print(f"input: {text}\n")
print(f"{'#':<3}{'orig':<16}{'norm':<16}{'sentence-initial':<18}note")
print("-" * 72)
for i, (o, n, s) in enumerate(zip(orig, norm, sent_init)):
    note = ""
    if o[0].isupper() and s:      note = "capitalised BUT sentence-initial -> not a name"
    elif o[0].isupper() and not s: note = "capitalised mid-sentence -> treat as name"
    print(f"{i:<3}{o:<16}{n:<16}{str(s):<18}{note}")
""")

# ─────────────────────────────────────────── 9 MATCHER
md(r"""
---
# § 9 · The matching algorithm

## Greedy longest-n-gram matching

Walk left to right. At each position, try the **longest** phrase first, then shorter ones. First
match wins, and we jump past everything it consumed.

```
position i:
    for n = longest_phrase_in_dictionary  down to  1:
        if norm[i : i+n] is in the dictionary:
            emit "sign", advance i by n        ← consumed n words at once
            break
    else:                                       ← nothing matched
        if capitalised and not sentence-initial:
            emit "spell"                        ← fingerspell it
        else:
            emit "uncovered"                    ← drop it, and COUNT it
        advance i by 1
```

## Why longest-first matters

Our dictionary has both `thank you` and (in principle) `you`. Shortest-first would match `thank`
→ nothing, then `you` → the wrong sign. **Longest-first matches `thank you` as one unit**, which
is correct: it is one sign in ISL, not two.

The same mechanism handles `so far so good` — a **four-word phrase retrieved as a single clip**.
That is a small but genuine demonstration of *phrase-level* retrieval, the direction Phase 1
takes with ISLTranslate.

> **Design note.** The maximum n-gram length is **read from the manifest**, not hardcoded. Adding
> a longer phrase needs no code change. An earlier version hardcoded 3 and would have silently
> never matched the 4-word phrase — a bug worth mentioning because it is exactly the kind that
> produces no error, just quietly wrong behaviour.
""")

code(r"""
print("longest phrase in the dictionary:", matcher.max_ngram(), "words")
print("(derived from manifest.csv - not hardcoded)\n")

out = matcher.match("Hello, thank you. My name is Mothishwaran.")

print(f"{'token':<16}{'type':<12}{'clips':<7}note")
print("-" * 68)
for p in out["plan"]:
    note = {"sign": "found in dictionary",
            "spell": "proper noun -> fingerspelled",
            "uncovered": "not in dictionary -> dropped and counted"}[p["type"]]
    print(f"{p['token']:<16}{p['type']:<12}{len(p['clips']):<7}{note}")

print(f"\ncoverage : {out['coverage']:.4f}  ({out['coverage']*100:.1f}%)")
print(f"counts   : {out['counts']}")
print(f"match_ms : {out['match_ms']} ms")
""")

code(r"""
# The behaviours worth proving, including the ones that are easy to get wrong.
tests = [
    ("thank you",                    "bigram beats two unigrams"),
    ("So far so good",               "4-word phrase -> ONE clip"),
    ("You thank me",                 "loose word order must NOT match the bigram"),
    ("Mothishwaran is here",         "capitalised at index 0 -> uncovered, NOT spelled"),
    ("My name is Mothishwaran",      "'My' sentence-initial -> uncovered, not M-Y"),
    ("The cat sat",                  "all unknown -> uncovered, nothing fingerspelled"),
]

for text, why in tests:
    r = matcher.match(text)
    types = [f"{p['token']}:{p['type']}" for p in r["plan"]]
    print(f"{text!r}")
    print(f"   {why}")
    print(f"   -> {'  '.join(types)}")
    print(f"   coverage {r['coverage']*100:5.1f}%   {r['counts']}\n")
""")

md(r"""
### The most important test above

`"The cat sat"` → **everything uncovered, nothing fingerspelled.**

The tempting shortcut is to fingerspell every unknown word so the system always produces
*something*. We deliberately do not, for two reasons:

1. **It would be unreadable.** Deaf signers fingerspell names and technical terms — not every
   word. A wall of letters is not usable sign language.
2. **It would hide the truth.** Constant output makes a system *look* like it is working. Counting
   what it dropped is what makes the coverage metric meaningful.
""")

# ─────────────────────────────────────────── 10 FINGERSPELL
md(r"""
---
# § 10 · Fingerspelling

When a word is a proper noun and has no sign, we spell it letter by letter using the ISL manual
alphabet — **two-handed**, unlike ASL and BSL.

The 26 letter clips were produced by splitting a single 80-second ISL alphabet video. Boundaries
were located by reading the video's own on-screen letter caption, then each clip was cut as a
centred window so the crossfades between letters are excluded. Every output was verified by
extracting its middle frame and confirming the caption matched the filename.

> **Speed matters more than it seems.** Fingerspelling rate is limited by what the **receiver**
> can read, not by what the system can emit. An early version played letters at 1.5× to keep the
> demo short — that was optimising the wrong thing, and it was corrected to true recorded speed.
> A sequence the receiver cannot parse has no communicative value however fast it was produced.
""")

code(r"""
name = "Mothishwaran"
clips = fingerspell.spell(name)

print(f"{name}  ->  {len(clips)} letter clips")
print("  " + " ".join(os.path.basename(c).replace('.mp4','').upper() for c in clips))

print("\nnon-alphabetic characters are dropped:")
for w in ["O'Brien-42", "R2D2", ""]:
    got = [os.path.basename(c)[0].upper() for c in fingerspell.spell(w)]
    print(f"  {w!r:<14} -> {got}")
""")

# ─────────────────────────────────────────── 11 SERVING
md(r"""
---
# § 11 · Serving the system

## Architecture

```
 Browser (frontend/index.html)          FastAPI server (src/api.py)
 ─────────────────────────────          ──────────────────────────
  MediaRecorder captures audio
  decode + resample attempt
             │  POST /translate  (audio + client_t0)
             └───────────────────────▶  save upload
                                        asr.transcribe()   → text
                                        matcher.match()    → plan
                                        append results.csv
             ◀───────────────────────  {transcript, plan, coverage, timings}
  preload every clip
  play sequentially (A/B buffer)
             │  POST /log_frame  (e2e_ms)
             └───────────────────────▶  append results.csv
```

## Three decisions worth explaining

**1 · One origin for everything.** FastAPI serves the API *and* the HTML *and* the video files.
Opening the page as a `file://` document would break the microphone entirely — `getUserMedia`
requires a *secure context*, and `http://127.0.0.1` qualifies while `file://` does not.

**2 · Preload before playing.** Every clip is fetched and buffered *before* the first one starts,
each with a timeout so one missing file cannot hang the demo. Then playback alternates between
**two stacked video elements** — while A plays clip *n*, B already holds clip *n+1*. This removes
the black flash you get from swapping `src` on a single element.

**3 · A missing clip must never stall the queue.** It logs an error, marks the token in the debug
panel, and playback continues.

## Measuring latency honestly

| Timestamp | Where | When |
|---|---|---|
| `t0` | client | the moment recording stops |
| `t1` | server | response sent |
| `t2` | client | **first video frame actually rendered** |

We report **`t2 − t0`**. Both ends are on the client's clock, so there is no clock-skew problem.

`t2` uses the video element's `playing` event, **not** the resolution of `play()`. `play()`
resolves before a frame is on screen — using it would make our latency look better than it is.
That would be a flattering measurement, which is to say a wrong one.
""")

# ─────────────────────────────────────────── 12 DEMO
md(r"""
---
# § 12 · Running the demo end to end

Start the server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000** — never the file directly.

The cell below runs the same pipeline the browser runs, so the notebook is self-contained.
""")

code(r"""
# The full pipeline: audio file -> transcript -> plan -> clip list.
import time

t_start = time.perf_counter()
asr_out   = asr.transcribe("eval/sample.wav")
match_out = matcher.match(asr_out["text"])
total_ms  = (time.perf_counter() - t_start) * 1000

print("STEP 1  audio    :", "eval/sample.wav")
print("STEP 2  transcript:", asr_out["text"])
print("STEP 3  normalised:", match_out["normalized"])
print("STEP 4  playback plan:")
for p in match_out["plan"]:
    for c in p["clips"]:
        print(f"           {p['type']:<10} {c}")
    if not p["clips"]:
        print(f"           {p['type']:<10} (nothing to play)")

print(f"\ncoverage : {match_out['coverage']*100:.1f}%")
print(f"asr      : {asr_out['asr_ms']} ms")
print(f"match    : {match_out['match_ms']} ms")
print(f"total    : {total_ms:.0f} ms")
""")

# ─────────────────────────────────────────── 13 EVAL DESIGN
md(r"""
---
# § 13 · Evaluation design

## The metrics, and precisely what each does and does not mean

### Coverage

$$ \text{coverage} = \frac{\text{tokens matched to a sign}}{\text{total tokens}} $$

Words that get fingerspelled or dropped both count as **not covered**.

**Coverage is a lexicon hit rate.** It answers: *what fraction of what was said do we have signs
for?*

It does **not** measure:
- whether the output is grammatically correct ISL (it is not)
- whether a Deaf viewer could understand it (we have not tested that)
- whether the retrieved sign was the right sense of an ambiguous word

Calling this "accuracy" would be a serious overclaim. Real accuracy would require evaluation by
Deaf signers, which is out of scope for Phase 0 and which we do not claim to have done.

### Word Error Rate (WER) — for the ASR stage only

$$ \text{WER} = \frac{S + D + I}{N} $$

Substitutions + Deletions + Insertions, over the number of words in the **reference**.

Worked example — Reference: `the cat sat on the mat` (N=6), Hypothesis: `the cat sat on mat`.
One deletion (`the`), so WER = 1/6 ≈ **16.7%**.

> WER can exceed 100%, because insertions are unbounded. A common follow-up question.

### Latency

End-to-end = recording stops → first video frame appears. Reported as **median with range**, never
a single best-case number.

## Why coverage and WER must be reported separately

They measure different stages. If Whisper mishears a word, coverage may drop even though the
matcher behaved perfectly. Collapsing them into one number would hide *which component* failed.
""")

code(r"""
# WER, implemented with the standard edit-distance dynamic program.
def wer(reference, hypothesis):
    r, h = reference.lower().split(), hypothesis.lower().split()
    d = np.zeros((len(r)+1, len(h)+1), dtype=int)
    d[:, 0] = np.arange(len(r)+1)
    d[0, :] = np.arange(len(h)+1)
    for i in range(1, len(r)+1):
        for j in range(1, len(h)+1):
            cost = 0 if r[i-1] == h[j-1] else 1
            d[i, j] = min(d[i-1, j] + 1,        # deletion
                          d[i, j-1] + 1,        # insertion
                          d[i-1, j-1] + cost)   # substitution / match
    return d[len(r), len(h)] / len(r), d[len(r), len(h)], len(r)

for ref, hyp in [
    ("the cat sat on the mat", "the cat sat on mat"),
    ("hello thank you my name is mothishwaran", "hello thank you my name is mothish"),
    ("hello thank you", "hello thank you"),
]:
    rate, errs, n = wer(ref, hyp)
    print(f"ref: {ref}\nhyp: {hyp}\n  -> {errs} error(s) / {n} words = WER {rate*100:.1f}%\n")
""")

code(r"""
# Read the measured runs and produce the deck tables.
import subprocess, sys as _s
print(subprocess.run([_s.executable, "tools/analyze_results.py"],
                     capture_output=True, text=True).stdout or
      "No runs logged yet - record some in the browser first.")
""")

# ─────────────────────────────────────────── 14 RESULTS
md(r"""
---
# § 14 · Results and findings

*(Numbers below come from the logged development runs. Re-run § 13 after the formal evaluation
to refresh them.)*

## Measured latency

| Stage | Median | Range |
|---|---|---|
| ASR (`base.en`, int8, CPU) | ~826 ms | 693–4394 ms |
| Matching | **0–1 ms** | 0–1 ms |
| End-to-end (speech stop → first frame) | ~1340 ms | 896–1793 ms |

## Coverage on the demo sentence

`"Hello, thank you. My name is Mothishwaran."` → 7 tokens

| | count |
|---|---|
| sign | 4 (`hello`, `thank you`, `name`) |
| spell | 1 (`Mothishwaran`) |
| uncovered | 2 (`my`, `is`) |
| **coverage** | **57.1%** |

We report 57.1% plainly. A six-word dictionary covering 57% of a sentence is an honest result;
claiming anything near 100% would be a lie that a single unusual sentence would expose.

## Finding 1 — latency is entirely ASR-bound

Matching costs **~0 ms** against ~826 ms for recognition. Retrieval is effectively free at this
vocabulary size, and a linear scan would stay fine into the thousands of entries. **Any latency
optimisation must target the ASR stage** — optimising the matcher would be wasted effort.

## Finding 2 — `initial_prompt` did not fix the out-of-vocabulary name

Across **six independent runs**, Whisper transcribed *"Mothishwaran"* as **"Mothish"** — every
time, identically, despite being explicitly prompted with the name.

This is a **negative result and we report it as one.** It has two useful consequences:

1. It shows precisely where the error boundary sits: the failure is in **recognition**, not in
   retrieval. The matcher then correctly fingerspells M-O-T-H-I-S — right for what it was given.
2. It is the clearest possible justification for having a fingerspelling fallback at all.

## Finding 3 — the browser audio path silently used its fallback

The front end tries to decode and resample audio to 16 kHz in the browser, and falls back to
uploading the raw recording if that fails. **In every logged run the fallback was used.**

Nothing was broken — resampling to 16 kHz mono still happens, inside
`faster_whisper.decode_audio` via PyAV's `AudioResampler`, server-side.

But it means a claim of *browser-side* resampling would have been **false**. We found this by
noticing every stored upload had a `.webm` extension rather than `.wav`. The results log now
records which path each run used.

> This is worth stating in a viva as a process point: a fallback that works silently will hide
> the fact that the primary path never runs. We only caught it by auditing the artefacts.
""")

# ─────────────────────────────────────────── 14B PHASE 1 RESULTS
import tools.build_notebook_part3b  # noqa: E402,F401  (appends its cells here, in order)

# ─────────────────────────────────────────── 15 LIMITATIONS
md(r"""
---
# § 15 · Limitations — what this system genuinely cannot do

Stated plainly, and volunteered rather than extracted.

| # | Limitation | Why |
|---|---|---|
| 1 | **It is not translation** | Lexical retrieval into a dictionary of isolated signs (6 entries in Phase 0, ~3,850 in Phase 1) |
| 2 | **Word order is English** | ISL has its own grammar; clip order follows the English sentence |
| 3 | **No non-manual markers** | Facial expression, head tilt and mouthing carry grammar in ISL; isolated dictionary clips cannot express sentence-level non-manuals |
| 4 | **No co-articulation** | Real signing blends one sign into the next; hard cuts do not |
| 5 | **Unknown words are dropped** | Reported honestly via coverage rather than hidden |
| 6 | **Fingerspelling is a fallback** | Deaf signers do not fingerspell everything |
| 7 | **No Deaf-user evaluation** | We measured coverage and latency, **not comprehensibility** |
| 8 | **Whisper is a component, not a contribution** | The contribution is the retrieval pipeline and its honest evaluation |
| 9 | **Word-sense ambiguity** | One English word can need different signs (*train* the vehicle vs *train* a person). Ambiguous inflections are left unmapped rather than guessed (§ 14B.4) |
| 10 | **Synonyms reviewed for English, not by a signer** | `data/synonyms.csv` approvals check English meaning; whether the synonym's sign is acceptable ISL needs a Deaf reviewer |
| 11 | **Long "(Explanation)" videos unused** | The sign sits inside continuous signing; `data/trims.csv` waits for someone who knows ISL to mark it (e.g. *how*) |
| 12 | **ASR accuracy measured on Svarah and synthetic speech** | Real-voice scoring is built in (§ 13) but needs more speakers than the two developers |

## What broke first when we scaled from 6 words to ~3,850? (Phase 0 prediction, checked in Phase 1)

**Exact matching.** Coverage would rise, but precision of *meaning* would fall — ISLRTC itself
notes synonyms, homonyms and context-specific signs, so one English word can map to several ISL
signs and exact matching has no way to choose the right one.

That is precisely why Phase 1 moves to sentence embeddings [9] and phrase-level corpora [2].
Notably, **retrieval speed is not the bottleneck** — Finding 1 already showed matching is free.

*Phase 1 check:* the prediction held. Speed stayed at ~0–1 ms; the hard problems were meaning
(14B.4) and which inflections are safe to map. Sentence embeddings turned out to be unsafe at
the single-word level, so Phase 1 used a reviewed lexical resource instead.
""")

# ─────────────────────────────────────────── 16 PENDING
md(r"""
---
# § 16 · Pending work

| Phase | Work | Status |
|---|---|---|
| **1** | Scale the vocabulary; GPU ASR; fine-tune Whisper on Indian English; synonyms with a reject option | **Done** — § 14B. Embeddings tried and rejected for single words (14B.4) |
| **2** | ISL word order (e.g. question words last, verb last); ISLTranslate [2] for phrase-level retrieval | Next — English word order is now the largest linguistic gap |
| **3** | Voice activity detection (Silero) for continuous input | Remove push-to-talk |
| **4** | Evaluation **with Deaf signers**; review of synonyms and explanation-video trims by ISL users; smoother clip transitions | Measure comprehensibility, not just coverage |

## The honest caveat about similarity thresholds

A cosine similarity score says **nothing** about linguistic correctness. It measures distance in an
embedding space trained on **English text** — it is a proxy for the similarity of the English, not
evidence that the retrieved ISL video is correct.

So thresholds must be calibrated against **manually reviewed** examples, and Phase 1 must keep a
reject option: showing nothing is better than confidently showing the wrong sign.

## Interim conclusion

**Phase 0 (Review 1):** a complete speech→ISL retrieval pipeline ran end to end on a laptop CPU
at roughly **1.3 s** median latency, covering **57%** of the demo sentence with a six-entry
vocabulary, using real ISL video recorded by Deaf signers.

**Phase 1:** the same architecture, unchanged in shape, now retrieves from **~4,000** local
dictionary phrases plus **~2,700** fetched from Google Drive on demand (anything else is
fingerspelled), recognises speech in **~0.2 s** on a laptop GPU with a Whisper model fine-tuned on
Indian-accented English (**~13.2 % → 11.3 % WER** on unseen speakers, two runs), and signs about
**two-thirds of the words ISL would sign** in held-out everyday sentences — reporting the rest
honestly as omitted, spelled or uncovered.

The Phase 0 vocabulary was small by design. The architecture — recognise, normalise, retrieve, fall back,
and **count what was missed** — is what the project set out to demonstrate, and it is vocabulary-agnostic.
""")

# ─────────────────────────────────────────── 17 REFERENCES
md(r"""
---
# § 17 · References (IEEE format)

Numbered by order of first citation. Every entry was checked against the publisher's page.

[1] A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey, and I. Sutskever, "Robust speech
recognition via large-scale weak supervision," in *Proc. 40th Int. Conf. Machine Learning
(ICML)*, PMLR vol. 202, 2023, pp. 28492–28518.
https://proceedings.mlr.press/v202/radford23a.html

[2] A. Joshi, S. Agrawal, and A. Modi, "ISLTranslate: Dataset for translating Indian Sign
Language," in *Findings of the Association for Computational Linguistics: ACL 2023*, Toronto,
Canada, 2023. https://aclanthology.org/2023.findings-acl.665/

[3] A. Joshi et al., "iSign: A benchmark for Indian Sign Language processing," in *Findings of the
Association for Computational Linguistics: ACL 2024*, 2024, pp. 10827–10844.
https://aclanthology.org/2024.findings-acl.643/

[4] A. Sridhar, R. G. Ganesan, P. Kumar, and M. Khapra, "INCLUDE: A large scale dataset for Indian
Sign Language recognition," in *Proc. 28th ACM Int. Conf. Multimedia*, 2020, pp. 1366–1375.

[5] N. C. Camgöz, S. Hadfield, O. Koller, H. Ney, and R. Bowden, "Neural sign language
translation," in *Proc. IEEE/CVF Conf. Computer Vision and Pattern Recognition (CVPR)*, 2018,
pp. 7784–7793.
https://openaccess.thecvf.com/content_cvpr_2018/html/Camgoz_Neural_Sign_Language_CVPR_2018_paper.html

[6] N. C. Camgöz, O. Koller, S. Hadfield, and R. Bowden, "Sign language transformers: Joint
end-to-end sign language recognition and translation," in *Proc. IEEE/CVF Conf. Computer Vision
and Pattern Recognition (CVPR)*, 2020, pp. 10023–10033.

[7] B. Saunders, N. C. Camgöz, and R. Bowden, "Progressive transformers for end-to-end sign
language production," in *Proc. European Conf. Computer Vision (ECCV)*, 2020, pp. 687–705.
https://link.springer.com/chapter/10.1007/978-3-030-58621-8_40

[8] P. Kapoor, R. Mukhopadhyay, S. B. Hegde, V. Namboodiri, and C. V. Jawahar, "Towards automatic
speech to sign language generation," in *Proc. Interspeech 2021*, 2021.
https://www.isca-archive.org/interspeech_2021/kapoor21_interspeech.html

[9] N. Reimers and I. Gurevych, "Sentence-BERT: Sentence embeddings using Siamese BERT-networks,"
in *Proc. 2019 Conf. Empirical Methods in Natural Language Processing (EMNLP-IJCNLP)*, Hong Kong,
2019, pp. 3982–3992. https://aclanthology.org/D19-1410/

[10] L. C. Quandt, A. Willis, M. Schwenk, K. Weeks, and R. Ferster, "Attitudes toward signing
avatars vary depending on hearing status, age of signed language acquisition, and avatar type,"
*Frontiers in Psychology*, vol. 13, art. 730917, 2022.
https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2022.730917/full

[12] T. Javed, S. Joshi, V. Nagarajan, S. Sundaresan, J. Nawale, A. Raman, K. Bhogale, P. Kumar,
and M. M. Khapra, "Svarah: Evaluating English ASR systems on Indian accents," in *Proc.
Interspeech 2023*, 2023. https://arxiv.org/abs/2305.15760

[13] G. A. Miller, "WordNet: A lexical database for English," *Communications of the ACM*,
vol. 38, no. 11, pp. 39–41, 1995.

*[12]–[13] were added in Phase 1.*

**Additional source consulted**

[11] M. Kipp, A. Heloir, and Q. Nguyen, "Assessing the deaf user perspective on sign language
avatars," in *Proc. 13th Int. ACM SIGACCESS Conf. Computers and Accessibility (ASSETS)*, 2011.
https://dl.acm.org/doi/10.1145/2049536.2049557

**Data sources**

- ISLRTC Indian Sign Language Dictionary — https://islrtc.nic.in/isl-dictionary/
- Government of India Open Data, ISL Dictionary — https://data.gov.in/catalog/indian-sign-language-dictionary
- ISL alphabet clips, FDMSE / RKMVERI Coimbatore — https://indiansignlanguage.org/category/alphabets/
- ISL Dictionary videos (Google Drive mirror used in Phase 1) — https://drive.google.com/drive/folders/1U-Pr4r1-cupgNOOq9NH_uTsQnPSVEKco
- Svarah (AI4Bharat, CC BY 4.0) — https://huggingface.co/datasets/ai4bharat/Svarah
- Word frequency list (google-10000-english) — https://github.com/first20hours/google-10000-english

---

*End of notebook.*
""")
