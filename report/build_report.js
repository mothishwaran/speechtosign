// Builds report/Speech_to_ISL_IEEE_Report.docx in the IEEE conference layout:
// US Letter, two 3.5-inch columns, Times New Roman 10 pt, numbered sections,
// TABLE captions above tables, Fig. captions below figures, IEEE references.
// Run:  node report/build_report.js   (needs the "docx" npm package)
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell,
  AlignmentType, WidthType, BorderStyle, SectionType, TabStopType, ExternalHyperlink,
  LevelFormat, VerticalAlign,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FIG = (f) => path.join(ROOT, "report", "figures", f);
const FONT = "Times New Roman";
const COL = 5040;                 // one column, twips (3.5 in)
const PAGE = { width: 12240, height: 15840 };
const MARGIN = { top: 1080, bottom: 1440, left: 900, right: 900 };

// ── inline markup: **bold**, *italic*, _{sub}, ^{sup} ──────────────────────
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|_\{[^}]+\}|\^\{[^}]+\})/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), font: FONT, bold: true, ...base }));
    else if (t.startsWith("*")) out.push(new TextRun({ text: t.slice(1, -1), font: FONT, italics: true, ...base }));
    else if (t.startsWith("_{")) out.push(new TextRun({ text: t.slice(2, -1), font: FONT, subScript: true, ...base }));
    else out.push(new TextRun({ text: t.slice(2, -1), font: FONT, superScript: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, ...base }));
  return out;
}

const P = (text, opts = {}) => new Paragraph({
  children: runs(text, { size: 20 }),
  alignment: AlignmentType.JUSTIFIED,
  indent: { firstLine: opts.noIndent ? 0 : 202 },
  spacing: { after: 0, line: 240 },
});

const romans = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"];
let h1n = 0, h2n = 0;
const H1 = (text, numbered = true) => {
  const label = numbered ? `${romans[h1n++]}. ${text}` : text;
  h2n = 0;
  return new Paragraph({
    children: [new TextRun({ text: label, font: FONT, size: 20, smallCaps: true })],
    alignment: AlignmentType.CENTER, spacing: { before: 200, after: 100 }, keepNext: true,
  });
};
const H2 = (text) => new Paragraph({
  children: [new TextRun({ text: `${String.fromCharCode(65 + h2n++)}. ${text}`, font: FONT, size: 20, italics: true })],
  spacing: { before: 120, after: 60 }, keepNext: true,
});

// bulleted list
const BULLET = "ieee-bullets";
const LI = (text) => new Paragraph({
  children: runs(text, { size: 20 }), alignment: AlignmentType.JUSTIFIED,
  numbering: { reference: BULLET, level: 0 }, spacing: { after: 20 },
});

// equations: centred expression, number flush right
let eqn = 0;
const EQ = (segments) => new Paragraph({
  tabStops: [{ type: TabStopType.CENTER, position: COL / 2 }, { type: TabStopType.RIGHT, position: COL }],
  spacing: { before: 60, after: 60 },
  children: [new TextRun({ text: "\t", font: FONT, size: 20 }), ...runs(segments, { size: 20 }),
             new TextRun({ text: `\t(${++eqn})`, font: FONT, size: 20 })],
});

// figures
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
let fign = 0;
function FIGURE(file, caption, widthIn = 3.35) {
  const { w, h } = pngSize(FIG(file));
  const px = Math.round(widthIn * 96);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: fs.readFileSync(FIG(file)),
        transformation: { width: px, height: Math.round(px * h / w) },
        altText: { title: `Fig. ${fign + 1}`, description: caption, name: file } })],
    }),
    new Paragraph({
      alignment: AlignmentType.JUSTIFIED, spacing: { after: 160 },
      children: [new TextRun({ text: `Fig. ${++fign}. `, font: FONT, size: 16 }), ...runs(caption, { size: 16 })],
    }),
  ];
}

// tables: IEEE style - caption above, horizontal rules only, 8 pt
let tabn = 0;
const NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const RULE = { style: BorderStyle.SINGLE, size: 6, color: "000000" };
function TABLE(title, header, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (text, i, isHead, isLast) => new TableCell({  // keepNext on all but the last row keeps the table in one piece
    width: { size: widths[i], type: WidthType.DXA },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 30, bottom: 30, left: 60, right: 60 },
    borders: { left: NONE, right: NONE, top: isHead ? RULE : NONE, bottom: (isHead || isLast) ? RULE : NONE },
    children: [new Paragraph({
      alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER, keepNext: !isLast,
      children: runs(text, { size: 16, bold: isHead }),
    })],
  });
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160, after: 0 }, keepNext: true,
      children: [new TextRun({ text: `TABLE ${romans[tabn++]}`, font: FONT, size: 16, smallCaps: true })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, keepNext: true,
      children: [new TextRun({ text: title, font: FONT, size: 16, smallCaps: true })] }),
    new Table({
      width: { size: total, type: WidthType.DXA }, columnWidths: widths, alignment: AlignmentType.CENTER,
      rows: [new TableRow({ tableHeader: true, cantSplit: true, children: header.map((t, i) => cell(t, i, true, false)) }),
             ...rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false, ri === rows.length - 1)) }))],
    }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
}

