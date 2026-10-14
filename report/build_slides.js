// Builds report/Speech_to_ISL_Final_Review.pptx in the same look as the mid-review
// Beamer deck (report/SPEECH_PROCESSING.pdf): white slides, numbered navy titles,
// navy-header / light-blue blocks, light-blue flow boxes, small footer.
// Run:  node report/build_slides.js   (needs the "pptxgenjs" npm package)
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const FIG = (f) => path.join(ROOT, "report", "figures", f);
const OUT = path.join(ROOT, "report", "Speech_to_ISL_Final_Review.pptx");

// colours sampled from the mid-review PDF
const NAVY = "1E375A", LIGHT = "E1EBF5", TEXT = "3C3C3C", GREY = "9AA9BF", RULE = "3C3C3C";
const FONT = "Calibri", MONO = "Courier New";
const FOOTER = "Speech Processing – Speech to Indian Sign Language";

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";              // 10 x 5.625 in
pres.author = "Mothishwaran";
pres.title = "Speech to Indian Sign Language - Final Review";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

const footer = { text: { text: FOOTER, options: { x: 0.15, y: 5.33, w: 5, h: 0.22, fontFace: FONT, fontSize: 8, color: NAVY, margin: 0 } } };
const slideNumber = { x: 9.15, y: 5.33, w: 0.6, h: 0.22, fontFace: FONT, fontSize: 8, color: TEXT, align: "right" };
pres.defineSlideMaster({ title: "TITLE", background: { color: "FFFFFF" }, objects: [footer], slideNumber });
pres.defineSlideMaster({
  title: "CONTENT", background: { color: "FFFFFF" }, slideNumber,
  objects: [footer, { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.2, w: 9, h: 0.55,
    fontFace: FONT, fontSize: 24, bold: true, color: NAVY, align: "left", valign: "middle", margin: 0 }, text: "" } }],
});

let n = 0;
function content(title) {
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText(`${++n}.  ${title}`, { placeholder: "title", align: "left" });
  return s;
}

// ── helpers ────────────────────────────────────────────────────────────────
const T = (text, o = {}) => ({ text, options: o });
function text(s, runs, o) {
  s.addText(runs, { isTextBox: true, fontFace: FONT, fontSize: 15, color: TEXT, valign: "top", margin: 0, ...o });
}
function heading(s, label, x, y, w = 4.5) {
  text(s, label, { x, y, w, h: 0.3, bold: true, fontSize: 16 });
}
// bullet list; items are strings or [boldLead, rest]
function bullets(s, items, o) {
  const runs = [];
  items.forEach((it, i) => {
    const last = i === items.length - 1;
    const para = { bullet: { indent: 14 }, paraSpaceAfter: o.gap ?? 5, breakLine: !last };
    if (Array.isArray(it)) {
      runs.push(T(it[0], { ...para, bold: true, breakLine: false }));
      runs.push(T(it[1], { breakLine: !last }));
    } else runs.push(T(it, para));
  });
  text(s, runs, o);
}
// Beamer-style block: navy title bar, light-blue body
function block(s, title, body, { x, y, w, h, size = 14 }) {
  const hh = 0.34;
  s.addText(title, { x, y, w, h: hh, fill: { color: NAVY }, color: "FFFFFF", fontFace: FONT, fontSize: 15,
    valign: "middle", margin: [8, 8, 0, 0] });
  s.addText(body, { x, y: y + hh, w, h: h - hh, fill: { color: LIGHT }, color: TEXT, fontFace: FONT, fontSize: size,
    valign: "top", margin: [8, 8, 5, 5] });
}
function box(s, label, detail, { x, y, w, h, size = 13 }) {
  const runs = detail ? [T(label, { bold: true, breakLine: true }), T(detail, { fontSize: size - 2.5 })] : [T(label, { bold: true })];
  s.addText(runs, { shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.06, x, y, w, h,
    fill: { color: LIGHT }, line: { color: NAVY, width: 0.75 }, fontFace: FONT, fontSize: size, color: TEXT,
    align: "center", valign: "middle", margin: 3 });
}
function arrow(s, x1, y1, x2, y2) {
  s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    flipH: x2 < x1, flipV: y2 < y1, line: { color: NAVY, width: 1.25, endArrowType: "triangle" } });
}
// booktabs-style table: thick top and bottom rules, thin rule under the header, no verticals
function table(s, header, rows, { x, y, w, colW, size = 12, align }) {
  const none = { type: "none" }, thick = { type: "solid", pt: 1.25, color: RULE }, thin = { type: "solid", pt: 0.6, color: RULE };
  const al = (i) => (align ? align[i] : i === 0 ? "left" : "left");
  const head = header.map((h, i) => ({ text: h, options: { bold: true, align: al(i), border: [thick, none, thin, none] } }));
  const body = rows.map((r, ri) => r.map((c, i) => ({ text: c, options: { align: al(i),
    border: [none, none, ri === rows.length - 1 ? thick : none, none] } })));
  s.addTable([head, ...body], { x, y, w, colW, fontFace: FONT, fontSize: size, color: TEXT, valign: "middle",
    margin: [2, 5, 2, 5], autoPage: false });
}
function stat(s, big, label, { x, y, w, h }) {
  s.addText([T(big, { fontSize: 26, bold: true, color: NAVY, breakLine: true }), T(label, { fontSize: 12, color: TEXT })],
    { shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.06, x, y, w, h, fill: { color: LIGHT }, fontFace: FONT,
      align: "center", valign: "middle", margin: 4 });
}
const CHART = {
  catAxisLabelFontFace: FONT, valAxisLabelFontFace: FONT, legendFontFace: FONT, titleFontFace: FONT,
  dataLabelFontFace: FONT, catAxisTitleFontFace: FONT, valAxisTitleFontFace: FONT,
  catAxisLabelColor: TEXT, valAxisLabelColor: TEXT, catAxisLabelFontSize: 10, valAxisLabelFontSize: 10,
  titleColor: NAVY, titleFontSize: 12, legendFontSize: 10, legendColor: TEXT,
  valAxisTitleColor: TEXT, catAxisTitleColor: TEXT, valAxisTitleFontSize: 10, catAxisTitleFontSize: 10,
};
const grid = () => ({ valGridLine: { color: "D9D9D9", size: 0.5 }, catGridLine: { style: "none" } });

