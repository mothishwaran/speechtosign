"""Cells: § 14B Phase 1 results - dataset scale, matching, fine-tuned ASR.

Imported from build_notebook_part3.py right after § 14, so the Phase 0
results (Review 1) stay in the notebook unchanged, as the record they are.
Every number below is recomputed from committed files when the notebook runs.
"""

from tools.build_notebook_part1 import CELLS


def md(t):
    CELLS.append(("markdown", t.strip("\n")))


def code(t):
    CELLS.append(("code", t.strip("\n")))


md(r"""
---
# § 14B · Phase 1 results (October 2026)

§ 14 is the Phase 0 record presented at Review 1 and is left exactly as it was. This section
reports what changed afterwards and what it measured.

| Area | Phase 0 (Review 1) | Phase 1 |
|---|---|---|
| Vocabulary | 6 phrases | **~3,850 phrases** from the full ISLRTC dictionary |
| Speech recognition | `base.en`, CPU int8, ~826 ms | `base.en` **fine-tuned on Indian-accented English**, GPU, ~150–200 ms |
| Matching | exact longest n-gram | + inflected forms, reviewed synonyms, ISL-omitted words |
| Unknown words | dropped | dropped by default; fingerspelling switch in the UI |
| Evaluation | 6 utterances | 20 everyday + 20 **held-out** sentences, 16 unseen Svarah speakers, real-voice scoring per speaker |
""")

# ─────────────────────────────────────────── dataset scale
md(r"""
## 14B.1 · Dictionary scale

The ISLRTC dictionary Drive folder holds **15,462 videos (~250 GB)**. The local copy was built
from its zip parts and topped up word-by-word through the Google Drive API
(`tools/drive_sync.py`) rather than downloading everything. `tools/build_manifest.py` turns file
names into phrases (`I_Don_t_Know.mp4` → *i don't know*, `Rupee, money.mp4` → *rupee* and
*money*), keeps one clip per phrase, transcodes the few that browsers cannot play, and drops
clips longer than 30 s — those are lectures about a word, not the sign for it.
""")

code(r"""
import csv
from collections import Counter

rows = list(csv.DictReader(open("data/manifest.csv", encoding="utf-8")))
kinds = Counter("alias" if r["notes"].startswith("alias of") else
                "transcoded" if "transcoded" in r["notes"] else
                "trimmed" if "trimmed" in r["notes"] else "dictionary clip" for r in rows)
syn = list(csv.DictReader(open("data/synonyms.csv", encoding="utf-8")))
forms = sum(r["kind"] == "form" and r["review"] != "reject" for r in syn)
approved = sum(r["kind"] == "synonym" and r["review"] == "ok" for r in syn)
proposed = sum(r["kind"] == "synonym" for r in syn)

print(f"manifest phrases     : {len(rows)}")
for k, v in kinds.most_common():
    print(f"   {k:<18}: {v}")
print(f"phrase lengths       : {dict(sorted(Counter(int(r['ngram_len']) for r in rows).items()))}")
print(f"extra spoken words   : {forms} inflected forms + {approved} reviewed synonyms "
      f"(of {proposed} proposed)")
""")

# ─────────────────────────────────────────── matching
md(r"""
## 14B.2 · How a word becomes a sign

Each word goes through these steps in order; the first that applies wins.

| Step | Type shown | Example | Counted as |
|---|---|---|---|
| 1. longest dictionary phrase | **sign** | *thank you*, *i don't know* | covered |
| 2. capitalised mid-sentence word | **spell** (name) | *Mothishwaran* | not covered |
| 3. word ISL does not sign | **omitted** | *is, are, the, to, of* | excluded from ISL-signed coverage |
| 4. inflected form of a dictionary word | **sign** | *went* → go, *children* → child | covered |
| 5. reviewed synonym | **similar** | *physician* → doctor | reported separately |
| 6. fingerspell switch (off by default) | **spell** (unknown) | *need* → N-E-E-D | not covered |
| 7. otherwise | **uncovered** | | not covered |

Three coverage figures are reported: **all words** (the Phase 0 definition, kept for
comparability), **words ISL signs** (step 3 removed from the denominator), and the same
**plus synonyms**.

**Step 3 is a linguistic correction, not a trick.** ISL, like most sign languages, has no
articles and no copula: *"Where is the hospital?"* is signed roughly HOSPITAL WHERE. Counting
*is* and *the* as failures understated what the dictionary covers.
""")

