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
| Vocabulary | 6 phrases | **~4,000 phrases** on disk + **~2,700 more fetched from Google Drive on demand** |
| Speech recognition | `base.en`, CPU int8, ~826 ms | `base.en` **fine-tuned on Indian-accented English**, GPU, ~150–200 ms |
| Matching | exact longest n-gram | + numbers, inflected forms, reviewed synonyms, ISL-omitted words |
| Unknown words | dropped | **fetched from Drive if it has the sign, otherwise fingerspelled** |
| Speech processing | resampling only | live waveform / spectrogram / pitch, spectral subtraction study, pitch question study |
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

Each word goes through these steps in order; the first that applies wins. Defaults are the
app's settings as demonstrated; the switches in the page change them.

| Step | Type shown | Example | Counted as |
|---|---|---|---|
| 1. longest dictionary phrase **on this laptop** | **sign** | *thank you*, *i don't know* | covered |
| 2. else the same phrase **on Google Drive** — fetched on demand | **sign** ☁ | *parrot*, *elephant* | covered |
| 3. a number | **sign** (several clips) | *25* → TWENTY FIVE | covered |
| 4. capitalised mid-sentence word | **spell** (name) | *Mothishwaran* | not covered |
| 5. word ISL does not sign | **omitted** | *is, are, the, to, of* | excluded from ISL-signed coverage |
| 6. inflected form of a dictionary word | **sign** | *went* → go, *children* → child | covered |
| 7. reviewed synonym | **similar** | *physician* → doctor | reported separately |
| 8. more general sign (switch, **off** by default) | **related** | *puppy* → dog | reported separately |
| 9. otherwise **fingerspell** (switch, **on** by default) | **spell** (unknown) | *about* → A-B-O-U-T | not covered |
| 10. a single letter that would read as the alphabet sign | **uncovered** | *I* | not covered |

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
matcher._manifest = matcher._max_ngram = matcher._synonyms = matcher._remote = None

def text_cov(path):
    sents = [l.strip() for l in open(path, encoding="utf-8") if l.strip()]
    local = [matcher.match(s, use_drive=False, use_related=False) for s in sents]
    full = [matcher.match(s) for s in sents]                 # Drive on demand + related
    pct = lambda ms, k: 100 * statistics.mean(m[k] for m in ms)
    return [pct(local, "coverage"), pct(local, "content_coverage"),
            pct(full, "content_coverage"), pct(full, "content_coverage_with_similar"),
            pct(full, "content_coverage_with_related")]

labels = ["all words\n(local)", "ISL-signed\n(local)", "+ Drive on\ndemand", "+ synonyms", "+ related"]
sets = {"everyday": "eval/test_sentences.txt", "held-out": "eval/test_sentences_heldout.txt"}
results = {name: text_cov(path) for name, path in sets.items()}
for name, vals in results.items():
    print(f"{name:9} " + " | ".join(f"{l.replace(chr(10), ' ')} {v:5.1f}%" for l, v in zip(labels, vals)))

fig, ax = plt.subplots(figsize=(8, 3.4))
w = 0.38
for i, (name, vals) in enumerate(results.items()):
    xs = [x + (i - 0.5) * w for x in range(len(labels))]
    bars = ax.bar(xs, vals, w, label=name)
    ax.bar_label(bars, fmt="%.0f%%", fontsize=7)
ax.set_xticks(range(len(labels)), labels, fontsize=8)
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
## 14B.6 · The whole dictionary on demand, and the closest related sign

**Drive on demand.** The ISLRTC Drive holds ~15,000 videos (~250 GB); downloading all of
it is impractical. `data/drive_manifest.csv` catalogues the signs that are on Drive but not
on this machine. When a sentence needs one, the server downloads only that clip, checks it
(≤ 30 s, else it is a lecture and is rejected for good), transcodes it if a browser cannot
play it, and caches it. The first use costs a few seconds; after that it is local.