// ── 0. title ───────────────────────────────────────────────────────────────
{
  const s = pres.addSlide({ masterName: "TITLE" });
  text(s, "Speech to Indian Sign Language", { x: 0.5, y: 0.85, w: 9, h: 0.6, fontSize: 32, bold: true, color: NAVY, align: "center" });
  text(s, "Accent-Adapted Speech Recognition and ISL Video Retrieval", { x: 0.5, y: 1.45, w: 9, h: 0.4, fontSize: 18, bold: true, color: NAVY, align: "center" });
  text(s, [T("Mothishwaran", { breakLine: true }), T("Roll No. 41", { breakLine: true }), T("AIE-A")],
    { x: 2.5, y: 2.2, w: 5, h: 0.95, fontSize: 16, align: "center" });
  text(s, [T("School of Artificial Intelligence", { breakLine: true }), T("Coimbatore")],
    { x: 2.5, y: 3.3, w: 5, h: 0.45, fontSize: 11, align: "center" });
  text(s, "Final Review – October 2026", { x: 2.5, y: 4.0, w: 5, h: 0.35, fontSize: 16, align: "center" });
}

// ── 1. problem ─────────────────────────────────────────────────────────────
{
  const s = content("Problem and Motivation");
  block(s, "The problem", "Most hearing people do not know Indian Sign Language, and trained interpreters are few. A Deaf person who signs can easily miss a lecture, an announcement or a conversation at a counter.",
    { x: 0.5, y: 0.95, w: 9, h: 1.0, size: 15 });
  heading(s, "Our idea", 0.5, 2.2);
  bullets(s, ["Take spoken English as input.", "Recognise it with a speech model tuned to Indian accents.",
    "Look up each word in the ISLRTC sign dictionary.", "Play real videos of Deaf signers, one sign after another."],
    { x: 0.5, y: 2.55, w: 4.5, h: 2.0, gap: 6 });
  heading(s, "Example", 5.4, 2.2);
  box(s, "“Where is the hospital?”", "speech", { x: 5.6, y: 2.55, w: 3.6, h: 0.5 });
  arrow(s, 7.4, 3.05, 7.4, 3.3);
  s.addText("where is the hospital", { shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.06, x: 5.6, y: 3.3, w: 3.6, h: 0.4,
    fill: { color: LIGHT }, line: { color: NAVY, width: 0.75 }, fontFace: MONO, fontSize: 13, color: TEXT, align: "center", valign: "middle" });
  arrow(s, 7.4, 3.7, 7.4, 3.95);
  box(s, "WHERE  ·  HOSPITAL", "two ISL videos (“is” and “the” are not signed in ISL)", { x: 5.6, y: 3.95, w: 3.6, h: 0.55 });
}

// ── 2. objectives ──────────────────────────────────────────────────────────
{
  const s = content("Objectives and Scope");
  heading(s, "Objectives", 0.5, 0.95);
  const obj = ["Lower recognition errors for Indian-accented English, and prove it on speakers the model never heard.",
    "Use classical speech processing (energy, zero-crossing rate, pitch, noise reduction) and measure whether it helps.",
    "Sign as many words as possible with real ISL videos, and never drop a word silently.",
    "Run in real time on a laptop."];
  text(s, obj.map((o, i) => T(o, { bullet: { type: "number" }, paraSpaceAfter: 6, breakLine: i < obj.length - 1 })),
    { x: 0.5, y: 1.3, w: 4.4, h: 2.55, fontSize: 14 });
  block(s, "Scope", [T("Speech-driven "), T("ISL video retrieval", { bold: true }), T(", not full ISL translation.")],
    { x: 0.5, y: 3.95, w: 4.4, h: 1.15 });
  heading(s, "Since the mid review", 5.3, 0.95);
  table(s, ["", "Mid review", "Final"], [
    ["Sign vocabulary", "6 signs", "4,068 local + 2,740 online"],
    ["Speech model", "stock Whisper", "fine-tuned on Indian English"],
    ["Recognition time", "833 ms (CPU)", "0.15–0.25 s (GPU)"],
    ["Speech analysis", "offline plots", "live in browser + 2 studies"],
    ["Unknown words", "names spelled", "Drive, then fingerspell"],
    ["Evaluation", "6 utterances", "16 unseen speakers + 40 sentences"],
  ], { x: 5.3, y: 1.3, w: 4.2, colW: [1.25, 1.1, 1.85], size: 11 });
}

// ── 3. literature ──────────────────────────────────────────────────────────
{
  const s = content("Literature Survey");
  table(s, ["Work", "Main idea", "Role in our project"], [
    ["Radford et al. [6]; Vaswani et al. [8]", "Whisper: Transformer ASR trained on 680k h of web audio", "Base speech recogniser"],
    ["Javed et al. (Svarah) [7]", "English ASR loses accuracy on Indian accents", "Fine-tuning and test data"],
    ["Davis & Mermelstein [9]", "Mel-scale spectral features for recognition", "Log-mel input to Whisper"],
    ["Rabiner [10]", "Autocorrelation pitch detection", "Our live pitch tracker"],
    ["Boll [11]; Berouti et al. [12]", "Spectral subtraction, over-subtraction and floor", "Our optional noise reducer"],
    ["Camgöz et al. [13], [14]", "Sign video to text with neural translation", "Opposite direction to ours"],
    ["Saunders et al. [2]; Kapoor et al. [3]", "Generate sign poses from text or speech", "Needs parallel data; avatar output"],
    ["Sridhar et al. [15]; Joshi et al. [16], [17]", "INCLUDE, ISLTranslate, iSign datasets", "No one-sign-per-clip lexicon"],
    ["Kipp et al. [4]; Quandt et al. [5]", "Deaf viewers rate signing avatars critically", "Why we use real signer videos"],
    ["Miller [19]; Reimers & Gurevych [18]", "WordNet; Sentence-BERT embeddings", "Synonym search (compared)"],
    ["Zeshan [1]; Efron & Tibshirani [20]", "ISL word order; the bootstrap", "ISL order option; significance test"],
  ], { x: 0.5, y: 0.9, w: 9, colW: [2.85, 3.55, 2.6], size: 11 });
}