// ── title block (spans both columns) ───────────────────────────────────────
const authorCell = (lines) => new TableCell({
  width: { size: 5200, type: WidthType.DXA },
  borders: { top: NONE, bottom: NONE, left: NONE, right: NONE },
  children: lines.map((l, i) => new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: 0 },
    children: [new TextRun({ text: l, font: FONT, size: i === 0 ? 22 : 18, italics: i > 0 && i < lines.length - 1 })],
  })),
});
const titleBlock = [
  new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: 200 },
    children: [new TextRun({ text: "Speech to Indian Sign Language: Accent-Adapted Speech Recognition and Dictionary-Based Sign Retrieval",
      font: FONT, size: 48 })],
  }),
  new Table({
    width: { size: 10400, type: WidthType.DXA }, columnWidths: [5200, 5200], alignment: AlignmentType.CENTER,
    rows: [new TableRow({ children: [
      authorCell(["Abhishek Karthik J", "Dept. of [Department name]", "[Institution name]", "[City], India", "[email address]"]),
      authorCell(["M. P. Mothishwaran", "Dept. of [Department name]", "[Institution name]", "[City], India", "[email address]"]),
    ] })],
  }),
  new Paragraph({ spacing: { after: 240 }, children: [] }),
];

// ── body ───────────────────────────────────────────────────────────────────
const abstract = new Paragraph({
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 120 },
  children: [
    new TextRun({ text: "Abstract", font: FONT, size: 18, bold: true, italics: true }),
    new TextRun({ text: "—", font: FONT, size: 18, bold: true }),
    ...runs("People whose first language is Indian Sign Language (ISL) are often cut off from spoken English in classrooms, offices and public places. This paper describes a system that listens to spoken English and plays the matching signs as video recordings of Deaf signers taken from the ISLRTC dictionary. Speech is recognised with Whisper base.en, which we fine-tuned on Svarah, a corpus of Indian-accented English. On sixteen speakers who were kept out of training, the word error rate dropped from 13.2% to 11.3%, and fourteen of the sixteen improved. Recognised words are mapped to signs through a lookup chain that covers about 4,000 phrases stored locally and another 2,700 that are downloaded on demand from the dictionary archive; inflected forms and manually reviewed synonyms extend the vocabulary, and unknown words are fingerspelled. Classical analysis runs alongside the recogniser: short-time energy, zero-crossing rate, an autocorrelation pitch tracker and spectral subtraction. Two of the experiments built on these gave negative results that we report in full. Spectral subtraction raised the signal-to-noise ratio by up to 7 dB but made recognition worse in 15 of 18 noise conditions, and the final pitch movement separated yes/no questions from statements with only 66.5% balanced accuracy. On twenty held-out everyday sentences, 67% of the words that ISL would sign had a dictionary sign. The whole pipeline runs interactively on a laptop GPU.",
      { size: 18, bold: true }),
  ],
});
const indexTerms = new Paragraph({
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 160 },
  children: [
    new TextRun({ text: "Index Terms", font: FONT, size: 18, bold: true, italics: true }),
    new TextRun({ text: "—", font: FONT, size: 18, bold: true }),
    new TextRun({ text: "speech recognition, Indian Sign Language, Whisper, fine-tuning, accented speech, pitch detection, spectral subtraction, sign retrieval",
      font: FONT, size: 18, bold: true }),
  ],
});

