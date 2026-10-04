# 09 · Literature Review — 10 papers

**Budget: ~3 hours, Tuesday morning.** Abstract and conclusion only. You are not reading full texts today.

---

## Read this first

Everything in the table below is a **search lead, not a verified citation.** I am working from memory on the bibliographic details and memory is exactly the wrong tool for an IEEE reference list — a wrong year or a wrong venue in a submitted document is a real, checkable error, and it is the kind of thing an examiner spot-checks precisely because it is cheap to check.

**But: I have web search in this session.** Ask me to verify these and I will return actual authors, venues, years and DOIs. That turns three hours into about twenty minutes and removes the error class entirely.

**Do that tonight, while the demo bakes.** It is the single highest-leverage thing in this folder that you are not already doing.

If you verify them yourself instead: Google Scholar → the ACL Anthology or IEEE Xplore or the publisher page → **never** a citation-generator site, which is where wrong years come from.

---

## The ten, grouped by theme

Group them on the slide. A grouped LR reads as far more competent than a flat list, because grouping is itself an argument about the field.

### A · Speech recognition — 2 papers

| Lead | Why it is in your LR |
|---|---|
| **Whisper** — Radford et al., "Robust Speech Recognition via Large-Scale Weak Supervision" | The ASR component you actually use. Cite it where you justify `base.en`. |
| **wav2vec 2.0** — Baevski et al., self-supervised speech representations | The main alternative you did not choose. Gives you a comparison sentence rather than a bare assertion. |

*Cut from the original 15: CTC (Graves et al.) and Conformer (Gulati et al.). Know what CTC is for the viva — question #7 — but you do not need to cite it.*

### B · Sign language datasets — 4 papers. **Highest priority group.**

| Lead | Why |
|---|---|
| **ISLTranslate** — ACL Findings 2023 | ~31k ISL–English pairs. Your Phase 1 primary corpus. CC-BY-NC. |
| **iSign** — ACL Findings 2024 | 118k+ pairs, ISL benchmark. Your expansion option. |
| **INCLUDE** — ISL isolated sign dataset, ACM Multimedia 2020 | Word-level ISL. Establishes that ISL resources are isolated-sign-heavy. |
| **RWTH-PHOENIX-Weather 2014T** | The standard continuous SLT benchmark — German Sign Language. **This is the paper that proves gap #1**, because it is what ISL is being compared against and losing to. |

This is the group to do first and the group you cannot cut. It is the evidence base for your dataset slide *and* for your gaps slide.

### C · Sign language translation & production — 2 papers

| Lead | Why |
|---|---|
| **Neural Sign Language Translation** — Camgöz et al., CVPR 2018 | Founded the field. Sign→text. |
| **Progressive Transformers for End-to-End Sign Language Production** — Saunders et al. | Text→sign *production* — the thing you deliberately are not attempting. Cite it where you justify retrieval. |

*Cut: Sign Language Transformers (CVPR 2020) and Everybody Sign Now. Add back only if time allows.*

### D · Retrieval — 1 paper

| Lead | Why |
|---|---|
| **Sentence-BERT** — Reimers & Gurevych, EMNLP 2019 | Your Phase 1 method. Cite it under Pending Work, not Methodology — Phase 0 uses exact matching and you must not blur that line. |

*Cut: FAISS. Mention it as future work, no citation needed at this stage.*

### E · Deaf community reception — 1 paper. **Never cut this one.**

| Lead | Why |
|---|---|
| **Kipp et al.** — assessing the Deaf user perspective on sign language avatars | The entire justification for your architecture. |

Group E is a single paper doing more work than any other in the list. It is what converts *"we reduced scope because generation was hard"* into *"we chose retrieval of real Deaf signers because the reception literature reports that avatar output is poorly received by Deaf users."*

Same decision, two framings. One reads as a retreat, the other as a design position with evidence behind it. That is worth more than the citation itself.

---

## Priority order if you run short

1. Group B — all four datasets
2. Group C — both SLT/production
3. Group E — **the avatar reception paper**
4. Whisper
5. Sentence-BERT
6. wav2vec 2.0

Group E sits third, above the paper describing your own ASR component, because it answers the most likely viva question and the Whisper one does not.

---

## Note-taking format — one line per paper, built as you go

Build the IEEE entry at the moment you read the paper. **Never at the end.** Assembling twenty references at 11pm the night before is how wrong years get in.

```
[n] IEEE-formatted reference
    Claim:  what the paper establishes, one line
    Uses:   which slide it supports — LR / Gaps / Dataset / Methodology / Pending
```

IEEE journal format:
> [1] A. B. Author, C. D. Author, and E. F. Author, "Title of paper," *Journal Name*, vol. x, no. x, pp. xx–xx, Month Year.

IEEE conference format:
> [2] A. B. Author and C. D. Author, "Title of paper," in *Proc. Conf. Name*, City, Country, Year, pp. xx–xx.

Consistency matters more than perfection here. Pick one style, apply it to all ten, order the list by **first citation in the deck** — not alphabetically. That is the IEEE convention and it is a detail that gets noticed.

---

## The three gaps — draw them out of the LR, do not invent them

Each gap must be traceable to papers you actually cited. A gap with no citation behind it is an opinion, and it reads as one.

**Gap 1 — ISL is severely under-resourced relative to ASL and DGS.**
Evidence: PHOENIX-2014T and the ASL literature versus ISLTranslate and iSign. Orders of magnitude in annotated data, and the ISL resources that do exist skew toward isolated signs (INCLUDE) rather than continuous signing.

**Gap 2 — Sign language *production* remains research-stage, and avatar output is poorly received by Deaf users.**
Evidence: Saunders et al. for the state of production; Kipp et al. for reception. No deployable text→ISL generation system exists.

**Gap 3 — Retrieval-based speech→sign has not been systematically evaluated on ISL.**
This is your contribution statement. Everything upstream builds to it.

**Say gap 3 in one line and make it your Objectives slide.** Something you write yourself, of this shape: *"We evaluate whether retrieval of real ISL signer video, driven by ASR output, is a viable and honestly measurable substitute for sign language generation."* Your words, not mine — but that is the load it has to carry.

---

## Traps

- **Do not cite a paper you have not opened.** If asked "what did that paper find?" and you cannot answer, the whole reference list becomes suspect.
- **Do not cite ISLTranslate as though you used it.** You have not, in Phase 0. It belongs under Dataset and Pending Work. Blurring this is the fastest way to get caught overclaiming.
- **Do not pad to 15.** Ten papers you can each describe in a sentence beat fifteen you cannot.
- Verify every citation. See the top of this file.