// ── 4. gaps ────────────────────────────────────────────────────────────────
{
  const s = content("Research Gaps");
  const gaps = [
    ["Gap 1 – Recognition", "Speech-to-sign work rarely adapts the recogniser to Indian speakers, even though its mistakes go straight into the signs."],
    ["Gap 2 – Coverage", "Sign generation needs paired data that ISL lacks. Retrieval systems rarely report how much of a sentence they can actually sign."],
    ["Gap 3 – Classical tools", "Noise reduction and pitch cues are assumed to help, but are seldom measured with a modern neural recogniser."],
  ];
  gaps.forEach(([t, b], i) => block(s, t, b, { x: 0.5 + i * 3.075, y: 0.95, w: 2.85, h: 2.2, size: 14 }));
  block(s, "Our approach", "Fine-tune the recogniser on Indian English, retrieve real ISL videos from the full ISLRTC dictionary, and measure every step, including the ideas that did not work.",
    { x: 0.5, y: 3.5, w: 9, h: 1.05, size: 15 });
}

// ── 5. datasets ────────────────────────────────────────────────────────────
{
  const s = content("Datasets");
  heading(s, "ISLRTC sign dictionary", 0.5, 0.95);
  table(s, ["Item", "Count"], [
    ["Videos in the online archive (~250 GB)", "15,462"],
    ["Videos stored on our machine", "5,615"],
    ["Phrases in the local manifest", "4,068"],
    ["More phrases fetched on demand", "2,740"],
    ["Skipped: explanations over 30 s", "1,256"],
    ["Alphabet clips for fingerspelling", "26"],
  ], { x: 0.5, y: 1.3, w: 4.3, colW: [3.2, 1.1], size: 12, align: ["left", "right"] });
  heading(s, "Svarah speech corpus (AI4Bharat)", 5.2, 0.95);
  text(s, "6,656 utterances · 9.6 h · 117 speakers · CC BY 4.0", { x: 5.2, y: 1.3, w: 4.3, h: 0.3, fontSize: 13 });
  table(s, ["Split", "Speaker groups", "Utterances", "Hours"], [
    ["Train", "84", "5,342", "7.61"], ["Dev", "15", "694", "0.99"], ["Test", "16", "620", "1.02"],
  ], { x: 5.2, y: 1.7, w: 4.3, colW: [0.9, 1.3, 1.1, 1.0], size: 12, align: ["left", "center", "center", "center"] });
  block(s, "Two data decisions", [
    T("The videos are never redistributed. The repository keeps only the manifest, which points to the files.", { bullet: { indent: 14 }, breakLine: true, paraSpaceAfter: 4 }),
    T("Svarah file names are not speaker IDs, so we split by each speaker's demographic profile. No voice appears in two splits.", { bullet: { indent: 14 } }),
  ], { x: 0.5, y: 3.85, w: 9, h: 1.3, size: 14 });
}

// ── 6. system ──────────────────────────────────────────────────────────────
{
  const s = content("Overall System");
  const W = 1.95, H = 0.75, xs = [0.5, 2.85, 5.2, 7.55], y1 = 1.05, y2 = 2.35;
  const r1 = [["Microphone", "browser, 16 kHz mono"], ["Speech analysis", "energy, ZCR, pitch"],
    ["Noise reduction", "spectral subtraction (optional)"], ["Whisper base.en", "fine-tuned on Svarah"]];
  const r2 = [["Playback", "real ISLRTC clips"], ["Sign order", "spoken or ISL rules"],
    ["Sign lookup", "local → Drive → spell"], ["Text processing", "numbers, omitted words"]];
  r1.forEach(([a, b], i) => { box(s, a, b, { x: xs[i], y: y1, w: W, h: H }); if (i < 3) arrow(s, xs[i] + W, y1 + H / 2, xs[i + 1], y1 + H / 2); });
  r2.forEach(([a, b], i) => { box(s, a, b, { x: xs[i], y: y2, w: W, h: H }); if (i > 0) arrow(s, xs[i], y2 + H / 2, xs[i - 1] + W, y2 + H / 2); });
  arrow(s, xs[3] + W / 2, y1 + H, xs[3] + W / 2, y2);
  text(s, "Record → Analyse → Recognise → Process → Look up → Play", { x: 0.5, y: 3.5, w: 9, h: 0.4, fontSize: 18, bold: true, align: "center" });
  heading(s, "Built with", 0.5, 4.1);
  text(s, "Python · FastAPI · faster-whisper (CTranslate2) · HTML + JavaScript (Web Audio) · Google Drive API · WordNet",
    { x: 0.5, y: 4.45, w: 9, h: 0.35, fontSize: 14 });
}

// ── 7. speech processing techniques ────────────────────────────────────────
{
  const s = content("Speech Processing Techniques We Use");
  table(s, ["Technique", "Where it runs", "What it does in our system"], [
    ["Resampling to 16 kHz mono, 16-bit PCM", "Browser (Web Audio)", "One fixed format for every microphone; keeps speech up to 8 kHz"],
    ["Framing + Hann window + FFT (STFT)", "Browser and Whisper", "Live spectrogram; first step of the log-mel features"],
    ["Log-mel spectrogram, 80 bands", "Whisper front end", "80 × 3000 feature matrix the recogniser reads"],
    ["Short-time energy", "Browser", "Shows speech vs silence while recording"],
    ["Zero-crossing rate", "Browser", "Separates noisy sounds like /s/ from vowels"],
    ["Autocorrelation pitch (F0)", "Browser and server", "Live pitch track; final rise used in the question study"],
    ["Spectral subtraction", "Server (optional)", "Noise reduction before recognition; tested in 18 conditions"],
    ["Neural ASR: Whisper, fine-tuned", "Server (GPU)", "Speech to text, 11.3% WER on unseen speakers"],
    ["Text normalisation", "Server", "Turns the transcript into a clean word list"],
    ["WER, SNR, semitones", "Evaluation tools", "How each step is measured"],
  ], { x: 0.5, y: 0.95, w: 9, colW: [2.9, 1.9, 4.2], size: 12 });
}