code(r"""
from src import matcher
matcher._manifest = matcher._max_ngram = matcher._synonyms = None   # reload current data

def show(text, **kw):
    m = matcher.match(text, **kw)
    mark = {"sign": "[{}]", "similar": "{{{}}}", "spell": "<{}>", "omitted": "({})", "uncovered": "{}"}
    print(" ".join(mark[p["type"]].format(p["token"] + ("~" + p["means"] if p["type"] == "similar" else ""))
                   for p in m["plan"]))
    print(f"   all words {m['coverage']*100:.0f}% | ISL-signed {m['content_coverage']*100:.0f}% "
          f"| +synonyms {m['content_coverage_with_similar']*100:.0f}%\n")

show("Hello, thank you. My name is Mothishwaran.")
show("The physician told me to rest for a week.")
show("We went to the market yesterday.")
show("I need a telephone to call my friends.", spell_unknown=True)
""")

# ─────────────────────────────────────────── coverage results
md(r"""
## 14B.3 · Coverage on everyday sentences

Two sets of 20 sentences. The **everyday** set was written early and has been looked at
throughout development; the **held-out** set was written after all matching work was finished
and was never used to tune anything — **its numbers are the honest ones to quote.**
The spoken columns come from Windows text-to-speech sent through the real `/translate`
endpoint (`tools/eval_dataset.py --tts`).
""")

code(r"""
import csv, statistics
import matplotlib.pyplot as plt
from src import matcher

def text_cov(path):
    sents = [l.strip() for l in open(path, encoding="utf-8") if l.strip()]
    ms = [matcher.match(s) for s in sents]
    return [100 * statistics.mean(m[k] for m in ms)
            for k in ("coverage", "content_coverage", "content_coverage_with_similar")]

sets = {"everyday": ("eval/test_sentences.txt", "eval/dataset_eval.csv"),
        "held-out": ("eval/test_sentences_heldout.txt", "eval/dataset_eval_heldout.csv")}
results = {}
for name, (txt, spoken_csv) in sets.items():
    results[name] = text_cov(txt)
    sp = list(csv.DictReader(open(spoken_csv, encoding="utf-8")))
    wer = 100 * statistics.mean(float(r["wer"]) for r in sp) if sp and "wer" in sp[0] else float("nan")
    spc = 100 * statistics.mean(float(r["speech_coverage"]) for r in sp) if sp and "speech_coverage" in sp[0] else float("nan")
    a, b, c = results[name]
    print(f"{name:9}  all words {a:5.1f}% | ISL-signed {b:5.1f}% | +synonyms {c:5.1f}%"
          f"   || spoken: coverage {spc:5.1f}%, WER {wer:4.1f}%")

labels = ["all words", "ISL-signed", "+ synonyms"]
fig, ax = plt.subplots(figsize=(7, 3.2))
w = 0.38
for i, (name, vals) in enumerate(results.items()):
    xs = [x + (i - 0.5) * w for x in range(3)]
    bars = ax.bar(xs, vals, w, label=name)
    ax.bar_label(bars, fmt="%.0f%%", fontsize=8)
ax.set_xticks(range(3), labels)
ax.set_ylim(0, 110)
ax.set_yticks(range(0, 101, 20))
ax.set_ylabel("coverage (%)")
ax.set_title("Sign coverage on 20 + 20 everyday sentences")
ax.legend(frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.0))
plt.tight_layout()
plt.show()
""")

