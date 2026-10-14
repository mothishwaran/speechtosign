"""Figures for the IEEE-format report, sized for one 3.5-inch column.

White backgrounds and Times New Roman throughout (the evaluation rules penalise
dark screenshots and require legible standard fonts in diagram blocks). Every
plot is computed from committed project data.

Run from the project root:  python report/make_figures.py
"""
import csv
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

sys.path.insert(0, os.getcwd())
OUT = "report/figures"
os.makedirs(OUT, exist_ok=True)
COL_W = 3.45          # inches, one IEEE column
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "figure.dpi": 300, "savefig.dpi": 300,
    "axes.grid": True, "grid.alpha": 0.3, "axes.linewidth": 0.6, "lines.linewidth": 1.0,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})


def save(fig, name):
    fig.savefig(f"{OUT}/{name}.png", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print("wrote", name)


# ── Fig. 1: system flow diagram ───────────────────────────────────────────────
def flow():
    steps = [
        ("Microphone (browser)", "record, resample to 16 kHz mono, 16-bit"),
        ("Speech analysis", "framing, STFT, energy, ZCR, autocorrelation F0"),
        ("Optional noise reduction", "spectral subtraction (off by default)"),
        ("Speech recognition", "Whisper base.en fine-tuned on Svarah (GPU)"),
        ("Text processing", "normalise, numbers, omitted words, questions"),
        ("Sign lookup", "local dictionary  >  Google Drive  >  word forms\n>  reviewed synonyms  >  fingerspelling"),
        ("Sign ordering", "spoken order (default) or ISL rules"),
        ("Playback", "ISLRTC clips played back-to-back"),
    ]
    GAP = 0.42
    heights = [1.25 if "\n" in d else 0.95 for _, d in steps]
    total = sum(heights) + GAP * (len(steps) - 1)
    fig, ax = plt.subplots(figsize=(COL_W, 5.2))
    ax.set_xlim(0, 10); ax.set_ylim(-0.05, total + 0.05); ax.axis("off")
    top = total
    for i, ((title, detail), h) in enumerate(zip(steps, heights)):
        y = top - h                                   # bottom edge of this box
        ax.add_patch(FancyBboxPatch((0.4, y), 9.2, h, boxstyle="round,pad=0.0,rounding_size=0.12",
                                    linewidth=0.8, edgecolor="#1f3b63", facecolor="#e8eef7"))
        ax.text(5, top - 0.30, title, ha="center", va="center", fontsize=8.5, fontweight="bold")
        ax.text(5, (y + top - 0.52) / 2, detail, ha="center", va="center", fontsize=7, linespacing=1.15)
        if i < len(steps) - 1:                        # one arrow, in the gap only
            ax.annotate("", xy=(5, y - GAP + 0.02), xytext=(5, y - 0.02),
                        arrowprops=dict(arrowstyle="-|>", lw=0.9, color="#1f3b63",
                                        shrinkA=0, shrinkB=0, mutation_scale=7))
        top = y - GAP
    save(fig, "fig1_flow")


# ── Fig. 2: speech analysis of the demo recording ─────────────────────────────
def speech():
    from faster_whisper import decode_audio
    from src import prosody
    x = decode_audio("eval/sample.wav", sampling_rate=16000)
    sr = 16000
    times, f0 = prosody.f0_track(x)
    fig, ax = plt.subplots(3, 1, figsize=(COL_W, 3.6), sharex=True)
    t = np.arange(len(x)) / sr
    ax[0].plot(t, x, lw=0.3, color="#1f3b63"); ax[0].set_ylabel("amplitude")
    ax[0].set_title("(a) waveform", loc="left")
    with np.errstate(divide="ignore"):
        ax[1].specgram(x, NFFT=512, Fs=sr, noverlap=352, cmap="Greys", vmin=-110)
    ax[1].set_ylim(0, 5000); ax[1].set_ylabel("Hz"); ax[1].grid(False)
    ax[1].set_title("(b) spectrogram (32 ms Hann, 10 ms hop)", loc="left")
    ax[2].plot(times, f0, ".", ms=1.6, color="#b03a2e"); ax[2].set_ylim(60, 220)
    ax[2].set_ylabel("F0 (Hz)"); ax[2].set_xlabel("time (s)")
    ax[2].set_title("(c) pitch from normalised autocorrelation", loc="left")
    fig.tight_layout(h_pad=0.4)
    save(fig, "fig2_speech")


# ── Fig. 3: fine-tuning curve and test WER ────────────────────────────────────
def training():
    import jiwer
    from tools.train.metrics import normalize
    log = list(csv.DictReader(open("eval/train_log_base_en_svarah.csv", encoding="utf-8")))
    st = [int(r["step"]) for r in log if r["dev_wer"]]
    dv = [100 * float(r["dev_wer"]) for r in log if r["dev_wer"]]
    hyps = list(csv.DictReader(open("eval/asr_svarah_test_hyps.csv", encoding="utf-8")))

    def wer(m):
        p = [(normalize(r["reference"]), normalize(r["hypothesis"])) for r in hyps if r["model"] == m]
        p = [q for q in p if q[0].strip()]
        return 100 * jiwer.wer([a for a, _ in p], [b for _, b in p])
    fig, ax = plt.subplots(1, 2, figsize=(COL_W, 1.7), gridspec_kw={"width_ratios": [1.5, 1]})
    ax[0].plot(st, dv, "o-", ms=3, color="#1f3b63")
    b = int(np.argmin(dv))
    ax[0].annotate(f"best {dv[b]:.2f}%", (st[b], dv[b]), textcoords="offset points", xytext=(0, 7),
                   ha="center", fontsize=6.5)
    ax[0].set_xlabel("training step"); ax[0].set_ylabel("dev WER (%)")
    ax[0].set_title("(a) dev speakers", loc="left")
    vals = [wer("base.en"), wer("whisper-base-en-svarah")]
    bars = ax[1].bar(["stock", "fine-tuned"], vals, color=["#9aa9bf", "#1f3b63"], width=0.6)
    ax[1].bar_label(bars, fmt="%.1f%%", fontsize=6.5); ax[1].set_ylim(0, 16)
    ax[1].set_title("(b) test speakers", loc="left"); ax[1].set_ylabel("WER (%)")
    fig.tight_layout(w_pad=0.8)
    save(fig, "fig3_training")


# ── Fig. 4: per-speaker WER on the unseen test speakers ───────────────────────
def speakers():
    import jiwer
    from collections import defaultdict
    from tools.train.metrics import normalize
    hyps = list(csv.DictReader(open("eval/asr_svarah_test_hyps.csv", encoding="utf-8")))
    acc = defaultdict(lambda: {"base.en": [0, 0], "whisper-base-en-svarah": [0, 0]})
    for r in hyps:
        ref, hyp = normalize(r["reference"]), normalize(r["hypothesis"])
        if not ref.strip():
            continue
        o = jiwer.process_words(ref, hyp)
        acc[r["speaker"]][r["model"]][0] += o.substitutions + o.deletions + o.insertions
        acc[r["speaker"]][r["model"]][1] += len(ref.split())
    pairs = sorted((100 * v["base.en"][0] / v["base.en"][1],
                    100 * v["whisper-base-en-svarah"][0] / v["whisper-base-en-svarah"][1]) for v in acc.values())
    fig, ax = plt.subplots(figsize=(COL_W, 1.8))
    xs = np.arange(len(pairs))
    ax.bar(xs - 0.2, [a for a, _ in pairs], 0.4, label="stock base.en", color="#9aa9bf")
    ax.bar(xs + 0.2, [b for _, b in pairs], 0.4, label="fine-tuned", color="#1f3b63")
    ax.set_xticks(xs, [str(i + 1) for i in xs]); ax.set_xlabel("test speaker (sorted by stock WER)")
    ax.set_ylabel("WER (%)"); ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    save(fig, "fig4_speakers")


# ── Fig. 5: noise robustness ──────────────────────────────────────────────────
def noise():
    rows = list(csv.DictReader(open("eval/noise_study.csv", encoding="utf-8")))

    def w(m, n, s, d):
        return next(100 * float(r["wer"]) for r in rows if r["model"] == m and r["noise"] == n
                    and r["snr_db"] == s and r["denoise"] == str(d))
    levels = ["20", "10", "5", "0"]
    xs = ["clean"] + [f"{l} dB" for l in levels]
    fig, ax = plt.subplots(2, 1, figsize=(COL_W, 3.0), sharex=True)
    for a, noise_kind in zip(ax, ["white", "babble"]):
        for m, c, lab in [("base.en", "#9aa9bf", "stock"), ("whisper-base-en-svarah", "#1f3b63", "fine-tuned")]:
            for d, ls in [(0, "-"), (1, "--")]:
                ys = [w(m, "clean", "", d)] + [w(m, noise_kind, l, d) for l in levels]
                a.plot(xs, ys, ls, marker="o", ms=2.5, color=c,
                       label=lab + (" + spectral subtraction" if d else ""))
        a.set_ylabel("WER (%)"); a.set_title(f"({'a' if noise_kind == 'white' else 'b'}) {noise_kind} noise", loc="left")
    ax[0].legend(frameon=False, fontsize=6.3, handlelength=3, loc="upper left")
    ax[1].set_xlabel("signal-to-noise ratio")
    fig.tight_layout(h_pad=0.4)
    save(fig, "fig5_noise")


# ── Fig. 6: sign coverage ─────────────────────────────────────────────────────
def coverage():
    import statistics
    from src import matcher

    def cov(path):
        s = [l.strip() for l in open(path, encoding="utf-8") if l.strip()]
        loc = [matcher.match(x, use_drive=False, use_related=False) for x in s]
        full = [matcher.match(x) for x in s]
        p = lambda ms, k: 100 * statistics.mean(m[k] for m in ms)
        return [p(loc, "coverage"), p(loc, "content_coverage"), p(full, "content_coverage"),
                p(full, "content_coverage_with_similar")]
    labels = ["all words", "ISL-signed\nwords", "+ Drive", "+ synonyms"]
    res = {"everyday": cov("eval/test_sentences.txt"), "held-out": cov("eval/test_sentences_heldout.txt")}
    fig, ax = plt.subplots(figsize=(COL_W, 1.9))
    x = np.arange(len(labels))
    for i, (name, vals) in enumerate(res.items()):
        b = ax.bar(x + (i - 0.5) * 0.38, vals, 0.38, label=name, color=["#9aa9bf", "#1f3b63"][i])
        ax.bar_label(b, fmt="%.0f", fontsize=6.3)
    ax.set_xticks(x, labels); ax.set_ylim(0, 105); ax.set_ylabel("coverage (%)")
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.17))
    fig.tight_layout()
    save(fig, "fig6_coverage")