// ── 8. capture and features ────────────────────────────────────────────────
{
  const s = content("Audio Capture and Feature Extraction");
  heading(s, "Capture, in the browser", 0.5, 0.95);
  const steps = ["MediaRecorder records the microphone.",
    "The recording is decoded and resampled to 16 kHz mono (OfflineAudioContext).",
    "Samples are written as a 16-bit PCM WAV file and uploaded.",
    "The server decodes it to a float32 array for Whisper."];
  text(s, steps.map((t, i) => T(t, { bullet: { type: "number" }, paraSpaceAfter: 3, breakLine: i < steps.length - 1 })),
    { x: 0.5, y: 1.28, w: 4.75, h: 1.65, fontSize: 13 });
  heading(s, "Features", 0.5, 3.0);
  bullets(s, [
    ["Framing: ", "25 ms frames, 10 ms hop, Hann window."],
    ["Log-mel: ", "STFT → 80 mel filters → log = Whisper input."],
    ["Energy and ZCR: ", "speech vs silence, voiced vs noisy."],
    ["Live: ", "all of these update while the user speaks."],
  ], { x: 0.5, y: 3.33, w: 4.75, h: 1.85, fontSize: 13, gap: 3 });
  s.addImage({ path: FIG("fig2_speech.png"), x: 5.5, y: 0.9, w: 4.0, h: 4.0 * 1026 / 981,
    altText: "Waveform, spectrogram and pitch track of a sample sentence" });
}

// ── 9. pitch and noise ─────────────────────────────────────────────────────
{
  const s = content("Pitch Tracking and Noise Reduction");
  const B = (t, last) => T(t, { bullet: { indent: 14 }, paraSpaceAfter: 4, breakLine: !last });
  const EQ = (t) => T(t, { fontFace: "Cambria Math", italic: true, align: "center", breakLine: true, paraSpaceAfter: 6 });
  block(s, "Pitch (F0) by autocorrelation", [
    T("Normalised autocorrelation of each frame:", { breakLine: true, paraSpaceAfter: 2 }),
    EQ("r(τ) = Σ x[n]·x[n+τ] / √(Σ x²[n] · Σ x²[n+τ])"),
    B("Search 70–400 Hz; F0 = fs / τ at the chosen peak."),
    B("Voiced when the peak is at least 0.5 and energy is above silence."),
    B("Octave guard: take the shortest peak within 10% of the best. Without it, a 330 Hz voice was read as 82.5 Hz."),
    B("Final rise in semitones: Δ = 12 log₂(F0 end / F0 body), using the last 300 ms.", true),
  ], { x: 0.5, y: 0.95, w: 4.4, h: 3.7, size: 14 });
  block(s, "Spectral subtraction", [
    T("Remove the estimated noise power from every frame:", { breakLine: true, paraSpaceAfter: 2 }),
    EQ("|Ŝ|² = max( |Y|² − α·N̂ ,  β·|Y|² )"),
    B("α = 2 (over-subtraction), β = 0.02 (spectral floor), as in Boll and Berouti."),
    B("Noise N̂ comes from the quietest 10% of frames, so no silent start is needed."),
    B("32 ms frames, 8 ms hop; the noisy phase is kept and the signal is rebuilt by overlap-add."),
    B("Sanity check: with α = 0 the output matches the input (147 dB SNR).", true),
  ], { x: 5.1, y: 0.95, w: 4.4, h: 3.7, size: 14 });
}

// ── 10. fine-tuning ─────────────────────────────────────────────────────────
{
  const s = content("Fine-Tuning Whisper on Indian Accents");
  table(s, ["Setting", "Value"], [
    ["Base model", "Whisper base.en (74 M parameters)"],
    ["Training data", "Svarah train split, 84 speaker groups"],
    ["Epochs / steps", "3 / 1,002"],
    ["Batch size", "16"],
    ["Optimiser", "AdamW, lr 1×10⁻⁵, 100 warm-up steps"],
    ["Precision", "mixed (fp16)"],
    ["Hardware / time", "RTX 4050 laptop GPU, 69 min"],
    ["Checkpoint kept", "step 600 (lowest dev WER)"],
    ["Exported as", "CTranslate2, 8-bit, 76 MB"],
  ], { x: 0.5, y: 0.95, w: 4.5, colW: [1.5, 3.0], size: 12 });
  s.addChart(pres.charts.LINE, [{ name: "Dev WER", labels: ["0", "200", "400", "600", "800", "1000"], values: [11.84, 9.77, 9.14, 8.95, 9.24, 8.98] }], {
    x: 5.3, y: 0.9, w: 4.2, h: 2.75, ...CHART, ...grid(), chartColors: [NAVY], lineSize: 2, lineDataSymbol: "circle", lineDataSymbolSize: 7,
    showTitle: true, title: "WER on the 15 dev speakers (%)", showLegend: false, showValue: true, dataLabelPosition: "t",
    dataLabelFontSize: 9, dataLabelColor: TEXT, dataLabelFormatCode: "0.00", valAxisMinVal: 8, valAxisMaxVal: 12.5, valAxisMajorUnit: 1,
    valAxisLabelFormatCode: "0", showCatAxisTitle: true, catAxisTitle: "training step",
  });
  bullets(s, ["Dev WER fell from 11.84% to 8.95% by step 600, then stopped improving.",
    "Checkpoints save the optimiser and random state, so a teammate can resume on another machine."],
  { x: 5.3, y: 3.8, w: 4.2, h: 1.3, fontSize: 13 });
}