md(r"""
## 14B.4 · A negative result: embedding similarity is unsafe for single words

The plan for Phase 1 was sentence embeddings [9] to catch paraphrases. Before wiring it in, we
checked it on 30 true synonym pairs and 30 *related but different* pairs, with MiniLM
(`all-MiniLM-L6-v2`).

| Threshold | synonyms accepted | **wrong pairs accepted** | examples of wrong pairs |
|---|---|---|---|
| 0.70 | 18 / 30 | 8 / 30 | buy → sell, father → mother, red → blue |
| 0.80 | 12 / 30 | 2 / 30 | Monday → Tuesday, husband → wife |
| 0.85 | 7 / 30 | 2 / 30 | Monday → Tuesday, husband → wife (both 0.87) |
| WordNet [13] (used) | 11 / 30 | **0 / 30** | — |

No threshold separates the two: *husband* and *wife* sit closer together than most real
synonyms. Shown as a sign, that is not "approximately right" — it is the wrong word, delivered
confidently. So matching uses WordNet [13] instead, a hand-built lexical database: inflected
forms are accepted automatically only when the part of speech is unambiguous (≥ 70 % of the
word's corpus uses), and synonyms are only **proposals** until a reviewer marks them `ok` in
`data/synonyms.csv`. A first, looser WordNet pass also proposed *million → billion* and
*decade → ten*; the review step exists because of exactly those.
""")

# ─────────────────────────────────────────── fine-tuning
md(r"""
## 14B.5 · Fine-tuning Whisper on Indian-accented English

**Data.** Svarah [12] (AI4Bharat, CC BY 4.0): 6,656 utterances, 9.6 h, 117 speakers from across
India. It ships as a single test split, so we re-split it **by speaker**. Svarah has no speaker
column, and the audio file names are *not* speaker ids (≈2,900 distinct prefixes for 117
speakers) — splitting on them would have put the same voices in train and test and inflated the
result. Speakers are grouped by their full demographic profile instead, which can never split
one speaker across two sets.

**Training.** Full fine-tune of `base.en` (the model the app runs), 3 epochs, batch 16, AdamW,
lr 1e-5, fp16, one RTX 4050 laptop GPU (6 GB), 69 minutes. Checkpoints every 200 steps are
fully resumable (model, optimiser, schedule, step and RNG state); the best dev checkpoint is
exported to CTranslate2 int8 (76 MB) and committed, so a teammate gets it with `git pull`.
""")

code(r"""
import csv
import matplotlib.pyplot as plt
from collections import defaultdict

split = list(csv.DictReader(open("eval/svarah_speaker_split.csv", encoding="utf-8")))
agg = defaultdict(lambda: [0, 0, 0.0])
for r in split:
    a = agg[r["split"]]; a[0] += 1; a[1] += int(r["utterances"]); a[2] += float(r["hours"])
for s in ("train", "dev", "test"):
    print(f"{s:5}: {agg[s][0]:3} speaker groups  {agg[s][1]:5} utterances  {agg[s][2]:.2f} h")

log = list(csv.DictReader(open("eval/train_log_base_en_svarah.csv", encoding="utf-8")))
steps = [int(r["step"]) for r in log if r["dev_wer"]]
dev = [100 * float(r["dev_wer"]) for r in log if r["dev_wer"]]
loss_steps = [int(r["step"]) for r in log if r["train_loss"]]
loss = [float(r["train_loss"]) for r in log if r["train_loss"]]

fig, ax1 = plt.subplots(figsize=(7, 3.2))
ax1.plot(steps, dev, "o-", label="dev WER")
best = min(range(len(dev)), key=dev.__getitem__)
ax1.annotate(f"best {dev[best]:.2f}% (exported)", (steps[best], dev[best]),
             textcoords="offset points", xytext=(0, -30), ha="center", fontsize=8,
             arrowprops=dict(arrowstyle="-", lw=0.6))
ax1.set_ylim(min(dev) - 0.9, max(dev) + 0.3)
ax1.set_xlabel("training step"); ax1.set_ylabel("dev WER (%)")
ax2 = ax1.twinx()
ax2.plot(loss_steps, loss, "s--", color="tab:gray", alpha=0.7, label="train loss")
ax2.set_ylabel("train loss")
ax1.set_title("Fine-tuning curve (dev = 15 speakers not in training)")
fig.legend(loc="upper right", bbox_to_anchor=(0.88, 0.85), frameon=False, fontsize=8)
plt.tight_layout(); plt.show()
""")