const body = [
  abstract, indexTerms,

  H1("Introduction"),
  P("Indian Sign Language is a complete language with its own vocabulary and grammar; it is not English spelled out with the hands [1]. For a Deaf person who grew up signing, a lecture, a railway announcement or a conversation at a counter is easy to miss, and trained interpreters are few. A tool that turns speech into signs automatically could close part of that gap, even if it cannot replace an interpreter."),
  P("Most research in this area runs the other way, from signs to text. Generating signs from speech is harder. Neural sign production models learn to output skeletal poses or avatar animation [2], [3], but they need large parallel corpora, which hardly exist for ISL, and Deaf viewers have consistently rated signing avatars below human signers [4], [5]. We therefore took a retrieval approach: every sign the system shows is a real recording of a Deaf signer, and our modelling effort goes into the part that decides what was said, namely speech recognition and the speech processing around it."),
  P("Recognition is a weak point for Indian users. Whisper [6] performs well on many benchmarks, but the Svarah study found that English recognisers lose accuracy on Indian accents [7]. Our main contributions are:"),
  LI("fine-tuning Whisper base.en on Indian-accented speech, evaluated on speakers who never appear in training, with a per-speaker analysis and a significance test;"),
  LI("a speech analysis front end (energy, zero-crossing rate, autocorrelation pitch and spectral subtraction) shown live while the user speaks, with two controlled studies of whether the classical tools help a neural recogniser;"),
  LI("a sign lookup chain over the full ISLRTC dictionary that combines locally stored clips, on-demand download, word forms, reviewed synonyms, number reading and fingerspelling;"),
  LI("an evaluation that reports coverage, error rates and negative results without merging approximate matches into the headline numbers."),
  P("Section II reviews related work and states the gaps we address. Section III gives the objectives and datasets, Section IV the method, Section V the results, Section VI the limitations, and Section VII concludes."),

  H1("Related Work"),
  H2("Speech Recognition and Indian Accents"),
  P("Whisper [6] is an encoder-decoder Transformer [8] trained on about 680,000 hours of weakly labelled audio. The encoder reads an 80-band log-mel spectrogram, a representation descended from the mel-frequency features studied by Davis and Mermelstein [9], and the decoder writes text token by token. Svarah [7] collected read and spontaneous English from 117 speakers across India and showed that error rates rise noticeably on these accents. Svarah was released as a test benchmark; we re-split it by speaker so that it could also be used for adaptation."),
  H2("Classical Speech Analysis"),
  P("Rabiner's study of autocorrelation pitch detection [10] remains a standard reference for estimating the fundamental frequency of voiced speech. For noise, Boll's spectral subtraction [11] estimates the noise spectrum during pauses and removes it from each frame, and Berouti *et al.* [12] added over-subtraction and a spectral floor to suppress the residual \"musical noise\". These methods were developed for older recognisers and for human listeners, and it is an open practical question whether they still help a large neural model."),
  H2("Sign Language Translation and Production"),
  P("Camgöz *et al.* framed sign language translation as neural machine translation from video [13] and later trained recognition and translation jointly with Transformers [14]. In the production direction, Saunders *et al.* generated continuous pose sequences from text [2], and Kapoor *et al.* went directly from speech to sign poses for Indian Sign Language [3]. The output of these systems is a skeleton or an avatar rather than a human signer, and they depend on paired data that is scarce for ISL."),
  H2("ISL Resources"),
  P("INCLUDE [15] is a word-level ISL recognition dataset of 263 signs recorded on video. ISLTranslate [16] provides about 31,000 sentence-level ISL-English pairs from educational videos, and iSign [17] gathers several ISL processing tasks into one benchmark. None of these provides the clean, one-sign-per-clip lexicon that a retrieval system needs; the ISLRTC dictionary does."),
  H2("Avatars, Semantics and Grammar"),
  P("Kipp *et al.* [4] found that Deaf participants judged signing avatars critically, mainly for stiff motion and missing facial expression, and Quandt *et al.* [5] showed that attitudes depend on hearing status and avatar type. For word meaning, Sentence-BERT [18] gives sentence embeddings for semantic similarity, while WordNet [19] organises English words into hand-built synonym sets. Zeshan's typological outline of Indo-Pakistani Sign Language [1] describes word-order tendencies such as question words at the end of a clause. We use the bootstrap [20] to test whether differences in error rate are larger than chance."),
  H2("Identified Gaps"),
  P("Three gaps motivated this work. First, speech-to-sign systems rarely adapt the recogniser to Indian speakers or report its error on them, although recognition errors pass straight into the signed output. Second, production models depend on parallel data and avatar rendering, while retrieval systems built on real signers seldom report how much of a sentence they can actually sign. Third, classical enhancement and prosodic cues are usually assumed to help, and are rarely measured against a modern neural recogniser inside a working pipeline."),

  H1("Objectives and Datasets"),
  H2("Objectives"),
  P("The objectives were: (i) to lower the recognition error for Indian-accented English and prove it on unseen speakers; (ii) to implement and evaluate classical speech processing within the pipeline; (iii) to sign as much of an everyday sentence as possible using genuine ISL signs, without silently dropping words; and (iv) to run in real time on a laptop."),
  H2("ISLRTC Sign Dictionary"),
  P("The Indian Sign Language Research and Training Centre (ISLRTC) publishes a video dictionary in which each clip shows one sign performed by a Deaf signer. The full archive holds 15,462 videos (about 250 GB). Downloading it all was impractical, so we kept 5,615 videos locally and built a manifest by parsing file names: for example, *I_Don_t_Know.mp4* becomes the phrase \"i don't know\" and *Rupee, money.mp4* yields two phrases. Clips longer than 30 s are explanations of a word rather than the sign itself and were excluded, as were Hindi-only files and regional compilations. The remaining files were catalogued for download on demand. Videos are never redistributed; the repository stores only the manifest and file references. Table I summarises the dictionary."),
  ...TABLE("ISLRTC dictionary as used", ["Item", "Count"], [
    ["Videos in the online archive", "15,462"],
    ["Videos stored locally", "5,615"],
    ["Phrases in the local manifest", "4,068"],
    ["Further phrases fetchable on demand", "2,740"],
    ["Clips skipped (longer than 30 s)", "1,256"],
    ["Alphabet clips for fingerspelling", "26"],
  ], [3600, 1300]),
  H2("Svarah Speech Corpus"),
  P("Svarah [7] contains 6,656 utterances (9.6 h) from 117 speakers and is released under CC BY 4.0. Because the corpus has no speaker column, and because its file name prefixes turned out not to identify speakers (there are about 2,900 distinct prefixes for 117 people), we grouped utterances by each speaker's full demographic profile. A speaker's profile never changes, so no speaker can appear in two splits. This gives 115 groups, because a few speakers share a profile and are kept together, which errs on the safe side; in the rest of the paper a \"speaker\" means one such group. Table II shows the split."),
  ...TABLE("Speaker-disjoint split of Svarah", ["Split", "Speaker groups", "Utterances", "Hours"], [
    ["Train", "84", "5,342", "7.61"],
    ["Dev", "15", "694", "0.99"],
    ["Test", "16", "620", "1.02"],
  ], [1400, 1100, 1300, 1000]),
  H2("Evaluation Sentences"),
  P("We wrote two sets of twenty everyday sentences. The first was used during development. The second, the held-out set, was written after all matching rules were fixed and was never used to tune anything, so its figures are the ones we treat as representative. Both sets were also spoken with a synthetic voice and passed through the complete system."),

  H1("Methodology"),
  P("Fig. 1 shows the pipeline. Audio is recorded in the browser, recognised on the server, mapped to signs and played back in the browser."),
  ...FIGURE("fig1_flow.png", "Processing pipeline of the speech-to-ISL system.", 3.0),
  H2("Signal Acquisition"),
  P("The browser records the microphone at its native rate and resamples to 16 kHz mono, 16-bit PCM before upload. Speech information lies mostly below 8 kHz, so by the Nyquist criterion 16 kHz preserves it, and it is the rate Whisper was trained on. Sixteen-bit samples give a quantisation floor about 96 dB below full scale."),
  H2("Short-Time Spectral Analysis"),
  P("Speech is treated as stationary over 20 to 40 ms, so it is divided into overlapping frames *x*_{m}[*n*] and multiplied by a Hann window *w*[*n*] to limit spectral leakage. The short-time Fourier transform of frame *m* is"),
  EQ("*X*(*m*, *k*) = Σ_{n} *x*[*n*] *w*[*n* − *mH*] e^{−j2πkn/N}"),
  P("with hop size *H*. Whisper's input is the log-mel spectrogram, obtained by pooling the power spectrum with 80 triangular mel filters *M*_{b}(*k*):", { noIndent: true }),
  EQ("*S*(*m*, *b*) = log_{10}( Σ_{k} *M*_{b}(*k*) |*X*(*m*, *k*)|^{2} )"),
  P("computed with 25 ms windows and a 10 ms hop over a 30 s window, which gives an 80 × 3000 matrix.", { noIndent: true }),
  H2("Time-Domain Features"),
  P("For a frame of *N* samples the short-time energy and zero-crossing rate are"),
  EQ("*E*(*m*) = 10 log_{10}( (1/*N*) Σ_{n} *x*_{m}^{2}[*n*] )"),
  EQ("*Z*(*m*) = (*f*_{s} / 2*N*) Σ_{n} |sgn(*x*_{m}[*n*]) − sgn(*x*_{m}[*n* − 1])|"),
  P("Energy separates speech from silence. Unvoiced sounds such as /s/ are noise-like and cross zero often, while vowels cross it rarely.", { noIndent: true }),
  H2("Pitch Estimation"),
  P("The fundamental frequency of a voiced frame is found from its normalised autocorrelation"),
  EQ("*r*_{m}(τ) = Σ *x*_{m}[*n*]*x*_{m}[*n*+τ] / √( Σ *x*_{m}^{2}[*n*] · Σ *x*_{m}^{2}[*n*+τ] )"),
  P("searched over lags corresponding to 70–400 Hz, with *F*_{0} = *f*_{s} / τ_{0} for the selected lag τ_{0}. A frame is voiced when the peak reaches 0.5 and its energy is above the silence threshold. Because multiples of the true period score almost as high as the period itself, we take the shortest local peak within 10% of the maximum; without this rule a 330 Hz test voice was read as 82.5 Hz. To describe intonation we compare the median *F*_{0} of the last 300 ms of voiced speech with the median of the rest, in semitones:", { noIndent: true }),
  EQ("Δ = 12 log_{2}( median *F*_{0,final} / median *F*_{0,body} )"),
  ...FIGURE("fig2_speech.png", "Analysis of a sample sentence: (a) waveform, (b) spectrogram, (c) pitch track from the autocorrelation tracker. Gaps in (c) are unvoiced or silent frames."),
  H2("Spectral Subtraction"),
  P("The optional noise reducer follows Boll [11] with over-subtraction [12]. The noise power spectrum *N*̂(*k*) is the mean over the quietest 10% of frames, which avoids assuming the recording starts with silence, and the clean power is"),
  EQ("|*S*̂(*m*, *k*)|^{2} = max( |*Y*(*m*, *k*)|^{2} − α*N*̂(*k*), β|*Y*(*m*, *k*)|^{2} )"),
  P("with α = 2 and β = 0.02, 32 ms frames and an 8 ms hop. The noisy phase is kept and the signal is rebuilt by overlap-add. With α = 0 the implementation reconstructs its input with an SNR of 147 dB, which confirms the transform pair.", { noIndent: true }),
  H2("Speech Recognition and Fine-Tuning"),
  P("We started from Whisper base.en, a 74-million-parameter English model, and fine-tuned all of its weights on the Svarah training split with the settings in Table III. Checkpoints were written every 200 steps and included the optimiser state, so training can resume on another machine. The checkpoint with the lowest dev error was converted to CTranslate2 with 8-bit weights (76 MB). At run time it is decoded greedily in 16-bit floating point on the GPU, falling back to 8-bit on the CPU."),
  ...TABLE("Fine-tuning settings", ["Setting", "Value"], [
    ["Base model", "Whisper base.en"],
    ["Epochs / steps", "3 / 1,002"],
    ["Batch size", "16"],
    ["Optimiser", "AdamW, lr 1×10^{−5}, 100 warm-up steps"],
    ["Precision", "mixed (fp16)"],
    ["Hardware / time", "RTX 4050 laptop GPU, 69 min"],
    ["Selection", "lowest dev WER (step 600)"],
  ], [1700, 3200]),
  H2("Text Processing"),
  P("The transcript is lower-cased and split into words, keeping apostrophes so that *don't* matches the dictionary entry. Numbers are read as they are spoken (25 becomes TWENTY FIVE, 7:30 becomes SEVEN THIRTY) and are signed digit by digit when part of the reading has no sign, which is the case for forty, eighty and ninety. Articles and forms of *be* are marked as omitted because ISL does not sign them. A sentence is treated as a question when it starts with a question word followed by a verb, starts with an auxiliary verb (\"Can you ...\"), or ends with a question mark."),
  H2("Sign Lookup"),
  P("Signs are matched greedily, longest phrase first, so that \"thank you\" maps to its own sign rather than two separate ones. A word that has no direct match passes through a fixed chain: the local manifest, then the online archive, then number reading, then fingerspelling for names, then the omitted-word list, then inflected forms, then reviewed synonyms, and finally fingerspelling. Inflected forms (*went* to GO, *children* to CHILD) come from WordNet [19]; a form is accepted only when its part of speech accounts for at least 70% of the base word's tagged uses, which keeps ambiguous cases such as *trained* unmapped. Synonyms are proposed from the most frequent sense in WordNet and used only after a manual review, which accepted 121 of 171 proposals. When a needed clip is only in the archive, the server downloads that one file, checks that it is a single sign, converts it if a browser cannot play it, and caches it."),
  H2("Ordering and Playback"),
  P("By default the signs follow the spoken order. An optional mode applies three rules within each sentence that are consistent with descriptions of ISL grammar [1]: time expressions first, negation last, and a question word last. Clips play back to back using two alternating video players to avoid gaps. Because very short phrases are sometimes misheard, the interface also lets the user type a corrected sentence and sign it through the same pipeline."),

  H1("Results and Analysis"),
  H2("Effect of Fine-Tuning"),
  P("Table IV and Fig. 3 compare the stock and fine-tuned models on the 620 test utterances, decoded exactly as the application decodes them. The word error rate is (*S* + *D* + *I*)/*N*, counting substituted, deleted and inserted words against the *N* reference words, after Whisper's English text normaliser. Whisper re-decodes difficult segments with random sampling, so two runs differ slightly; both are reported."),
  ...TABLE("Word error rate on 16 unseen test speakers", ["Model", "Run 1", "Run 2"], [
    ["Whisper base.en (stock)", "13.12%", "13.32%"],
    ["Fine-tuned on Svarah", "11.30%", "11.27%"],
  ], [2500, 1200, 1200]),
  ...FIGURE("fig3_training.png", "(a) Dev WER during fine-tuning; the checkpoint at step 600 was kept. (b) Test WER of the stock and fine-tuned models."),
  P("The relative reduction is about 14%. Fourteen of the sixteen speakers improved (Fig. 4); the other two became slightly worse, by 0.4 and 0.5 points. The largest gains came for speakers the stock model found hard: from 53.8% to 41.0%, from 37.4% to 28.2% and from 19.6% to 10.6%. In a paired bootstrap over utterances [20], the fine-tuned model had fewer errors in all 2,000 resamples. We also tried running both models and keeping the more confident transcript; this gave 11.25%, too small a gain to justify doubling the computation, so it was not adopted."),
  ...FIGURE("fig4_speakers.png", "Per-speaker WER on the sixteen test speakers, sorted by the stock model's error."),
  H2("Noise Robustness and Spectral Subtraction"),
  P("To test robustness we mixed 200 test utterances with white noise and with babble made from four other speakers, at 20, 10, 5 and 0 dB SNR, and decoded each with both models, with and without spectral subtraction. Table V gives selected results and Fig. 5 the full curves."),
  ...TABLE("WER (%) under noise; SS = spectral subtraction", ["Condition", "Stock", "+SS", "Tuned", "+SS"], [
    ["Clean", "13.1", "13.6", "11.0", "11.9"],
    ["White 10 dB", "28.3", "28.8", "25.4", "24.5"],
    ["White 5 dB", "44.9", "43.9", "34.5", "36.5"],
    ["White 0 dB", "67.7", "73.6", "55.6", "59.8"],
    ["Babble 10 dB", "22.2", "25.8", "21.1", "21.3"],
    ["Babble 5 dB", "41.5", "47.4", "36.8", "39.8"],
  ], [1500, 800, 800, 800, 800]),
  ...FIGURE("fig5_noise.png", "WER against signal-to-noise ratio for (a) white and (b) babble noise. Dashed lines include spectral subtraction."),
  P("Two findings stand out. The fine-tuned model was more robust at every white-noise level, although it never saw added noise during training; at 5 dB its error was 34.5% against 44.9%. Spectral subtraction, on the other hand, improved the SNR by 3.7 to 7.1 dB for white noise but by less than 1 dB for babble, as expected for a method that assumes stationary noise, and it raised the error rate in 15 of the 18 conditions. Whisper was trained on noisy audio and appears to cope with noise better than with the artefacts that subtraction leaves. The noise reducer is therefore an option that is off by default."),
  H2("Pitch as a Question Cue"),
  P("We measured the final pitch movement of all 387 questions in Svarah and of 387 randomly chosen statements. The threshold was chosen on training speakers and evaluated on dev and test speakers (Table VI)."),
  ...TABLE("Question detection on unseen speakers", ["Method", "Result"], [
    ["Median final movement", "yes/no −0.3, wh −2.6, statement −2.2 st"],
    ["Pitch alone (yes/no vs statement)", "66.5% balanced accuracy"],
    ["Word order and \"?\"", "79/85 questions, 1/70 false alarms"],
    ["Word order, \"?\" removed", "61/85 questions, 1/70 false alarms"],
  ], [1800, 3100]),
  P("In this read Indian English, yes/no questions did not rise at the end; they fell less than statements did. Pitch alone was a weak cue, and adding it to the word-order rule mostly added false alarms on the training speakers. The system therefore decides from word order and shows the pitch movement only as supporting evidence."),
  H2("Sign Coverage"),
  P("Coverage is the share of words that receive a dictionary sign. We report it over all words, over the words that ISL actually signs (excluding articles and forms of *be*), and with on-demand download and synonyms added (Fig. 6). On the held-out sentences, 54% of all words and 66% of ISL-signed words had a local sign; the archive raised this to 67% and synonyms to 72%. The development set reached 87%, which shows how optimistic figures become once a test set has influenced the design. In the end-to-end test with a synthetic voice, recognition errors were 2.0% and 2.4% on the two sets and every requested clip was served. Fig. 7 shows the clips played for one sentence."),
  ...FIGURE("fig6_coverage.png", "Sign coverage on the development (everyday) and held-out sentence sets."),
  ...FIGURE("fig7_signs.png", "Clips played for \"Where is the hospital? I am 25 years old.\" Articles and the verb *be* are omitted, and 25 is signed as TWENTY FIVE. The pronoun *I* has no dictionary entry and is deliberately not fingerspelled, since a single letter I would mislead."),
  H2("Embeddings Versus WordNet"),
  P("Before using sentence embeddings for synonyms we tested a MiniLM model, from the Sentence-BERT family [18], on 30 true synonym pairs and 30 pairs of related but different words. At every useful threshold it accepted wrong pairs such as Monday and Tuesday or husband and wife, both with a cosine similarity of 0.87, which is higher than many real synonyms. WordNet accepted none of the wrong pairs (Table VII). Showing the sign for a different word is worse than showing nothing, so WordNet with manual review was used."),
  ...TABLE("Synonym check: 30 true and 30 false pairs", ["Method", "True accepted", "False accepted"], [
    ["Embeddings, threshold 0.70", "18", "8"],
    ["Embeddings, threshold 0.85", "7", "2"],
    ["WordNet (used)", "11", "0"],
  ], [2300, 1300, 1300]),
  H2("Latency"),
  P("On the same short recording, recognition took about 3.1 s on the CPU on battery power, 1.6 s on mains power, and 0.15 to 0.25 s on the GPU. Matching against the dictionary takes under a millisecond, so the recogniser accounts for almost all of the delay. A sign that has to be downloaded adds a few seconds the first time it is used (5.6 s for a 3.3 MB clip on our connection) and nothing afterwards."),
  H2("Error Analysis"),
  P("Some problems appeared only in live use. A short recording of \"cricket match\" was misheard by the fine-tuned model (\"trickier to match\"), by the stock model (\"click here to match\") and by the three-times-larger small.en (\"couldn't get the match\"); with so little context the decoder has almost nothing to go on, which is why the interface has a correction box. In the longer sentence \"I play cricket and hockey\" the stock and small models were correct but the fine-tuned model wrote \"chicken\", a reminder that a lower average error does not mean every word improves. Users also reported that fingerspelling was unreadably fast. The cause was a timestamp error in the tool that cut the alphabet clips, which stored 1.5 s of signing as 0.03 s; the clips were re-timed and fingerspelling now runs at about one letter per second."),

  H1("Discussion and Limitations"),
  P("The system retrieves signs; it does not translate. Signs follow English order unless the reordering option is used, and that option applies only three rules. Facial expressions, which carry grammatical information in ISL, cannot be expressed by joining isolated dictionary clips; yes/no questions, for example, are marked with raised eyebrows. Synonyms were reviewed for English meaning but not by an ISL signer. Recognition was evaluated on Svarah and on synthetic speech, and the evaluation with the two authors' own voices is still small. Most importantly, no Deaf user has yet judged whether the output is understandable, so our coverage figures measure what the dictionary can express, not what a viewer understands."),

  H1("Conclusion and Future Work"),
  P("We built a speech-to-ISL system that uses real signer videos and concentrated the speech processing work where it matters most for Indian users. Fine-tuning Whisper on Indian-accented English reduced the error on unseen speakers from 13.2% to 11.3% and also made the model more robust to noise. Two classical techniques were implemented and measured honestly: spectral subtraction did not help a modern recogniser, and final pitch movement was a weak question cue for this speech. The lookup chain signs about two thirds of the signable words in unseen everyday sentences and never drops a word silently. Future work should include an evaluation with Deaf ISL users, training on more Indian speech including noisy recordings, and richer ISL grammar learnt from parallel corpora such as ISLTranslate [16]."),

  H1("Acknowledgment", false),
  P("We thank ISLRTC for making the ISL dictionary available and AI4Bharat for releasing the Svarah corpus under an open licence."),

  H1("References", false),
];