// ── 11. recognition results ────────────────────────────────────────────────
{
  const s = content("Results: Recognition on Unseen Speakers");
  stat(s, "13.2% → 11.3%", "test WER, 620 utterances (about 14% fewer errors)", { x: 0.5, y: 0.95, w: 2.75, h: 1.2 });
  stat(s, "14 of 16", "unseen test speakers improved", { x: 0.5, y: 2.35, w: 2.75, h: 1.2 });
  stat(s, "2,000 / 2,000", "bootstrap resamples favour the fine-tuned model", { x: 0.5, y: 3.75, w: 2.75, h: 1.2 });
  const stock = [5.9, 7.8, 8.1, 10.3, 10.7, 11.9, 13.3, 14.5, 14.6, 14.9, 16.0, 18.2, 19.6, 21.7, 37.4, 53.8];
  const tuned = [6.3, 7.5, 5.9, 10.0, 9.3, 8.3, 10.9, 10.6, 11.1, 15.4, 13.4, 15.2, 10.6, 19.3, 28.2, 41.0];
  const labels = stock.map((_, i) => String(i + 1));
  s.addChart(pres.charts.BAR, [{ name: "Stock base.en", labels, values: stock }, { name: "Fine-tuned", labels, values: tuned }], {
    x: 3.55, y: 0.9, w: 5.95, h: 2.85, ...CHART, ...grid(), barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
    chartColors: [GREY, NAVY], showTitle: true, title: "WER per test speaker (%), sorted by stock WER",
    showLegend: true, legendPos: "t", valAxisLabelFormatCode: "0",
  });
  bullets(s, ["Biggest gains on the hardest voices: 53.8 → 41.0, 37.4 → 28.2, 19.6 → 10.6.",
    "Two speakers got slightly worse, by 0.4 and 0.5 points.",
    "Running both models and keeping the more confident output gave 11.25%, not worth twice the compute."],
  { x: 3.55, y: 3.85, w: 5.95, h: 1.3, fontSize: 13, gap: 3 });
}

// ── 12. text cleaning ──────────────────────────────────────────────────────
{
  const s = content("Text Cleaning and Normalisation");
  heading(s, "Steps applied to the Whisper transcript", 0.5, 0.95);
  const steps = ["Split the transcript into words at spaces.",
    "Strip punctuation from both ends of each word.",
    "Lower-case, and turn curly apostrophes (’) into straight ones (').",
    "Keep only letters, digits and apostrophes, so don't stays one word.",
    "Mark where sentences start (after . ? ! : ;) for names and questions.",
    "Keep the original form too: capitals mark names, digits mark numbers."];
  text(s, steps.map((t, i) => T(t, { bullet: { type: "number" }, paraSpaceAfter: 4, breakLine: i < steps.length - 1 })),
    { x: 0.5, y: 1.3, w: 4.4, h: 2.75, fontSize: 13 });
  block(s, "Same rules on both sides", "Every dictionary phrase is cleaned by the same function when the manifest is built, so speech and dictionary never disagree on spelling.",
    { x: 0.5, y: 4.0, w: 4.4, h: 1.15, size: 13 });
  heading(s, "Example", 5.2, 0.95);
  box(s, "“Hello, my friend Ravi! Don’t worry, the doctors come at 7:30.”", "Whisper output", { x: 5.2, y: 1.3, w: 4.3, h: 0.65, size: 12 });
  arrow(s, 7.35, 1.95, 7.35, 2.2);
  table(s, ["Original", "Cleaned", "Starts sentence"], [
    ["Hello,", "hello", "yes"], ["Ravi!", "ravi", "no (capital → name)"], ["Don’t", "don't", "yes"],
    ["doctors", "doctors", "no"], ["7:30.", "7:30 → number", "no"],
  ], { x: 5.2, y: 2.25, w: 4.3, colW: [1.1, 1.4, 1.8], size: 12 });
  text(s, "hello my friend ravi don't worry the doctors come at 730", { x: 5.2, y: 4.35, w: 4.3, h: 0.5, fontSize: 11, fontFace: MONO, color: NAVY });
}

// ── 13. words to signs ─────────────────────────────────────────────────────
{
  const s = content("From Words to Signs");
  const chain = ["Local dictionary", "Google Drive", "Number", "Name", "Omitted word", "Word form", "Reviewed synonym", "Fingerspell"];
  const W = 1.02, gap = 0.117;
  chain.forEach((c, i) => {
    box(s, c, null, { x: 0.5 + i * (W + gap), y: 0.95, w: W, h: 0.5, size: 10.5 });
    if (i < chain.length - 1) arrow(s, 0.5 + i * (W + gap) + W, 1.2, 0.5 + (i + 1) * (W + gap), 1.2);
  });
  text(s, "Longest dictionary phrase first (“thank you” = one sign); words left over go through the chain in this order.",
    { x: 0.5, y: 1.55, w: 9, h: 0.3, fontSize: 12 });
  table(s, ["Word", "Rule that fired", "Played"], [
    ["Hello, my, friend, worry, come", "local dictionary", "HELLO, MY, FRIEND, WORRY, COME"],
    ["Ravi", "capital letter mid-sentence → name", "R-A-V-I (fingerspelled)"],
    ["Don’t", "not on this laptop → Google Drive, then cached", "DON'T"],
    ["the", "omitted word (ISL does not sign it)", "—"],
    ["doctors", "word form", "DOCTOR"],
    ["at", "no sign anywhere", "A-T (fingerspelled)"],
    ["7:30", "number reading", "SEVEN THIRTY"],
  ], { x: 0.5, y: 1.95, w: 9, colW: [2.5, 3.6, 2.9], size: 12 });
  block(s, "Result", "11 words → 8 signed, 2 fingerspelled, 1 omitted, none dropped. (45 → FOUR FIVE: forty has no sign.)",
    { x: 0.5, y: 4.25, w: 9, h: 0.9, size: 13 });
}

