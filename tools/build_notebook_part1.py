"""Builds cells 1-N of the project notebook. See build_notebook.py for assembly."""

CELLS = []


def md(t):
    CELLS.append(("markdown", t.strip("\n")))


def code(t):
    CELLS.append(("code", t.strip("\n")))


# ─────────────────────────────────────────────────────────────── TITLE
md(r"""
# Speech → Indian Sign Language
### A retrieval-based demonstration system — Phase 0

**Course:** Speech Processing (22AIE450) · Amrita School of Artificial Intelligence, Coimbatore
**Student:** Mothishwaran · Roll 41 · AIE-A
**Review 1 · August 2026**

---

## What this notebook is

A complete, honest walkthrough of the project: the problem, the literature, the research gaps,
the speech-processing theory, every line of the working system, and the measured results.

Read it top to bottom and you will understand the whole project.

## What this system IS

> A person speaks English. The system recognises the speech, looks each word up in a small
> dictionary of **real Indian Sign Language video clips recorded by Deaf signers**, and plays
> the matching clips back in order.

## What this system is NOT

**It is not translation.** This distinction is the single most important thing in this notebook,
and it is stated up front rather than buried at the end.

| We do | We do NOT |
|---|---|
| Retrieve pre-recorded clips of real human signers | Generate or synthesise any signing |
| Match words and short phrases exactly | Understand meaning or context |
| Play clips in English word order | Produce correct ISL grammar |
| Report honestly what fraction of words we covered | Claim the output is fluent ISL |

Indian Sign Language is a **complete natural language with its own grammar** — not English
performed with the hands. Concatenating dictionary clips in English word order produces, at
best, "signed English". We say so throughout, and Section 15 lists every limitation explicitly.
""")

md(r"""
---
# Table of contents

| § | Section | What it covers |
|---|---|---|
| 1 | Problem and motivation | Why speech→ISL, why India |
| 2 | Literature review | 10 verified papers, grouped, with links |
| 3 | Research gaps | Three gaps, each traced to the papers above |
| 4 | System overview | The pipeline, end to end |
| 5 | Dataset | ISLRTC clips, the manifest, licensing |
| 6 | Speech processing theory | Sampling, framing, windowing, spectrograms, MFCC |
| 7 | Speech recognition | What Whisper is and how we configured it |
| 8 | Text normalisation | Turning a transcript into clean tokens |
| 9 | The matching algorithm | Longest-n-gram retrieval |
| 10 | Fingerspelling | The fallback for names |
| 11 | Serving the system | API and browser front end |
| 12 | Running the demo | End-to-end test |
| 13 | Evaluation design | What we measure and what it means |
| 14 | Results | Measured numbers and findings |
| 15 | Limitations | What this system genuinely cannot do |
| 16 | Pending work | Phases 1–4 |
| 17 | References | IEEE format |
""")

# ─────────────────────────────────────────────────────────── SETUP
md(r"""
---
# § 0 · Setup

Run this first. It confirms the environment and imports the project modules.

Everything runs on **CPU only** and, once the model is cached, **fully offline**.
""")

code(r"""
import os, sys, json, csv, wave, time
import numpy as np

# Run from the project root so relative paths in the modules resolve.
if os.path.basename(os.getcwd()) == "tools":
    os.chdir("..")
sys.path.insert(0, os.getcwd())

print("working dir :", os.getcwd())
print("python      :", sys.version.split()[0])
print("numpy       :", np.__version__)
""")

code(r"""
# Project modules. Each is small and does exactly one job.
from src import matcher, fingerspell

print("matcher    ->", matcher.__doc__.splitlines()[0])
print("fingerspell->", fingerspell.__doc__.splitlines()[0])
""")

# ─────────────────────────────────────────── 1 PROBLEM
md(r"""
---
# § 1 · Problem and motivation

## The communication gap

India has one of the world's largest Deaf and hard-of-hearing populations. Indian Sign Language
(ISL) is their primary language. But almost nobody outside the Deaf community signs, and
qualified ISL interpreters are extremely scarce relative to the population that needs them.

So an ordinary interaction — a hospital reception desk, a railway counter, a classroom — has no
shared language on either side.

## What would actually help

A system that takes **spoken English** and shows **Indian Sign Language video**, live.

## Why this is genuinely hard

1. **Sign language is not a writing system for speech.** ISL has its own grammar, its own word
   order, and uses the space in front of the signer to carry meaning.
2. **Meaning lives in the face and body too**, not just the hands. Raised eyebrows can turn a
   statement into a question. These are called *non-manual markers*.
3. **ISL has very little machine-readable data** compared to American or German Sign Language.
4. **Generating realistic signing is an unsolved research problem** — see § 2 and § 3.

## The design decision this project makes

Because generating signing is unsolved, we **do not generate anything**. We retrieve and play
**real video of real Deaf signers** from the government ISL dictionary.

This trades away flexibility (we can only show words we have clips for) in exchange for the
output being genuine, human, correctly-articulated signing. § 2 and § 3 explain why the
literature supports that trade.
""")