// ── references (IEEE, every entry with a verified DOI link) ─────────────────
const REFS = [
  ["U. Zeshan, \"Indo-Pakistani Sign Language grammar: A typological outline,\" *Sign Language Studies*, vol. 3, no. 2, pp. 157–212, 2003.", "10.1353/sls.2003.0005"],
  ["B. Saunders, N. C. Camgöz, and R. Bowden, \"Progressive transformers for end-to-end sign language production,\" in *Proc. Eur. Conf. Comput. Vis. (ECCV)*, LNCS, 2020, pp. 687–705.", "10.1007/978-3-030-58621-8_40"],
  ["P. Kapoor, R. Mukhopadhyay, S. B. Hegde, V. Namboodiri, and C. V. Jawahar, \"Towards automatic speech to sign language generation,\" in *Proc. Interspeech*, 2021, pp. 3700–3704.", "10.21437/Interspeech.2021-1094"],
  ["M. Kipp, Q. Nguyen, A. Heloir, and S. Matthes, \"Assessing the deaf user perspective on sign language avatars,\" in *Proc. 13th Int. ACM SIGACCESS Conf. Comput. Accessibility (ASSETS)*, 2011, pp. 107–114.", "10.1145/2049536.2049557"],
  ["L. C. Quandt, A. Willis, M. Schwenk, K. Weeks, and R. Ferster, \"Attitudes toward signing avatars vary depending on hearing status, age of signed language acquisition, and avatar type,\" *Frontiers in Psychology*, vol. 13, art. 730917, 2022.", "10.3389/fpsyg.2022.730917"],
  ["A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey, and I. Sutskever, \"Robust speech recognition via large-scale weak supervision,\" *arXiv:2212.04356*, 2022 (also in *Proc. ICML*, 2023).", "10.48550/arXiv.2212.04356"],
  ["T. Javed, S. Joshi, V. Nagarajan, S. Sundaresan, J. Nawale, A. Raman, K. Bhogale, P. Kumar, and M. M. Khapra, \"Svarah: Evaluating English ASR systems on Indian accents,\" in *Proc. Interspeech*, 2023, pp. 5087–5091.", "10.21437/Interspeech.2023-2588"],
  ["A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez, Ł. Kaiser, and I. Polosukhin, \"Attention is all you need,\" *arXiv:1706.03762*, 2017 (also in *Proc. NeurIPS*, 2017).", "10.48550/arXiv.1706.03762"],
  ["S. Davis and P. Mermelstein, \"Comparison of parametric representations for monosyllabic word recognition in continuously spoken sentences,\" *IEEE Trans. Acoust., Speech, Signal Process.*, vol. 28, no. 4, pp. 357–366, 1980.", "10.1109/TASSP.1980.1163420"],
  ["L. Rabiner, \"On the use of autocorrelation analysis for pitch detection,\" *IEEE Trans. Acoust., Speech, Signal Process.*, vol. 25, no. 1, pp. 24–33, 1977.", "10.1109/TASSP.1977.1162905"],
  ["S. Boll, \"Suppression of acoustic noise in speech using spectral subtraction,\" *IEEE Trans. Acoust., Speech, Signal Process.*, vol. 27, no. 2, pp. 113–120, 1979.", "10.1109/TASSP.1979.1163209"],
  ["M. Berouti, R. Schwartz, and J. Makhoul, \"Enhancement of speech corrupted by acoustic noise,\" in *Proc. IEEE Int. Conf. Acoust., Speech, Signal Process. (ICASSP)*, vol. 4, 1979, pp. 208–211.", "10.1109/ICASSP.1979.1170788"],
  ["N. C. Camgöz, S. Hadfield, O. Koller, H. Ney, and R. Bowden, \"Neural sign language translation,\" in *Proc. IEEE/CVF Conf. Comput. Vis. Pattern Recognit. (CVPR)*, 2018, pp. 7784–7793.", "10.1109/CVPR.2018.00812"],
  ["N. C. Camgöz, O. Koller, S. Hadfield, and R. Bowden, \"Sign language transformers: Joint end-to-end sign language recognition and translation,\" in *Proc. IEEE/CVF Conf. Comput. Vis. Pattern Recognit. (CVPR)*, 2020, pp. 10020–10030.", "10.1109/CVPR42600.2020.01004"],
  ["A. Sridhar, R. G. Ganesan, P. Kumar, and M. Khapra, \"INCLUDE: A large scale dataset for Indian Sign Language recognition,\" in *Proc. 28th ACM Int. Conf. Multimedia*, 2020, pp. 1366–1375.", "10.1145/3394171.3413528"],
  ["A. Joshi, S. Agrawal, and A. Modi, \"ISLTranslate: Dataset for translating Indian Sign Language,\" in *Findings Assoc. Comput. Linguistics: ACL 2023*, 2023, pp. 10466–10475.", "10.18653/v1/2023.findings-acl.665"],
  ["A. Joshi, R. Mohanty, M. Kanakanti, A. Mangla, S. Choudhary, M. Barbate, and A. Modi, \"iSign: A benchmark for Indian Sign Language processing,\" in *Findings Assoc. Comput. Linguistics: ACL 2024*, 2024, pp. 10827–10844.", "10.18653/v1/2024.findings-acl.643"],
  ["N. Reimers and I. Gurevych, \"Sentence-BERT: Sentence embeddings using Siamese BERT-networks,\" in *Proc. Conf. Empirical Methods Natural Lang. Process. (EMNLP-IJCNLP)*, 2019, pp. 3980–3990.", "10.18653/v1/D19-1410"],
  ["G. A. Miller, \"WordNet: A lexical database for English,\" *Commun. ACM*, vol. 38, no. 11, pp. 39–41, 1995.", "10.1145/219717.219748"],
  ["B. Efron and R. J. Tibshirani, *An Introduction to the Bootstrap*. New York, NY, USA: Springer, 1993.", "10.1007/978-1-4899-4541-9"],
];
const refParas = REFS.map(([text, doi], i) => new Paragraph({
  alignment: AlignmentType.LEFT, spacing: { after: 40 },
  indent: { left: 360, hanging: 360 },
  tabStops: [{ type: TabStopType.LEFT, position: 360 }],
  children: [
    new TextRun({ text: `[${i + 1}]\t`, font: FONT, size: 16 }),
    ...runs(text + " doi: ", { size: 16 }),
    new ExternalHyperlink({ link: `https://doi.org/${doi}`,
      children: [new TextRun({ text: `https://doi.org/${doi}`, font: FONT, size: 16, color: "1F3B63", underline: {} })] }),
  ],
}));

// ── document ───────────────────────────────────────────────────────────────
const doc = new Document({
  creator: "Abhishek Karthik J, M. P. Mothishwaran",
  title: "Speech to Indian Sign Language: Accent-Adapted Speech Recognition and Dictionary-Based Sign Retrieval",
  styles: { default: { document: { run: { font: FONT, size: 20 } } } },
  numbering: { config: [{ reference: BULLET, levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 288, hanging: 180 } } } }] }] },
  sections: [
    { properties: { page: { size: PAGE, margin: MARGIN } }, children: titleBlock },
    { properties: { type: SectionType.CONTINUOUS, page: { size: PAGE, margin: MARGIN },
        column: { count: 2, space: 360, equalWidth: true } },
      children: [...body, ...refParas] },
    { properties: { type: SectionType.CONTINUOUS, page: { size: PAGE, margin: MARGIN } },
      children: [new Paragraph({ spacing: { after: 0 }, children: [] })] },
  ],
});

const out = path.join(ROOT, "report", "Speech_to_ISL_IEEE_Report.docx");
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(out, buf); console.log("wrote", out, buf.length, "bytes"); });