// ── 14. synonyms ───────────────────────────────────────────────────────────
{
  const s = content("Synonyms: Embeddings vs WordNet");
  heading(s, "Test: 30 true synonym pairs, 30 related but different pairs", 0.5, 0.95, 9);
  table(s, ["Method", "True pairs accepted", "Wrong pairs accepted"], [
    ["Embeddings, threshold 0.70", "18 / 30", "8 / 30"],
    ["Embeddings, threshold 0.80", "12 / 30", "2 / 30"],
    ["Embeddings, threshold 0.85", "7 / 30", "2 / 30"],
    ["WordNet", "11 / 30", "0 / 30"],
  ], { x: 0.5, y: 1.35, w: 4.6, colW: [2.3, 1.15, 1.15], size: 12, align: ["left", "center", "center"] });
  bullets(s, ["Embeddings scored Monday–Tuesday and husband–wife at 0.87, higher than many real synonyms.",
    "Showing the sign for a different word is worse than showing nothing.",
    "WordNet proposals were checked by hand: 121 of 171 kept.",
    "984 word forms are also mapped, e.g. children → CHILD."],
  { x: 5.4, y: 1.35, w: 4.1, h: 2.5, fontSize: 14, gap: 6 });
  block(s, "Decision", "WordNet with manual review is used. Embedding similarity was tested and rejected.",
    { x: 0.5, y: 4.05, w: 9, h: 0.85, size: 15 });
}

// ── 15. start to finish ────────────────────────────────────────────────────────
{
  const s = content("Start to Finish: One Sentence Through the System");
  table(s, ["Step", "What happens", "Output", "Time"], [
    ["1. Record", "Browser records, resamples to 16 kHz mono; live waveform, spectrogram, pitch", "WAV file", "while speaking"],
    ["2. Denoise", "Optional spectral subtraction", "cleaner audio", "~22 ms (off by default)"],
    ["3. Recognise", "Fine-tuned Whisper, greedy decoding", "“Where is the hospital? I am 25 years old.”", "0.15–0.25 s GPU"],
    ["4. Clean", "Split, strip punctuation, lower-case, mark sentences", "where is the hospital i am 25 years old", "< 1 ms"],
    ["5. Question?", "“where” + verb, and a “?”", "sentence 1 is a question", "< 1 ms"],
    ["6. Look up", "Longest phrase first, then the chain", "WHERE HOSPITAL TWENTY FIVE YEAR OLD", "< 1 ms"],
    ["7. Order", "Spoken order (ISL option: HOSPITAL WHERE …)", "play list of 6 clips", "< 1 ms"],
    ["8. Play", "Two video players alternate, so there is no gap", "6 real ISL videos", "clip length (median 7.9 s)"],
  ], { x: 0.5, y: 0.95, w: 9, colW: [1.15, 3.35, 3.1, 1.4], size: 11 });
  block(s, "Where the time goes", "Recognition is almost all of the waiting: 0.15–0.25 s on the GPU against 1.6 s (plugged in) or 3.1 s (battery) on the CPU. A sign fetched from Google Drive adds about 5.6 s the first time only.",
    { x: 0.5, y: 4.15, w: 9, h: 1.0, size: 13 });
}

// ── 16. noise ──────────────────────────────────────────────────────────────
{
  const s = content("Results: Noise Robustness");
  const labels = ["clean", "20 dB", "10 dB", "5 dB", "0 dB"];
  const series = (st, sts, ft, fts) => [
    { name: "Stock", labels, values: st }, { name: "Stock + SS", labels, values: sts },
    { name: "Fine-tuned", labels, values: ft }, { name: "Fine-tuned + SS", labels, values: fts }];
  const noiseChart = (title, data, x) => s.addChart(pres.charts.LINE, data, {
    x, y: 0.9, w: 4.4, h: 2.75, ...CHART, ...grid(), chartColors: [GREY, "C9A227", NAVY, "B03A2E"], lineSize: 2,
    lineDataSymbol: "circle", lineDataSymbolSize: 5, showTitle: true, title, showLegend: true, legendPos: "b",
    valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 20, valAxisLabelFormatCode: "0",
  });
  noiseChart("WER (%) with white noise", series([13.1, 16.6, 28.3, 44.9, 67.7], [13.6, 17.2, 28.8, 43.9, 73.6], [11.0, 13.4, 25.4, 34.5, 55.6], [11.9, 14.0, 24.5, 36.5, 59.8]), 0.5);
  noiseChart("WER (%) with babble noise", series([13.1, 14.4, 22.2, 41.5, 88.2], [13.6, 14.8, 25.8, 47.4, 95.1], [11.0, 12.8, 21.1, 36.8, 92.2], [11.9, 13.9, 21.3, 39.8, 88.5]), 5.1);
  bullets(s, ["200 test utterances mixed with white noise and four-speaker babble at 20, 10, 5 and 0 dB. SS = spectral subtraction.",
    "The fine-tuned model was more robust at every white-noise level (5 dB: 44.9% → 34.5%), though it never heard added noise in training.",
    "Spectral subtraction raised SNR by 3.7–7.1 dB on white noise and under 1 dB on babble, but made WER worse in 15 of 18 conditions. It is off by default."],
  { x: 0.5, y: 3.8, w: 9, h: 1.4, fontSize: 13, gap: 3 });
}

// ── 17. question cue ───────────────────────────────────────────────────────
{
  const s = content("Results: Pitch as a Question Cue");
  s.addChart(pres.charts.BAR, [{ name: "Median final movement", labels: ["yes/no question", "wh-question", "statement"], values: [-0.3, -2.6, -2.17] }], {
    x: 0.5, y: 0.9, w: 4.3, h: 2.6, ...CHART, ...grid(), barDir: "col", chartColors: [NAVY], showLegend: false,
    showTitle: true, title: "Median final pitch movement (semitones)", showValue: true, dataLabelFormatCode: "0.0",
    dataLabelFontSize: 10, dataLabelColor: TEXT, valAxisMinVal: -3, valAxisMaxVal: 0.5, valAxisLabelFormatCode: "0.0",
  });
  text(s, "387 questions and 387 statements from Svarah; threshold set on training speakers only.",
    { x: 0.5, y: 3.55, w: 4.3, h: 0.45, fontSize: 11 });
  heading(s, "Tested on unseen dev + test speakers", 5.1, 0.95);
  table(s, ["Method", "Questions found", "Statements flagged"], [
    ["Pitch alone (yes/no only)", "44.7%", "11.8%"],
    ["Word order + “?”", "79 / 85", "1 / 70"],
    ["Word order, “?” removed", "61 / 85", "1 / 70"],
  ], { x: 5.1, y: 1.3, w: 4.4, colW: [2.0, 1.2, 1.2], size: 12, align: ["left", "center", "center"] });
  text(s, "Pitch alone reaches only 66.5% balanced accuracy.", { x: 5.1, y: 2.75, w: 4.4, h: 0.3, fontSize: 12 });
  block(s, "Finding", "In read Indian English, yes/no questions did not rise at the end; they only fell less than statements. So word order decides, and pitch is shown as supporting evidence.",
    { x: 0.5, y: 4.05, w: 9, h: 1.05, size: 14 });
}