**Related sign.** When a word has no sign, no reviewed synonym and nothing on Drive, the
matcher can fall back to the nearest **more general** word that has a sign — its WordNet
parent: *puppy → dog*, *cottage → house*, *champagne → wine*. Only generalisations are used,
because they stay true (a puppy *is* a dog); "sibling" words were tested and rejected because
they are different things (dog/cat, husband/wife, man/woman). The word's most frequent
attested sense is used (the first-listed sense gave *chess → grass*), vague parents
(*quality*, *amount*, *thing* …) are excluded, and every mapping can be vetoed in
`data/synonyms.csv` — a review pass rejected 204 of 780 generated pairs. These signs are
shown as **related**, labelled with the substitute word, and counted separately.
""")

code(r"""
import csv
drive = list(csv.DictReader(open("data/drive_manifest.csv", encoding="utf-8")))
syn = list(csv.DictReader(open("data/synonyms.csv", encoding="utf-8")))
rel = [r for r in syn if r["kind"] == "related"]
print(f"signs fetchable from Drive on demand : {len(drive)}")
print(f"related (generalisation) pairs        : {len(rel)} generated, "
      f"{sum(r['review'] == 'reject' for r in rel)} rejected in review, "
      f"{sum(r['review'] != 'reject' for r in rel)} in use")
from src import matcher
for t in ["My puppy sleeps in the cottage.", "She drinks champagne at the carnival."]:
    m = matcher.match(t, use_drive=False)
    print("  " + " ".join(f"{p['token']}->{p['means']}" if p.get("means") else p["token"]
                          for p in m["plan"] if p["type"] in ("sign", "related", "similar")))
""")

md(r"""
## 14B.7 · Speech analysis shown live in the app

While you speak, the page computes and draws the waveform, a spectrogram and the pitch (F0)
track, with short-time energy, zero-crossing rate and a voiced / unvoiced / silent decision.
Pitch uses our own normalised autocorrelation: for each 2048-sample frame, the lag in the
70–400 Hz range where the frame best matches a shifted copy of itself is the period. Because
multiples of the period score almost as high, the shortest lag within 10 % of the best peak is
taken — without that guard a 330 Hz voice was read as 82.5 Hz (a two-octave error) in testing.

The cell below runs **the same algorithm** in Python on the demo recording. The few isolated
high points at word onsets are a known autocorrelation artefact at voicing transitions; they
are left visible rather than smoothed away.
""")

code(r"""
import wave
import numpy as np
import matplotlib.pyplot as plt

with wave.open("eval/sample.wav") as w:
    sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768

FRAME, HOP, F0_MIN, F0_MAX, VOICED_R, SILENCE_DB = 1024, 160, 70, 400, 0.5, -50

