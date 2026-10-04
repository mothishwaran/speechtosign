# 11 · Viva Prep — roughly half the marks

**Budget: ~1.5 hours, Tuesday evening.**

**Out loud. Every question.** Silent reading does not prepare you to speak, and the failure mode in a viva is never "didn't know" — it is "knew it and couldn't assemble it into a sentence under pressure."

Below each question is a **skeleton**: the points a strong answer contains. They are not scripts. Say them in your own words, because rehearsed phrasing is audible and invites follow-ups.

---

## A · Speech processing fundamentals — expect most questions here

This is a *speech processing* course. The examiner is more likely to probe MFCCs than your matcher.

**1 · Why 16 kHz? What does Nyquist say?**
Nyquist: sample at ≥ 2× the highest frequency you need. Speech intelligibility lives mostly under 8 kHz → 16 kHz. Telephony used 8 kHz and lost fricatives (`/s/`, `/f/`), which is why phone speech is harder to understand. Whisper's front end expects 16 kHz. **And you can add: you verified you actually get 16 kHz by resampling in an `OfflineAudioContext`, because the browser ignores the constraint.** That last sentence is the difference between a textbook answer and yours.

**2 · Walk through MFCC extraction. Why mel? Why DCT?**
Pre-emphasis → frame → window → FFT → power spectrum → mel filterbank → log → DCT → keep ~13 coefficients.
Mel: human pitch perception is roughly logarithmic, so mel spacing allocates resolution where the ear has it.
Log: perceived loudness is roughly logarithmic, and it turns the source–filter convolution into an addition.
DCT: decorrelates the filterbank energies (they are highly correlated because filters overlap), so a diagonal-covariance model becomes viable, and it compacts energy into the low coefficients.
**Practise this one end to end. It is the most likely single question in the whole viva.**

**3 · Framing and windowing. Typical sizes? Why Hamming?**
Speech is non-stationary overall but quasi-stationary over ~20–25 ms. Frame 25 ms, hop 10 ms → 60% overlap, so a frame boundary never destroys a transient.
Rectangular windows cut mid-cycle → discontinuity → spectral leakage. Hamming tapers to near zero at the edges → much lower sidelobes, at the cost of a slightly wider main lobe. That trade is worth it.

**4 · Spectrogram vs mel-spectrogram.**
Spectrogram: time × linear frequency × magnitude, from STFT. Mel-spectrogram: the same, with frequency warped to the mel scale and binned into filters — fewer bins, perceptually weighted. Whisper's input is a log-mel spectrogram (80 mel bins).

**5 · What does VAD do, and why later and not now?**
Voice activity detection segments speech from silence — needed to know *when* an utterance ended so you can transcribe continuously. You use push-to-talk, so the user supplies the boundary explicitly. VAD (Silero) is Phase 1, for continuous input. **Deliberately deferred, not overlooked** — say it that way.

**6 · How is WER computed? Compute it by hand.**
`WER = (S + D + I) / N`, N = words in the reference. Levenshtein alignment at word level.
**Drill this with a concrete pair before you walk in.** Example — Ref: `the cat sat on the mat` (N=6), Hyp: `the cat sat on mat`. One deletion (`the`) → WER = 1/6 ≈ 16.7%.
Also know: WER can exceed 100% because insertions are unbounded. That is a classic follow-up.

**7 · CTC vs attention encoder-decoder. Which does Whisper use?**
CTC: frame-level output with a blank symbol, monotonic alignment, conditionally independent outputs, no explicit language model — fast, streamable.
Attention encoder-decoder: autoregressive, learns alignment via attention, models output dependencies — more accurate, not natively streamable.
**Whisper is an attention-based encoder-decoder Transformer.** Not CTC. Be certain about this.

**8 · Describe Whisper's architecture. Input representation?**
Encoder-decoder Transformer. Input: log-mel spectrogram, 80 bins, 16 kHz audio, 30-second padded windows. Encoder produces audio representations; decoder generates text tokens autoregressively, conditioned via cross-attention, with special tokens for task and language. Trained on ~680k hours of weakly-supervised multilingual data — that scale is the paper's actual contribution.

**9 · What is int8 quantisation and what does it cost?**
Weights and/or activations stored as 8-bit integers instead of 32-bit floats. ~4× smaller, and much faster on CPU via integer SIMD. Cost: quantisation error, so a small accuracy drop — typically minor for a model this size. **You chose it deliberately: for a 5-word lexicon the accuracy margin is irrelevant and the latency is what the demo is judged on.** Trade-offs you can name are worth more than defaults you inherited.

**10 · DTW and HMMs — where do they fit?**
DTW: pre-statistical template matching, non-linear time alignment for variable speaking rate. Historically the isolated-word approach.
HMM: models speech as states with transition probabilities and emission distributions (GMMs, later DNNs). HMM-GMM then HMM-DNN dominated ASR until end-to-end neural models. Whisper is end-to-end — no explicit HMM, no separate pronunciation lexicon.