# ─────────────────────────────────────────── 2 LITERATURE
md(r"""
---
# § 2 · Literature review

Ten papers. Every citation below was **checked against the publisher's own page** — the links
go to ACL Anthology, CVF Open Access, PMLR, Springer, ACM or ISCA, not to a citation generator.

They are grouped by theme, because the grouping is itself the argument: the field has good
*recognition* of sign language, weak *production* of it, and almost nothing for ISL.
""")

md(r"""
## Group A — Speech recognition (the input side)

### [1] Whisper — the speech recogniser we actually use

> Radford, Kim, Xu, Brockman, McLeavey, Sutskever, **"Robust Speech Recognition via Large-Scale
> Weak Supervision"**, *ICML 2023*, PMLR vol. 202, pp. 28492–28518.
> 🔗 https://proceedings.mlr.press/v202/radford23a.html

**In simple terms:** OpenAI trained one speech-recognition model on **680,000 hours** of audio
scraped from the internet with imperfect labels. The lesson of the paper is that *enormous
messy data beats small clean data* — the model works on accents, noise and microphones it has
never seen, with no fine-tuning.

**Why we use it:** it works out of the box on Indian-accented English, runs on a laptop CPU, and
needs no training data of our own. We use the `base.en` variant.

**What it does NOT solve for us:** it only produces English text. Everything after that — the
actual sign language problem — is ours.
""")

md(r"""
## Group B — Indian Sign Language datasets (the resource problem)

### [2] ISLTranslate — the biggest ISL sentence-level dataset

> Joshi, Agrawal, Modi, **"ISLTranslate: Dataset for Translating Indian Sign Language"**,
> *Findings of ACL 2023*.
> 🔗 https://aclanthology.org/2023.findings-acl.665/

**In simple terms:** ~**31,000** pairs of (ISL video, English sentence). The largest translation
dataset for continuous ISL. Licensed CC-BY-NC — research use, attribution required, no commercial use.

**Why it matters to us:** this is our **Phase 1** corpus. We are *not* using it in Phase 0, and
we are careful never to imply otherwise.

### [3] iSign — a larger, more recent ISL benchmark

> Joshi et al., **"iSign: A Benchmark for Indian Sign Language Processing"**,
> *Findings of ACL 2024*, pp. 10827–10844.
> 🔗 https://aclanthology.org/2024.findings-acl.643/

**In simple terms:** over **118,000** video–sentence pairs plus a set of standard tasks
(video→text, pose→text, text→pose, word prediction, sign semantics) so different research groups
can compare fairly.

**Why it matters:** it is the current state of ISL resources, and it shows the field is finally
building infrastructure for ISL. It is our expansion option if ISLTranslate proves too small.

### [4] INCLUDE — isolated ISL word recognition

> Sridhar, Ganesan, Kumar, Khapra, **"INCLUDE: A Large Scale Dataset for Indian Sign Language
> Recognition"**, *ACM Multimedia 2020*, pp. 1366–1375.
> 🔗 https://www.semanticscholar.org/paper/fd9642b9a64553e36184565f1d21a2fa43b41362

**In simple terms:** 4,287 videos covering 263 individual word-signs, recorded with experienced signers.

**Why it matters:** it is representative of ISL resources generally — **isolated words, not
continuous sentences.** That imbalance is exactly Gap 1 in § 3.
""")

md(r"""
## Group C — Sign language translation and production (the state of the art)

### [5] Neural Sign Language Translation — the paper that started the field

> Camgöz, Hadfield, Koller, Ney, Bowden, **"Neural Sign Language Translation"**,
> *CVPR 2018*, pp. 7784–7793.
> 🔗 https://openaccess.thecvf.com/content_cvpr_2018/html/Camgoz_Neural_Sign_Language_CVPR_2018_paper.html

**In simple terms:** the first work to treat sign→text as a proper machine-translation problem,
explicitly handling the fact that sign order and spoken order differ. It also introduced
**RWTH-PHOENIX-Weather 2014T** (German Sign Language weather forecasts) — still the standard
benchmark.

**Why it matters:** PHOENIX14T is the yardstick the whole field measures against, and it is
German. Nothing of comparable quality exists for ISL. That contrast is Gap 1.

### [6] Sign Language Transformers — the modern architecture

> Camgöz, Koller, Hadfield, Bowden, **"Sign Language Transformers: Joint End-to-End Sign Language
> Recognition and Translation"**, *CVPR 2020*, pp. 10023–10033.
> 🔗 https://openaccess.thecvf.com/content_CVPR_2020/papers/Camgoz_Sign_Language_Transformers_Joint_End-to-End_Sign_Language_Recognition_and_Translation_CVPR_2020_paper.pdf

**In simple terms:** one transformer that learns to recognise signs and translate them at the
same time, using a CTC loss to tie the two tasks together. Roughly doubled previous scores.

**Why it matters:** this is sign **→** text. Our project is the opposite direction, which is the
much harder and much less solved one.

### [7] Progressive Transformers — text → sign *production*

> Saunders, Camgöz, Bowden, **"Progressive Transformers for End-to-End Sign Language
> Production"**, *ECCV 2020*, pp. 687–705.
> 🔗 https://link.springer.com/chapter/10.1007/978-3-030-58621-8_40

**In simple terms:** the first end-to-end model that goes from a written sentence to a
continuous sequence of 3D sign poses — a skeleton, not a video of a person.

**Why it matters most to us:** this is the closest thing to "what we are not attempting". Output
is stick-figure pose sequences, still research-grade, and the paper itself frames human-level
translation as the goal rather than the achievement. **This is the direct evidence for choosing
retrieval over generation.**
""")