def pitch(frame):
    lags = np.arange(int(sr / F0_MAX), min(int(sr / F0_MIN), len(frame) // 2) + 1)
    r = np.array([np.dot(frame[:-k], frame[k:]) /
                  (np.sqrt(np.dot(frame[:-k], frame[:-k]) * np.dot(frame[k:], frame[k:])) or 1)
                  for k in lags])
    best = r.max()
    if best < VOICED_R:
        return np.nan
    for i in range(1, len(r) - 1):            # shortest local peak within 10% of the best
        if r[i] >= 0.9 * best and r[i] >= r[i - 1] and r[i] >= r[i + 1]:
            return sr / lags[i]
    return np.nan

times, f0, energy, zcr = [], [], [], []
for start in range(0, len(x) - FRAME, HOP):
    fr = x[start:start + FRAME]
    e_db = 10 * np.log10(np.mean(fr ** 2) + 1e-12)
    times.append(start / sr); energy.append(e_db)
    zcr.append(np.mean(np.abs(np.diff(np.sign(fr))) > 0) * sr)
    f0.append(pitch(fr) if e_db > SILENCE_DB else np.nan)
times, f0 = np.array(times), np.array(f0)

fig, axes = plt.subplots(3, 1, figsize=(8, 6), sharex=True)
axes[0].plot(np.arange(len(x)) / sr, x, lw=0.4)
axes[0].set_ylabel("amplitude"); axes[0].set_title("eval/sample.wav — waveform, spectrogram, pitch")
with np.errstate(divide="ignore"):          # silent frames have zero power
    axes[1].specgram(x, NFFT=512, Fs=sr, noverlap=352, cmap="magma", vmin=-120)
axes[1].set_facecolor("black")              # zero-power (silent) frames
axes[1].set_ylim(0, 5000); axes[1].set_ylabel("Hz")
axes[2].plot(times, f0, ".", ms=3, color="tab:orange")
axes[2].set_ylim(F0_MIN, F0_MAX); axes[2].set_ylabel("F0 (Hz)"); axes[2].set_xlabel("time (s)")
plt.tight_layout(); plt.show()

voiced = ~np.isnan(f0)
print(f"frames {len(f0)} | voiced {voiced.mean() * 100:.0f}% | median F0 {np.nanmedian(f0):.0f} Hz | "
      f"F0 range {np.nanpercentile(f0, 5):.0f}-{np.nanpercentile(f0, 95):.0f} Hz")
print(f"mean ZCR voiced {np.mean(np.array(zcr)[voiced]):.0f}/s vs unvoiced-but-loud "
      f"{np.mean(np.array(zcr)[~voiced & (np.array(energy) > SILENCE_DB)]):.0f}/s")
""")

md(r"""
## 14B.8 · Noise robustness and spectral subtraction

**Spectral subtraction** (`src/denoise.py`, our own numpy implementation of Boll 1979 with
Berouti-style over-subtraction): STFT with 32 ms Hann frames and 8 ms hop; the noise power
spectrum is the mean of the quietest 10 % of frames; clean power = |Y|² − 2·N, floored at
0.02·|Y|² to limit musical noise; inverse STFT with the noisy phase. With subtraction switched
off it reconstructs the input exactly (147 dB SNR), and it runs in ~22 ms for 4 s of audio.

**Study** (`tools/noise_study.py`): 200 utterances from the 16 unseen Svarah test speakers,
mixed with **white** noise (flat, stationary — a fan or hiss) or **babble** (four other speakers
at once — a classroom), at 20 / 10 / 5 / 0 dB SNR; stock vs fine-tuned Whisper, each with and
without spectral subtraction; decoded exactly as the app does.
""")

code(r"""
import csv
import matplotlib.pyplot as plt

rows = list(csv.DictReader(open("eval/noise_study.csv", encoding="utf-8")))
snr = list(csv.DictReader(open("eval/noise_study_snr.csv", encoding="utf-8")))
print("signal-to-noise ratio before -> after spectral subtraction (dB):")
for r in snr:
    print(f"  {r['noise']:6} {r['snr_in']:>3} dB -> {float(r['snr_denoised']):5.1f} dB "
          f"({float(r['snr_denoised']) - float(r['snr_noisy']):+.1f})")

def wer(model, noise, s, d):
    for r in rows:
        if r["model"] == model and r["noise"] == noise and r["snr_db"] == s and r["denoise"] == str(d):
            return 100 * float(r["wer"])
    return float("nan")

levels = ["20", "10", "5", "0"]
fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
styles = {("base.en", 0): ("tab:blue", "-", "stock"),
          ("base.en", 1): ("tab:blue", "--", "stock + spectral subtraction"),
          ("whisper-base-en-svarah", 0): ("tab:orange", "-", "fine-tuned"),
          ("whisper-base-en-svarah", 1): ("tab:orange", "--", "fine-tuned + spectral subtraction")}
for ax, noise in zip(axes, ["white", "babble"]):
    for (model, d), (c, ls, label) in styles.items():
        xs = ["clean"] + [f"{l} dB" for l in levels]
        ys = [wer(model, "clean", "", d)] + [wer(model, noise, l, d) for l in levels]
        ax.plot(xs, ys, ls, color=c, marker="o", ms=4, label=label)
    ax.set_title(f"{noise} noise"); ax.set_xlabel("SNR")
    ax.grid(alpha=0.3)
axes[0].set_ylabel("WER (%)")
axes[1].legend(fontsize=7, frameon=False, handlelength=3.5)   # long enough to show dashes
fig.suptitle("WER vs noise on 200 utterances from unseen Indian-accented speakers", fontsize=10)
plt.tight_layout(); plt.show()

print(f"\n{'condition':<18}{'stock':>8}{'+SS':>8}{'tuned':>8}{'+SS':>8}")
for noise in ["clean", "white", "babble"]:
    for l in ([""] if noise == "clean" else levels):
        cells = [wer(m, noise, l, d) for m in ("base.en", "whisper-base-en-svarah") for d in (0, 1)]
        print(f"{noise + (' ' + l + ' dB' if l else ''):<18}" + "".join(f"{c:7.1f}%" for c in cells))
""")

md(r"""
## 14B.9 · Questions: pitch versus word order, and ISL word order

**Can intonation tell a question from a statement?** `src/prosody.py` measures the final
pitch movement — median F0 of the last 300 ms of voiced speech against the rest, in semitones
(so low and high voices compare fairly) — with the same autocorrelation tracker. On Svarah's
387 spoken questions and 387 statements (`tools/question_study.py`, threshold chosen on train
speakers only, results on unseen speakers):
""")

code(r"""
import json, csv
from src import matcher, isl_order

q = json.load(open("eval/question_threshold.json"))
print(f"median final pitch movement: yes/no {q['median_rise_st']['yesno']:+.1f} st | "
      f"wh {q['median_rise_st']['wh']:+.1f} st | statements {q['median_rise_st']['statement']:+.1f} st")
h = q["heldout_dev_test"]
print(f"pitch alone (threshold {q['threshold_st']:+.2f} st, unseen speakers): balanced accuracy "
      f"{h['balanced_acc']*100:.1f}% (yes/no recall {h['yesno_recall']*100:.0f}%, "
      f"statements kept {h['statement_specificity']*100:.0f}%)")

rows = [r for r in csv.DictReader(open("eval/question_study.csv", encoding="utf-8")) if r["split"] != "train"]
def detected(t):
    return isl_order.detect_question(t, matcher.match(t, use_drive=False)["plan"])["type"] is not None
qs = [r for r in rows if r["kind"] != "statement"]; st = [r for r in rows if r["kind"] == "statement"]
for label, strip in [('word order + "?"', False), ('word order, "?" removed', True)]:
    f = lambda r: detected(r["text"].rstrip("?. ") if strip else r["text"])
    print(f"app detector, {label:24}: questions {sum(map(f, qs))}/{len(qs)}, "
          f"statements wrongly flagged {sum(map(f, st))}/{len(st)}")
""")

md(r"""
**Finding 9 — in read Indian English, yes/no questions do not rise; they fall less.** Median
final movement is about −0.3 semitones for yes/no questions against about −2.2 for statements
and −2.6 for wh-questions. Pitch alone separates them only modestly (≈ 66 % balanced accuracy),
and adding it to word-order cues mainly added false alarms on the training speakers. So the app
decides with word order (question word first, verb first, or "?") and **reports** the pitch
movement as evidence rather than letting it decide.

**ISL word order** (`src/isl_order.py`) then applies three low-risk rules inside each
sentence: time expressions first, negation last, a sentence-initial question word last
(only when it really asks — "Where **is** …?", not "When I was young …"). Full
verb-final order is not attempted: without reliable verb/object detection a wrong reorder is
worse than English order. A yes/no question is marked in ISL by raised eyebrows — a facial
marker isolated dictionary clips cannot show — so the UI states it instead.
""")

code(r"""
from src import matcher, isl_order
for t in ["Where is the hospital?", "I go to school tomorrow.", "I never eat rice.",
          "Can you help me", "I am 25 years old. Meet me at 7:30."]:
    m = matcher.match(t, use_drive=False)
    order, rules = isl_order.reorder(m["plan"])
    qd = isl_order.detect_question(t, m["plan"])
    print(f"{t:38} -> {isl_order.gloss(m['plan'], order):34} {('[' + qd['type'] + '-question]') if qd['type'] else ''}")
    if rules:
        print(f"{'':41}{'; '.join(rules)}")
""")

md(r"""
**Numbers** are signed as they are read: *25* → TWENTY FIVE, *2026* → TWO THOUSAND TWENTY
SIX, *7:30* → SEVEN THIRTY. The dictionary has no sign for forty, eighty or ninety, so a
number needing one is signed digit by digit (*45* → FOUR FIVE), which ISL signers also do.
""")

md(r"""
## 14B.10 · Fixes and findings from live testing

The last round of changes came from using the app with real speech, which exposed problems
that the automated tests had not.

**Fingerspelling was unreadably fast — a timestamp bug.** Every alphabet clip held 45 frames
(1.5 s of signing) but was stamped as lasting 0.03 s, so the browser flashed each letter past.
The cause was the letter-cutting tool letting the encoder assign timestamps (`pts=None`); the
26 clips were re-timed to 30 fps and the tool fixed. Fingerspelling now defaults to 1.5× speed
(about one second per letter), adjustable in the page. The browser had also cached the broken
clips, so the server now sends `Cache-Control: no-cache` for clips (an unchanged file costs
only a 304 reply).

**Words are never silently dropped.** The default became: sign on this laptop → else fetch it
from Google Drive → else fingerspell it. "How about you, my boy?" plays
H-O-W A-B-O-U-T YOU MY BOY — *how* and *about* exist nowhere on the 15,462-file Drive except as
long explanation videos. Substituting a more general sign (*puppy* → dog) and ISL reordering
stay available as switches but are off by default, because both change what the listener
said.

**Very short phrases defeat every model.** A recorded "cricket match" (2.9 s) came out as
"Trickier to match" (fine-tuned), "To the cat match" (stock) and "Couldn't get the match"
(the 3× larger `small.en`). With no surrounding words the decoder has no context; in a full
sentence ("I play cricket and hockey") the word was recognised. The page now has a
**correction box**: if a word is misheard, the user types the right sentence and signs it with
the identical pipeline — logged as "typed", so it never counts as an ASR result.
""")

code(r"""
import json
r = json.load(open("eval/asr_two_model_selection.json"))
w = r["wer"]
print(f"two-model selection on {r['utterances']} test utterances ({r['speakers']} unseen speakers):")
print(f"  fine-tuned alone              {w['fine_tuned_alone']*100:.2f}%")
print(f"  stock alone                   {w['stock_alone']*100:.2f}%")
print(f"  keep the more confident one   {w['pick_confident_margin_0.0']*100:.2f}%  "
      f"(stock chosen {r['stock_chosen']['margin_0.0']} times)")
print("decision:", r["decision"])
""")

md(r"""
**Finding 12 — combining two models did not help.** Running stock and fine-tuned Whisper and
keeping the transcript with the higher confidence (average log-probability) gave 11.25 % WER
against 11.30 % for the fine-tuned model alone, at twice the GPU time, so it was not adopted.
The fine-tuned model is wrong on some words the stock model gets right (*chicken* for
*cricket*), but per-utterance confidence does not identify those cases reliably.
""")

md(r"""
## 14B.11 · Latency

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

**Finding 10 — spectral subtraction raises SNR but does not help Whisper.** It improves SNR
by +3.7 to +7 dB on white noise but only +0.4 to +1 dB on babble (it assumes the noise
spectrum is steady — true of a fan, false of people talking). Yet WER got slightly *worse* in 15
of 18 noisy/clean conditions (e.g. fine-tuned, clean 11.0 % → 11.9 %; white 5 dB 34.5 % →
36.5 %). Whisper was trained on noisy audio and copes with noise better than with the "musical
noise" artefacts subtraction leaves behind — a known result for neural ASR. The switch
therefore stays off by default; the classic method is kept as a measured, explained baseline.

**Finding 11 — fine-tuning on accented speech also made Whisper more robust to noise.** The
fine-tuned model beats stock Whisper at every white-noise level (5 dB: 44.9 % → 34.5 %; 0 dB:
67.7 % → 55.6 %) and on babble down to 5 dB, though it never saw added noise in training.
At 0 dB babble both models fail (~90 % WER).

**Finding 8 — an octave error caught by testing, not by eye.** The first pitch tracker read a
330 Hz voice as 82.5 Hz. Autocorrelation peaks at every multiple of the period; choosing the
shortest strong peak fixed it (all synthetic test voices within ~1 Hz, white noise rejected).

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