// ── 18. coverage ───────────────────────────────────────────────────────────
{
  const s = content("Results: Sign Coverage");
  const labels = ["All words", "Words ISL signs", "+ Google Drive", "+ Synonyms"];
  s.addChart(pres.charts.BAR, [{ name: "Development sentences", labels, values: [74.0, 86.5, 86.5, 86.5] },
    { name: "Held-out sentences", labels, values: [53.9, 66.3, 67.1, 72.3] }], {
    x: 0.5, y: 0.9, w: 5.4, h: 4.2, ...CHART, ...grid(), barDir: "col", barGrouping: "clustered", barGapWidthPct: 50,
    chartColors: [GREY, NAVY], showTitle: true, title: "Words that get a dictionary sign (%)", showLegend: true, legendPos: "t",
    showValue: true, dataLabelFormatCode: "0", dataLabelFontSize: 10, dataLabelColor: TEXT, valAxisMinVal: 0, valAxisMaxVal: 100,
    valAxisLabelFormatCode: "0",
  });
  bullets(s, ["Held-out sentences were written after all rules were fixed, so these are the honest numbers.",
    "66% of the words ISL signs had a local sign; Drive raised it to 67% and synonyms to 72%.",
    "The development set reached 87%. Tuning on your own test set inflates results.",
    "Spoken end to end with a synthetic voice: WER 2.0% and 2.4%, and every clip was served."],
  { x: 6.2, y: 1.0, w: 3.3, h: 4.1, fontSize: 13, gap: 8 });
}

// ── 19. demonstration ──────────────────────────────────────────────────────
{
  const s = content("End-to-End Demonstration");
  heading(s, "Input speech", 0.5, 0.95);
  text(s, "“Where is the hospital? I am 25 years old.”", { x: 0.5, y: 1.25, w: 4.3, h: 0.3, fontSize: 14 });
  heading(s, "Whisper output", 0.5, 1.65);
  text(s, "where is the hospital i am 25 years old", { x: 0.5, y: 1.95, w: 4.3, h: 0.3, fontSize: 12, fontFace: MONO });
  heading(s, "Playback plan", 0.5, 2.35);
  bullets(s, ["where → WHERE;  hospital → HOSPITAL", "is, the, am → omitted (not signed in ISL)",
    "25 → TWENTY FIVE;  years → YEAR (word form)", "old → OLD", "I → no dictionary sign; not spelled, since a lone letter I would mislead"],
  { x: 0.5, y: 2.7, w: 4.3, h: 2.4, fontSize: 13, gap: 4 });
  s.addImage({ path: FIG("fig7_signs.png"), x: 5.0, y: 0.95, w: 4.5, h: 4.5 * 508 / 990, altText: "Frames from the six sign clips played for the sentence" });
  block(s, "With ISL order switched on", "HOSPITAL WHERE  TWENTY FIVE YEAR OLD  (question word moved to the end)",
    { x: 5.0, y: 3.5, w: 4.5, h: 1.0, size: 13 });
}

// ── 20. what we learned ────────────────────────────────────────────────────
{
  const s = content("What We Learned");
  const finding = (title, items, x, y) => { heading(s, title, x, y, 4.4); bullets(s, items, { x, y: y + 0.32, w: 4.4, h: 1.6, fontSize: 13, gap: 3 }); };
  finding("Finding 1 – Short phrases are hard", ["“cricket match” alone was misheard by all three models: “trickier to match”, “click here to match”, “couldn't get the match”.",
    "This is why we added the correction box."], 0.5, 0.95);
  finding("Finding 2 – Averages hide word errors", ["In “I play cricket and hockey” the fine-tuned model wrote “chicken”; the stock model and small.en were right.",
    "Lower average WER does not mean every word improves."], 5.1, 0.95);
  finding("Finding 3 – Check the data, not only the code", ["Svarah file names looked like speaker IDs but were not; splitting on them would have leaked test voices.",
    "Alphabet clips were stamped 0.03 s instead of 1.5 s, so fingerspelling was unreadable until re-timed."], 0.5, 3.0);
  finding("Finding 4 – Meaning needs a human", ["WordNet proposed million → billion and chess → grass.",
    "Manual review removed 50 of 171 synonym proposals."], 5.1, 3.0);
}

// ── 21. limitations ────────────────────────────────────────────────────────
{
  const s = content("Limitations");
  bullets(s, [
    "Signs follow English order unless the ISL-order option is on, and that option knows only three rules.",
    "Facial expressions carry ISL grammar (raised eyebrows for yes/no questions); joined dictionary clips cannot show them.",
    "Synonyms were checked for English meaning, not by an ISL signer.",
    "Recognition was tested on Svarah and synthetic speech; tests with our own voices are still few.",
    "Some common words, such as the pronoun I, have no dictionary sign.",
    "1,256 long explanation videos are skipped until an ISL user marks the sign inside them.",
  ], { x: 0.5, y: 0.95, w: 9, h: 2.9, fontSize: 15, gap: 6 });
  block(s, "Most important limitation", [T("No Deaf user has judged the output yet. Coverage tells us what the dictionary "),
    T("can express", { bold: true }), T(", not what a viewer "), T("understands", { bold: true }), T(".")],
  { x: 0.5, y: 3.95, w: 9, h: 1.15, size: 15 });
}