code(r"""
import csv, random
from collections import defaultdict
import matplotlib.pyplot as plt
import jiwer
from tools.train.metrics import normalize

hyps = list(csv.DictReader(open("eval/asr_svarah_test_hyps.csv", encoding="utf-8")))
models = list(dict.fromkeys(r["model"] for r in hyps))
stock, tuned = models[0], models[1]

def errs(ref, hyp):
    r, h = normalize(ref), normalize(hyp)
    if not r.strip():
        return 0, 0
    o = jiwer.process_words(r, h)
    return o.substitutions + o.deletions + o.insertions, len(r.split())

E = {m: [errs(r["reference"], r["hypothesis"]) for r in hyps if r["model"] == m] for m in models}
spk = [r["speaker"] for r in hyps if r["model"] == stock]
for m in models:
    print(f"{m:26} test WER {sum(e for e, _ in E[m]) / sum(n for _, n in E[m]) * 100:.2f}%")

per = defaultdict(lambda: [0, 0, 0])
for i, s in enumerate(spk):
    per[s][0] += E[stock][i][0]; per[s][1] += E[tuned][i][0]; per[s][2] += E[stock][i][1]
pairs = sorted((v[0] / v[2] * 100, v[1] / v[2] * 100) for v in per.values())
print(f"speakers improved: {sum(b < a for a, b in pairs)}/{len(pairs)}")

random.seed(0)
n, wins = len(spk), 0
for _ in range(2000):
    idx = [random.randrange(n) for _ in range(n)]
    wins += sum(E[tuned][i][0] for i in idx) < sum(E[stock][i][0] for i in idx)
print(f"paired bootstrap: fine-tuned better in {wins}/2000 resamples")

fig, ax = plt.subplots(figsize=(7, 3.2))
xs = range(len(pairs))
ax.bar([x - 0.2 for x in xs], [a for a, _ in pairs], 0.4, label=f"stock {stock}")
ax.bar([x + 0.2 for x in xs], [b for _, b in pairs], 0.4, label="fine-tuned")
ax.set_xticks(list(xs), [str(i + 1) for i in xs])
ax.set_xlabel("held-out test speaker (sorted by stock WER)"); ax.set_ylabel("WER (%)")
ax.set_title("Per-speaker WER on 16 unseen Indian-accented speakers")
ax.legend(frameon=False); plt.tight_layout(); plt.show()
""")

md(r"""
## 14B.6 · Latency

Measured on one laptop (RTX 4050, 6 GB); the same sentence (`eval/sample.wav`, 4.4 s).

| Configuration | ASR time per sentence |
|---|---|
| CPU int8, on battery | ~3,100 ms |
| CPU int8, plugged in | ~1,600 ms |
| **GPU fp16 (current)** | **~150–250 ms** |

`src/asr.py` uses the GPU when one is present and falls back to CPU otherwise, so the same code
runs on a teammate's laptop without an NVIDIA card. Matching remains ~0–1 ms against a
3,855-phrase dictionary — Finding 1 (latency is entirely ASR-bound) still holds at 600× the
vocabulary.

## Phase 1 findings

**Finding 4 — fine-tuning helps the hardest accents most.** Test WER fell from ~13.2 % to 11.3 % (13.12 → 11.30 and 13.32 → 11.27 in two runs; the ±0.2 spread comes from Whisper's random temperature fallback, which the app also uses)
on speakers never seen in training; 14 of 16 improved, and the largest gains were on the
speakers the stock model handled worst.

**Finding 5 — for single words, embedding similarity is not meaning.** See 14B.4. The safe
alternative was a reviewed lexical resource, and the review caught real errors.

**Finding 6 — counting ISL-omitted words as failures understated coverage.** On the held-out
set, ~12 points of the gap between "all words" and "ISL-signed" coverage are words ISL does
not sign at all.

**Finding 7 — a data-split mistake that would have inflated the headline.** Svarah's file
names look like speaker ids but are not. The first split put the same voices in train and test;
it was caught by counting distinct ids (≈2,900 vs 117 speakers) before training.

**Update to Finding 3.** On the second development laptop the browser's 16 kHz WAV path ran
in every recorded session, so the earlier all-fallback runs were specific to that machine. The
reason for any future fallback is now written to the results log
(`encode_error=` in the note column) instead of being silent.
""")