---

## B · Project defence

**11 · Why retrieval and not generation?**
Three legs: (a) production models are research-stage and not deployable — Saunders et al.; (b) the reception literature reports avatar output is poorly received by Deaf users — Kipp et al.; (c) retrieval plays **real video of Deaf signers**, so facial expression, timing and articulation are genuine rather than synthesised.
**Lead with the literature, not with the difficulty.** "Generation is hard" is a retreat; "the reception evidence points away from synthesis" is a design position.

**12 · Why ISL and not ASL, given ASL has more data?**
India-focused problem, and ISL is the language of the users this would serve. Under-resourcing is precisely the gap — building only for well-resourced languages is what created the disparity. Note also that ISL is not a dialect of ASL; it is a distinct language with its own grammar, so ASL data does not transfer.

**13 · What does a cosine similarity threshold guarantee about linguistic correctness?**
**Nothing.** Say that word first. It measures distance in a sentence-embedding space trained on English text — it is a proxy for semantic similarity of the *English*, not evidence that the retrieved video is correct ISL. That is why thresholds have to be calibrated against manually reviewed examples, and why Phase 0 uses exact matching, where the failure mode is at least legible.
**This question separates a good viva from an average one. Answer it with confidence, not hedging.**

**14 · Why is word-by-word signing linguistically wrong?**
ISL has its own grammar — different word order, spatial reference, verb agreement realised in signing space, and non-manual markers (facial expression, head tilt, mouthing) that carry grammatical meaning such as negation and question marking. Concatenating dictionary clips in English order produces signed English at best, and it drops the non-manual channel entirely. **Your system does this and you say so.**

**15 · Why can't you fingerspell every unknown word?**
Deaf signers do not fingerspell everything — it is reserved for names, technical terms and loanwords. A wall of fingerspelling is slow and unreadable. So unknown words are typed `uncovered` and dropped, and coverage reports exactly how much was dropped. **Dropping honestly beats spelling dishonestly**, and it is what makes coverage a real metric.

**16 · What are non-manual markers and why can't your system produce them?**
Facial expression, eyebrow position, head tilt, mouth patterns, body lean. They are grammatical, not decorative — eyebrow raise marks a yes/no question, headshake marks negation, and a sentence can change meaning without any change in the hands. Your clips are isolated dictionary signs recorded in neutral context, so no sentence-level non-manual grammar survives concatenation.

**17 · Licence on your data, and what does it prevent?**
ISLRTC terms must be checked before any public hosting; academic use is not the same as redistribution. ISLTranslate is CC-BY-NC — non-commercial, attribution required, so no commercial product without renegotiation. **This is why the repo commits `manifest.csv` with source URLs and never the video files** — reconstructible without redistributing.

**18 · What is coverage, and how is it different from accuracy?**
Coverage = tokens matched to a sign / total tokens. It measures **lexicon hit rate** — what fraction of the utterance the inventory could address. It says nothing about whether the output was correct, grammatical, or comprehensible. Accuracy would require Deaf-signer evaluation of the output, which you have not done and do not claim.
Report the number: **57.1% on the demo sentence, 4 sign / 1 spell / 2 uncovered out of 7 tokens.**

**19 · What breaks first going from 5 words to 500?**
Exact matching. Coverage rises but **precision of meaning collapses** — homonyms and context-dependent signs. ISLRTC explicitly carries synonyms, homonyms and context-specific variants, so one English word maps to several ISL signs and exact matching has no way to choose. That is the motivation for embeddings and phrase-level retrieval in Phase 1, and for phrase-level corpora over word-level ones.
Second-order: playback duration grows, and the naive clip queue starts to feel long.
Not the bottleneck: lookup cost. `match_ms ≈ 0`, and linear scan stays fine to thousands of entries.

**20 · What can this system genuinely not do?**
Spec §10 — memorise it. Not translation. English word order. No non-manual markers. No co-articulation. Unknown words dropped. Fingerspelling is a fallback, not natural output. Whisper is a component, not a contribution.
**Volunteer this before you are asked.** Confident admission of limits reads as mastery; overclaiming gets punished, and it gets punished harder if the examiner is the one who finds it.

---

## Drill list — do these three out loud, no notes

1. **WER by hand** on a pair you have not seen before. Very common ask.
2. **MFCC extraction**, end to end, ~60 seconds.
3. **"Why retrieval and not generation"**, leading with the reception literature.

---

## Delivery

- Answer the question asked. Stop. Silence after a complete answer is fine — filling it is how you talk yourself into a follow-up you did not want.
- "I don't know, but here is how I would find out" beats a confident wrong answer, every time.
- When you hit a limitation, say it plainly and move to what you *did* do. Do not apologise for scope.
- Rehearse the demo narration too — what you say while the clips play, including the ~10 seconds of fingerspelling. **Dead air during a demo is worse than the demo being short.**