// ── 22. conclusion ─────────────────────────────────────────────────────────
{
  const s = content("Conclusion and Future Work");
  block(s, "What we have achieved", "A working system that turns spoken Indian English into a sequence of real ISL dictionary videos, with recognition in under a quarter of a second on a laptop GPU.",
    { x: 0.5, y: 0.95, w: 9, h: 1.0, size: 15 });
  heading(s, "Key results", 0.5, 2.15);
  bullets(s, ["WER 13.2% → 11.3% on unseen speakers, and more robust to noise.",
    "67% of ISL-signed words covered in unseen sentences (72% with synonyms).",
    "Two honest negative results: spectral subtraction and pitch-only question detection."],
  { x: 0.5, y: 2.5, w: 4.4, h: 1.9, fontSize: 14, gap: 5 });
  heading(s, "Future work", 5.1, 2.15);
  bullets(s, ["Evaluate with Deaf ISL users.", "Train on more, and noisier, Indian speech.",
    "Learn ISL word order from parallel data such as ISLTranslate.", "Mark the sign inside long explanation videos with an ISL expert."],
  { x: 5.1, y: 2.5, w: 4.4, h: 1.9, fontSize: 14, gap: 5 });
  text(s, "Speech → Fine-tuned Whisper → Text → Sign lookup → Real ISL video", { x: 0.5, y: 4.55, w: 9, h: 0.4, fontSize: 17, bold: true, align: "center" });
}

// ── references ─────────────────────────────────────────────────────────────
const REFS = [
  "U. Zeshan, “Indo-Pakistani Sign Language grammar: A typological outline,” Sign Lang. Stud., 2003. doi:10.1353/sls.2003.0005",
  "B. Saunders, N. C. Camgöz, R. Bowden, “Progressive transformers for end-to-end sign language production,” ECCV, 2020. doi:10.1007/978-3-030-58621-8_40",
  "P. Kapoor et al., “Towards automatic speech to sign language generation,” Interspeech, 2021. doi:10.21437/Interspeech.2021-1094",
  "M. Kipp et al., “Assessing the deaf user perspective on sign language avatars,” ASSETS, 2011. doi:10.1145/2049536.2049557",
  "L. C. Quandt et al., “Attitudes toward signing avatars vary depending on hearing status, age of signed language acquisition, and avatar type,” Front. Psychol., 2022. doi:10.3389/fpsyg.2022.730917",
  "A. Radford et al., “Robust speech recognition via large-scale weak supervision,” arXiv:2212.04356, 2022. doi:10.48550/arXiv.2212.04356",
  "T. Javed et al., “Svarah: Evaluating English ASR systems on Indian accents,” Interspeech, 2023. doi:10.21437/Interspeech.2023-2588",
  "A. Vaswani et al., “Attention is all you need,” arXiv:1706.03762, 2017. doi:10.48550/arXiv.1706.03762",
  "S. Davis, P. Mermelstein, “Comparison of parametric representations for monosyllabic word recognition,” IEEE Trans. ASSP, 1980. doi:10.1109/TASSP.1980.1163420",
  "L. Rabiner, “On the use of autocorrelation analysis for pitch detection,” IEEE Trans. ASSP, 1977. doi:10.1109/TASSP.1977.1162905",
  "S. Boll, “Suppression of acoustic noise in speech using spectral subtraction,” IEEE Trans. ASSP, 1979. doi:10.1109/TASSP.1979.1163209",
  "M. Berouti, R. Schwartz, J. Makhoul, “Enhancement of speech corrupted by acoustic noise,” ICASSP, 1979. doi:10.1109/ICASSP.1979.1170788",
  "N. C. Camgöz et al., “Neural sign language translation,” CVPR, 2018. doi:10.1109/CVPR.2018.00812",
  "N. C. Camgöz et al., “Sign language transformers: Joint end-to-end sign language recognition and translation,” CVPR, 2020. doi:10.1109/CVPR42600.2020.01004",
  "A. Sridhar et al., “INCLUDE: A large scale dataset for Indian Sign Language recognition,” ACM Multimedia, 2020. doi:10.1145/3394171.3413528",
  "A. Joshi, S. Agrawal, A. Modi, “ISLTranslate: Dataset for translating Indian Sign Language,” Findings of ACL, 2023. doi:10.18653/v1/2023.findings-acl.665",
  "A. Joshi et al., “iSign: A benchmark for Indian Sign Language processing,” Findings of ACL, 2024. doi:10.18653/v1/2024.findings-acl.643",
  "N. Reimers, I. Gurevych, “Sentence-BERT: Sentence embeddings using Siamese BERT-networks,” EMNLP-IJCNLP, 2019. doi:10.18653/v1/D19-1410",
  "G. A. Miller, “WordNet: A lexical database for English,” Commun. ACM, 1995. doi:10.1145/219717.219748",
  "B. Efron, R. J. Tibshirani, An Introduction to the Bootstrap. Springer, 1993. doi:10.1007/978-1-4899-4541-9",
];
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("References", { placeholder: "title", align: "left" });
  const col = (a, b, x) => text(s, REFS.slice(a, b).map((r, i) => {
    const k = r.lastIndexOf("doi:");
    return [T(`[${a + i + 1}] ${r.slice(0, k)}`, { paraSpaceAfter: 3, breakLine: false }),
      T(r.slice(k), { color: NAVY, hyperlink: { url: "https://doi.org/" + r.slice(k + 4) }, breakLine: i < b - a - 1 })];
  }).flat(), { x, y: 0.85, w: 4.4, h: 4.4, fontSize: 10 });
  col(0, 10, 0.5);
  col(10, 20, 5.1);
}

// ── thank you ──────────────────────────────────────────────────────────────
{
  const s = pres.addSlide({ masterName: "TITLE" });
  text(s, "Thank You", { x: 0.5, y: 1.2, w: 9, h: 0.9, fontSize: 44, bold: true, align: "center" });
  text(s, "Questions?", { x: 0.5, y: 2.15, w: 9, h: 0.5, fontSize: 22, align: "center" });
  s.addText([T("Speech Recognition + Speech Processing", { breakLine: true }), T("+ Retrieval + Real ISL Video")], {
    shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.08, x: 2.85, y: 3.05, w: 4.3, h: 0.75, fill: { color: LIGHT },
    line: { color: NAVY, width: 0.75 }, fontFace: FONT, fontSize: 16, bold: true, color: TEXT, align: "center", valign: "middle" });
}

pres.writeFile({ fileName: OUT }).then((f) => console.log("wrote", f, "slides:", pres.slides.length));