# ── Fig. 7: output sign sequence ──────────────────────────────────────────────
def signs():
    import av
    from PIL import Image, ImageDraw, ImageFont
    from src import matcher
    m = matcher.match("Where is the hospital? I am 25 years old.", spell_unknown=True, use_drive=False)
    tiles = []
    for p in m["plan"]:
        if not p["clips"]:
            continue
        words = p.get("means", p["token"]).split()
        for i, clip in enumerate(p["clips"]):
            c = av.open(clip); v = c.streams.video[0]
            frames = [f for f in c.decode(v)]; c.close()
            img = frames[len(frames) // 2].to_image()
            label = words[i] if len(p["clips"]) > 1 and i < len(words) else p.get("means") or p["token"]
            tiles.append((label.upper(), img))
    W, H, COLS, BAR = 330, 220, 3, 34
    rows = (len(tiles) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * W, rows * (H + BAR)), "white")
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/timesbd.ttf", 24)
    except OSError:
        font = ImageFont.load_default()
    for k, (label, img) in enumerate(tiles):
        x0, y0 = (k % COLS) * W, (k // COLS) * (H + BAR)
        sheet.paste(img.resize((W - 8, H)), (x0 + 4, y0 + BAR))
        d.text((x0 + 8, y0 + 4), f"{k + 1}. {label}", fill="black", font=font)
    sheet.save(f"{OUT}/fig7_signs.png")
    print("wrote fig7_signs")


if __name__ == "__main__":
    flow(); speech(); training(); speakers(); noise(); coverage(); signs()