md(r"""
## Group D — Speech → sign directly (the closest prior work to us)

### [8] Towards Automatic Speech to Sign Language Generation

> Kapoor, Mukhopadhyay, Hegde, Namboodiri, Jawahar, **"Towards Automatic Speech to Sign Language
> Generation"**, *Interspeech 2021*.
> 🔗 https://www.isca-archive.org/interspeech_2021/kapoor21_interspeech.html

**In simple terms:** goes straight from **speech audio** to sign pose sequences, skipping text
entirely, using a multi-tasking transformer. They also released the first ISL dataset with
speech-level annotations.

**Why this one matters enormously:** it is the same input and the same output and the same
language as our project — Indian Sign Language, driven by speech. It is the paper an examiner is
most likely to ask us to compare against.

**How we differ, honestly:** they *generate* poses; we *retrieve* real video. Theirs is more
ambitious and more general. Ours is simpler, produces genuine human signing, and is honestly
measurable. We do not claim to beat it.
""")

md(r"""
## Group E — Retrieval (the method for Phase 1)

### [9] Sentence-BERT — comparing sentences by meaning

> Reimers, Gurevych, **"Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks"**,
> *EMNLP-IJCNLP 2019*, pp. 3982–3992.
> 🔗 https://aclanthology.org/D19-1410/

**In simple terms:** turns a whole sentence into a single vector, so two sentences that *mean*
the same thing sit close together even when the words differ. Finding the closest pair drops
from ~65 hours with plain BERT to ~5 seconds.

**Why it matters:** this is how Phase 1 will match "could you help me" to a stored clip for
"please help", which exact matching can never do. **We are not using it in Phase 0** — Phase 0
is deliberately exact-match only.
""")

md(r"""
## Group F — How Deaf people actually receive this technology

This group decides our architecture. Skipping it would make the whole project an engineering
exercise with no grounding in its users.

### [10] Attitudes toward signing avatars

> Quandt, Willis, Schwenk, Weeks, Ferster, **"Attitudes Toward Signing Avatars Vary Depending on
> Hearing Status, Age of Signed Language Acquisition, and Avatar Type"**,
> *Frontiers in Psychology*, vol. 13, art. 730917, 2022.
> 🔗 https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2022.730917/full

**In simple terms — and read this carefully, because the popular summary of it is wrong:**

Deaf participants rated signing avatars **significantly lower** than hard-of-hearing or hearing
participants did. But the study found this depends on **avatar type**:

- **Computer-synthesised** avatars were rated harshly by Deaf signers.
- **Motion-capture** avatars — driven by a recording of a real human's movement — were **not**
  rated harshly.

The authors' interpretation: fluent signers are **expert judges of movement quality**. They are
not rejecting avatars in principle; they are detecting unnatural motion that less fluent viewers
miss.

**Why this is the single most useful paper for us.** The problem is *movement naturalness*, and
the closer the motion is to a real human, the better it is received. Retrieving **actual video of
actual Deaf signers** is the limit case of that spectrum — the motion is not approximated at all.

> ⚠️ **Accuracy note.** An earlier draft of our own plan claimed this literature shows avatars are
> "rejected by Deaf users". That overstates it and we corrected it. The finding is
> *conditional*: attitudes depend on hearing status, age of sign acquisition, and avatar type.
> Stating it correctly is stronger than overstating it — and an examiner who knows the paper will
> catch the overclaim.

**Related, also verified:** Kipp, Heloir, Nguyen, *"Assessing the deaf user perspective on sign
language avatars"*, ASSETS 2011 — 🔗 https://dl.acm.org/doi/10.1145/2049536.2049557
""")
