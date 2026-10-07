"""Cells: research gaps, system overview, dataset, speech processing theory."""

from tools.build_notebook_part1 import CELLS


def md(t):
    CELLS.append(("markdown", t.strip("\n")))


def code(t):
    CELLS.append(("code", t.strip("\n")))


# ─────────────────────────────────────────── 3 GAPS
md(r"""
---
# § 3 · Research gaps

A gap is only worth stating if it points at real papers. Each of these traces to § 2.

## Gap 1 — Indian Sign Language is severely under-resourced

The standard sign-language benchmark, **PHOENIX14T [5]**, is German. The bulk of translation
research targets German and American Sign Language. ISL resources are far newer and smaller
(**ISLTranslate [2]**, 2023, ~31k pairs; **iSign [3]**, 2024, ~118k), and what exists for ISL
skews toward **isolated words** (**INCLUDE [4]**) rather than continuous signing.

**Consequence:** methods that assume a large annotated corpus cannot simply be transferred to ISL.

## Gap 2 — Sign language *production* is unsolved, and output quality is judged by movement naturalness

Recognition (sign→text) is mature (**[5]**, **[6]**). Production (text/speech→sign) is not:
**Progressive Transformers [7]** outputs 3D pose skeletons, and **Kapoor et al. [8]** — the closest
work to ours — also outputs poses rather than natural video.

Meanwhile **Quandt et al. [10]** show Deaf viewers are sensitive specifically to **unnatural
movement**, rating computer-synthesised avatars poorly while accepting motion-captured ones.

**Consequence:** synthesising signing risks producing exactly the artefact the target users are
most sensitive to. Using real recorded human signers avoids that failure mode entirely.

## Gap 3 — Retrieval-based speech→ISL has not been systematically evaluated

**[8]** attacks speech→sign by *generation*. **[9]** provides the retrieval machinery. But we
found no work that treats speech→ISL as a **retrieval** problem and reports honest coverage
against a fixed sign inventory.

**This gap is our contribution**, and we state it in one sentence:

> We test whether retrieving real ISL signer video, driven by automatic speech recognition, is a
> workable and *honestly measurable* alternative to generating sign language — and we report what
> fraction of speech such a system can actually cover.

The phrase **"honestly measurable"** is doing real work there. A generation system can always
output *something*; you cannot tell from the output alone whether it is correct. A retrieval
system either has the clip or it does not — so its failures are visible and countable. That is
the methodological argument for this design.
""")

# ─────────────────────────────────────────── 4 OVERVIEW
md(r"""
---
# § 4 · System overview

```
 ┌──────────┐   ┌───────────────┐   ┌──────────────────────┐   ┌───────────────┐
 │  Speech  │──▶│  Microphone   │──▶│  16 kHz mono audio   │──▶│    Whisper    │
 │ (person) │   │  push-to-talk │   │  (PCM, single chan.) │   │  base.en int8 │
 └──────────┘   └───────────────┘   └──────────────────────┘   └───────┬───────┘
                                                                       │ English text
                                                                       ▼
                                                        ┌──────────────────────────┐
                                                        │  Normalise + tokenise    │
                                                        │  lowercase, strip punct. │
                                                        └────────────┬─────────────┘
                                                                     ▼
                                                        ┌──────────────────────────┐
                                                        │  Longest-n-gram lookup   │
                                                        │  against manifest.csv    │
                                                        └────────────┬─────────────┘
                              ┌──────────────────────────────────────┼──────────────────────────┐
                              ▼                                      ▼                          ▼
                     ┌─────────────────┐                  ┌────────────────────┐      ┌──────────────────┐
                     │ FOUND → "sign"  │                  │ CAPITALISED name   │      │ NOT FOUND        │
                     │ play ISL clip   │                  │ → "spell"          │      │ → "uncovered"    │
                     │                 │                  │ fingerspell letters│      │ drop, and COUNT  │
                     └────────┬────────┘                  └─────────┬──────────┘      └──────────────────┘
                              └──────────────┬─────────────────────-┘
                                             ▼
                              ┌──────────────────────────────┐
                              │ Preload all clips, then play │
                              │ sequentially in the browser  │
                              └──────────────────────────────┘
```

## The three outcomes for every word

This three-way split is the entire intellectual content of the system.

| Outcome | Meaning | What the user sees |
|---|---|---|
| **sign** | Word/phrase exists in our ISL dictionary | The real ISL clip plays |
| **spell** | Looks like a proper noun (capitalised mid-sentence) | Fingerspelled letter by letter |
| **uncovered** | Not in the dictionary, not a name | **Nothing plays — and we count it** |

**Why "uncovered" matters more than it looks.** The lazy design would fingerspell every unknown
word. That produces an unreadable wall of letters, and it *hides* the system's limits behind
apparent activity. Dropping the word and counting it makes the limitation visible and gives us a
real metric. § 13 defines that metric.
""")

# ─────────────────────────────────────────── 5 DATASET
md(r"""
---
# § 5 · Dataset

## Source: the ISLRTC Indian Sign Language Dictionary

**ISLRTC** — the Indian Sign Language Research and Training Centre, an autonomous body under the
Department of Empowerment of Persons with Disabilities, Government of India.

| Property | Detail |
|---|---|
| Size | ~10,000 terms |
| Signers | Deaf signers (per ISLRTC) |
| Categories | Academic, agricultural, everyday, technical, legal |
| Distribution | ISLRTC website, YouTube, Google Drive, DIKSHA |
| Official page | https://islrtc.nic.in/isl-dictionary/ |
| Open-data entry | https://data.gov.in/catalog/indian-sign-language-dictionary |

The alphabet (fingerspelling) clips come from the ISL portal maintained by **FDMSE, RKMVERI,
Coimbatore** — 🔗 https://indiansignlanguage.org/category/alphabets/

> **Note on the ISL manual alphabet:** ISL uses a **two-handed** alphabet, unlike American and
> British Sign Language which are one-handed. We use the two-handed set consistently.

## What we actually use in Phase 0

Deliberately tiny. Five words plus one multi-word phrase, so the *pipeline* can be proven before
the vocabulary is grown. Adding a word later is **one row in a CSV and one video file** — no code
change.

## Licensing — and why no video is in our repository

We commit **`manifest.csv` with a source URL for every clip**, and we **never commit the video
files themselves**. The dataset is therefore fully reconstructible from the repository without us
redistributing government-licensed material.

This matters practically: "available for academic use" is *not* the same as "free to
redistribute", and ISLTranslate's CC-BY-NC licence would forbid commercial use outright.
""")

code(r"""
# The manifest is the single source of truth for the sign vocabulary.
import csv

with open("data/manifest.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print(f"{len(rows)} entries in the sign dictionary  (first 6 and a few longer phrases shown)\n")
print(f"{'id':<16}{'phrase':<18}{'words':<7}{'licence':<10}clip")
print("-" * 78)
sample = rows[:6] + [r for r in rows if int(r["ngram_len"]) >= 4][:4]
for r in sample:
    print(f"{r['id'][:15]:<16}{r['phrase'][:17]:<18}{r['ngram_len']:<7}{r['license']:<10}{r['local_path']}")
""")

code(r"""
# Verify every clip the manifest promises actually exists on disk,
# plus the 10 alphabet letters needed to fingerspell "Mothishwaran".
import os

missing = [r["local_path"] for r in rows if not os.path.exists(r["local_path"])]
print("sign clips present :", len(rows) - len(missing), "/", len(rows))
if missing:
    print("  MISSING:", missing)

needed = sorted(set("mothishwaran"))
have = [c for c in needed if os.path.exists(f"data/alphabet/{c}.mp4")]
print(f"alphabet letters   : {len(have)}/{len(needed)} needed for the demo name")

total = len([f for f in os.listdir("data/alphabet") if f.endswith(".mp4")])
print(f"alphabet clips     : {total} total (full A-Z available)")
""")

# ─────────────────────────────────── 6 SPEECH PROCESSING
md(r"""
---
# § 6 · Speech processing theory

This is the core of the course, so it gets treated properly. Everything below is computed from
our own audio file — nothing is copied from a textbook figure.

## 6.1 Sound → numbers: sampling

Sound is a continuous pressure wave. A computer stores **samples** — the wave's height measured
many times per second.

**Sampling rate** = samples per second. We use **16,000 Hz (16 kHz)**.

### Why 16 kHz? The Nyquist–Shannon theorem

> To represent a signal containing frequencies up to *f*, you must sample at **at least 2·f**.

Reversed: sampling at 16 kHz faithfully captures everything **up to 8 kHz**.

Speech intelligibility lives almost entirely below 8 kHz. Telephones used 8 kHz sampling (4 kHz
ceiling), which is why phone audio blurs `/s/` and `/f/` — those fricatives carry energy above
4 kHz. 16 kHz keeps them.

Whisper's front end expects exactly 16 kHz, so this is also a hard requirement, not just a choice.

**Sampling below Nyquist causes *aliasing*** — high frequencies fold back and masquerade as low
ones, corrupting the signal irreversibly.

## 6.2 Bit depth

Each sample is stored as a 16-bit integer (**PCM16**): 65,536 possible amplitude levels. Fewer
bits would add audible quantisation noise.

Our audio is **mono** — one channel. Two microphones give no benefit for single-speaker ASR and
would double the data.
""")

code(r"""
import wave
import numpy as np
import matplotlib.pyplot as plt

PATH = "eval/sample.wav"
with wave.open(PATH, "rb") as w:
    sr        = w.getframerate()
    n_ch      = w.getnchannels()
    width     = w.getsampwidth()
    n_frames  = w.getnframes()
    raw       = w.readframes(n_frames)

signal = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
if n_ch > 1:
    signal = signal.reshape(-1, n_ch).mean(axis=1)

print(f"file          : {PATH}")
print(f"sample rate   : {sr} Hz      -> Nyquist limit = {sr//2} Hz")
print(f"channels      : {n_ch} (mono)")
print(f"bit depth     : {width*8}-bit PCM")
print(f"samples       : {len(signal):,}")
print(f"duration      : {len(signal)/sr:.2f} s")
print(f"amplitude     : min {signal.min():+.3f}   max {signal.max():+.3f}")
""")

code(r"""
# The waveform: amplitude over time. You can see where words are and where silence is,
# but you cannot see WHICH sounds they are. That needs frequency analysis.
t = np.arange(len(signal)) / sr

fig, ax = plt.subplots(figsize=(13, 3))
ax.plot(t, signal, linewidth=0.4, color="#2563eb")
ax.set_xlabel("time (seconds)")
ax.set_ylabel("amplitude")
ax.set_title('Waveform - "Hello, thank you. My name is Mothishwaran."')
ax.set_xlim(0, t[-1])
ax.grid(alpha=0.3)
plt.tight_layout(); plt.show()
""")

md(r"""
## 6.3 Framing and windowing

Speech is **non-stationary** — it changes constantly. But over a *short* span (~20–30 ms) the
vocal tract barely moves, so the signal is approximately **stationary**. That short span is a
**frame**.

| Parameter | Typical | Why |
|---|---|---|
| Frame length | 25 ms | Long enough to measure pitch, short enough to be stationary |
| Hop (stride) | 10 ms | Frames overlap 60%, so no transient is lost at a boundary |

### Why we apply a window function

Cutting a frame with a hard edge (a *rectangular* window) chops the waveform mid-cycle. The FFT
assumes the frame repeats forever, so that discontinuity injects fake frequencies across the whole
spectrum — **spectral leakage**.

A **Hamming window** tapers smoothly to near zero at both edges, so the frame joins itself
cleanly. Cost: a slightly wider main lobe (a little less frequency resolution). Benefit: far lower
side lobes (much less leakage). For speech that trade is clearly worth it.
""")

code(r"""
FRAME_MS, HOP_MS = 25, 10
frame_len = int(sr * FRAME_MS / 1000)
hop_len   = int(sr * HOP_MS   / 1000)

hamming = np.hamming(frame_len)
rect    = np.ones(frame_len)

print(f"frame length : {FRAME_MS} ms = {frame_len} samples")
print(f"hop length   : {HOP_MS} ms = {hop_len} samples")
print(f"overlap      : {100*(1-hop_len/frame_len):.0f}%")

start = int(1.0 * sr)                       # a frame from ~1 s in
seg = signal[start:start+frame_len]

fig, axes = plt.subplots(1, 3, figsize=(14, 3.2))
axes[0].plot(seg, color="#334155", lw=0.8)
axes[0].set_title("raw 25 ms frame"); axes[0].grid(alpha=.3)
axes[1].plot(hamming, color="#dc2626", lw=1.5, label="Hamming")
axes[1].plot(rect, color="#94a3b8", lw=1.2, ls="--", label="rectangular")
axes[1].set_title("window functions"); axes[1].legend(); axes[1].grid(alpha=.3)
axes[2].plot(seg*hamming, color="#2563eb", lw=0.8)
axes[2].set_title("frame x Hamming (tapers to 0)"); axes[2].grid(alpha=.3)
plt.tight_layout(); plt.show()
""")

code(r"""
# Spectral leakage, measured rather than asserted: a pure tone that does not fit
# a whole number of cycles in the frame.
f0 = 440.5
tone = np.sin(2*np.pi*f0*np.arange(frame_len)/sr)

spec_rect = 20*np.log10(np.abs(np.fft.rfft(tone*rect))    + 1e-10)
spec_hamm = 20*np.log10(np.abs(np.fft.rfft(tone*hamming)) + 1e-10)
freqs = np.fft.rfftfreq(frame_len, 1/sr)

fig, ax = plt.subplots(figsize=(11, 3.4))
ax.plot(freqs, spec_rect, color="#94a3b8", lw=1, label="rectangular - leakage everywhere")
ax.plot(freqs, spec_hamm, color="#dc2626", lw=1.2, label="Hamming - energy stays local")
ax.set_xlim(0, 2000); ax.set_xlabel("frequency (Hz)"); ax.set_ylabel("magnitude (dB)")
ax.set_title(f"Spectral leakage for a {f0} Hz tone"); ax.legend(); ax.grid(alpha=.3)
plt.tight_layout(); plt.show()

print("The grey curve smears energy across frequencies that are NOT in the signal.")
print("That smearing is what the window function suppresses.")
""")

md(r"""
## 6.4 The spectrogram

Take every frame, window it, run an **FFT**, keep the magnitude. Stack the results side by side
and you get a **spectrogram**: time on x, frequency on y, energy as colour.

This is the *Short-Time Fourier Transform* (STFT). It is where you can finally *see* speech —
the horizontal bands are **formants**, the resonances of the vocal tract that distinguish
vowels from one another.
""")

code(r"""
def stft_magnitude(x, frame_len, hop_len, window):
    n_frames = 1 + (len(x) - frame_len) // hop_len
    out = np.empty((n_frames, frame_len//2 + 1), dtype=np.float32)
    for i in range(n_frames):
        seg = x[i*hop_len : i*hop_len + frame_len] * window
        out[i] = np.abs(np.fft.rfft(seg))
    return out

mag = stft_magnitude(signal, frame_len, hop_len, hamming)
power = mag ** 2
print("spectrogram shape :", mag.shape, "= (frames, frequency bins)")
print("frequency bins    :", mag.shape[1], f"covering 0 to {sr//2} Hz")

fig, ax = plt.subplots(figsize=(13, 4))
im = ax.imshow(20*np.log10(mag.T + 1e-10), origin="lower", aspect="auto",
               extent=[0, len(signal)/sr, 0, sr/2], cmap="magma")
ax.set_xlabel("time (s)"); ax.set_ylabel("frequency (Hz)")
ax.set_title("Linear-frequency spectrogram (STFT magnitude, dB)")
fig.colorbar(im, ax=ax, label="dB")
plt.tight_layout(); plt.show()
""")

md(r"""
## 6.5 The mel scale — matching human hearing

Human pitch perception is **not linear**. The gap between 100 Hz and 200 Hz sounds huge; the gap
between 8000 Hz and 8100 Hz is inaudible. We hear roughly **logarithmically**.

The **mel scale** warps frequency to match that:

$$ m = 2595 \cdot \log_{10}\!\left(1 + \frac{f}{700}\right) $$

We then build overlapping triangular **filters**, evenly spaced *in mel*, and sum the spectrogram
energy inside each. Low frequencies get many narrow filters (fine detail where we hear well);
high frequencies get few wide ones.

This is both perceptually sensible **and** a big compression: 201 linear bins → 80 mel bins.
""")

code(r"""
def hz_to_mel(f):  return 2595.0 * np.log10(1.0 + f/700.0)
def mel_to_hz(m):  return 700.0 * (10**(m/2595.0) - 1.0)

def mel_filterbank(n_filters, n_fft, sr, fmin=0, fmax=None):
    fmax = fmax or sr/2
    mel_pts = np.linspace(hz_to_mel(fmin), hz_to_mel(fmax), n_filters + 2)
    hz_pts  = mel_to_hz(mel_pts)
    bins    = np.floor((n_fft + 1) * hz_pts / sr).astype(int)
    fb = np.zeros((n_filters, n_fft//2 + 1))
    for i in range(1, n_filters + 1):
        left, centre, right = bins[i-1], bins[i], bins[i+1]
        for k in range(left, centre):
            if centre > left:  fb[i-1, k] = (k - left) / (centre - left)
        for k in range(centre, right):
            if right > centre: fb[i-1, k] = (right - k) / (right - centre)
    return fb, hz_pts

N_MELS = 80                      # 80 is exactly what Whisper uses
fb, hz_pts = mel_filterbank(N_MELS, frame_len, sr)
print("filterbank shape :", fb.shape)

fig, axes = plt.subplots(1, 2, figsize=(13, 3.4))
freqs = np.fft.rfftfreq(frame_len, 1/sr)
for i in range(0, N_MELS, 4):
    axes[0].plot(freqs, fb[i], lw=0.9)
axes[0].set_title(f"Mel filterbank (every 4th of {N_MELS})")
axes[0].set_xlabel("frequency (Hz)"); axes[0].grid(alpha=.3)

f_lin = np.linspace(0, sr/2, 500)
axes[1].plot(f_lin, hz_to_mel(f_lin), color="#7c3aed", lw=2)
axes[1].plot(f_lin, f_lin*(hz_to_mel(sr/2)/(sr/2)), ls="--", color="#94a3b8", lw=1.2)
axes[1].set_title("mel scale (purple) vs linear (dashed)")
axes[1].set_xlabel("frequency (Hz)"); axes[1].set_ylabel("mel"); axes[1].grid(alpha=.3)
plt.tight_layout(); plt.show()

print("\nFilter spacing - note how they widen as frequency rises:")
for i in [0, 20, 40, 60, 78]:
    print(f"  filter {i:>2}: centred near {hz_pts[i+1]:7.0f} Hz")
""")

code(r"""
# Apply the filterbank, then take log -> the log-mel spectrogram.
# This is LITERALLY the input representation Whisper consumes.
mel_power = power @ fb.T
log_mel   = np.log10(mel_power + 1e-10)

print("linear spectrogram :", power.shape)
print("log-mel spectrogram:", log_mel.shape, " <- 201 bins compressed to 80")

fig, axes = plt.subplots(2, 1, figsize=(13, 6.5), sharex=True)
axes[0].imshow(20*np.log10(mag.T + 1e-10), origin="lower", aspect="auto",
               extent=[0, len(signal)/sr, 0, sr/2], cmap="magma")
axes[0].set_ylabel("frequency (Hz)"); axes[0].set_title("Linear spectrogram (201 bins)")
axes[1].imshow(log_mel.T, origin="lower", aspect="auto",
               extent=[0, len(signal)/sr, 0, N_MELS], cmap="magma")
axes[1].set_ylabel("mel filter index"); axes[1].set_xlabel("time (s)")
axes[1].set_title("Log-mel spectrogram (80 bins) - what Whisper actually sees")
plt.tight_layout(); plt.show()
""")

md(r"""
## 6.6 MFCCs — and why Whisper does *not* use them

The classical pipeline goes one step further: apply a **Discrete Cosine Transform** to the
log-mel energies and keep the first ~13 coefficients. Those are **MFCCs** (Mel-Frequency
Cepstral Coefficients).

### The full MFCC pipeline

```
audio → pre-emphasis → framing → windowing → FFT → power spectrum
      → mel filterbank → log → DCT → keep 13 coefficients
```

### Why each step exists

| Step | Reason |
|---|---|
| Pre-emphasis | Boost high frequencies; voiced speech naturally rolls off ~-6 dB/octave |
| Framing | Make a non-stationary signal locally stationary |
| Windowing | Prevent spectral leakage at frame edges |
| FFT → power | Move to the frequency domain, discard phase |
| Mel filterbank | Weight frequency the way human hearing does |
| **Log** | Match perceived loudness; turns source×filter into source+filter (a *sum*, separable) |
| **DCT** | **Decorrelate** the filterbank energies |
| Keep 13 | Low coefficients hold vocal-tract shape; high ones hold pitch/noise |

### Why the DCT specifically

Mel filters **overlap**, so neighbouring filter energies are strongly correlated. Classical
recognisers used Gaussian Mixture Models with **diagonal** covariance matrices — which assume
features are *independent*. The DCT decorrelates them, making that assumption survivable, and it
compacts most energy into the first few coefficients.

### So why doesn't Whisper use MFCCs?

Because that assumption is obsolete. Whisper is a **neural network**, and a neural network can
learn its own decorrelation from data. Throwing away the higher coefficients would just throw
away information. So Whisper takes the **log-mel spectrogram directly** (80 bins) and skips the
DCT.

> **This is a very likely viva question.** The honest answer: MFCCs are a compression designed
> for a modelling assumption (diagonal-covariance GMM-HMM) that deep models no longer need.
""")

code(r"""
# Type-II DCT implemented directly with numpy, so the notebook needs no scipy.
def dct_ii(x, n_keep):
    N = x.shape[-1]
    k = np.arange(N)[None, :]
    n = np.arange(n_keep)[:, None]
    basis = np.cos(np.pi * (2*k + 1) * n / (2*N))
    out = x @ basis.T
    out[:, 0]  *= np.sqrt(1.0/N)
    out[:, 1:] *= np.sqrt(2.0/N)
    return out

N_MFCC = 13
mfcc = dct_ii(log_mel, N_MFCC)
print("log-mel :", log_mel.shape, "->  MFCC :", mfcc.shape)

fig, ax = plt.subplots(figsize=(13, 3))
im = ax.imshow(mfcc.T, origin="lower", aspect="auto",
               extent=[0, len(signal)/sr, 0, N_MFCC], cmap="coolwarm")
ax.set_xlabel("time (s)"); ax.set_ylabel("coefficient")
ax.set_title(f"{N_MFCC} MFCCs (classical ASR features - Whisper does NOT use these)")
fig.colorbar(im, ax=ax)
plt.tight_layout(); plt.show()
""")

code(r"""
# Evidence for the decorrelation claim, measured rather than asserted.
# Compare the FULL 80-band filterbank against the 13 MFCCs. (Comparing only the
# first 13 mel bands would be misleading - those are all low-frequency bands and
# are less mutually correlated than the filterbank as a whole.)
def corr(x):
    xc = x - x.mean(0, keepdims=True)
    sd = xc.std(0, keepdims=True) + 1e-10
    return (xc/sd).T @ (xc/sd) / len(x)

def mean_offdiag(c):
    n = c.shape[0]
    return np.abs(c - np.diag(np.diag(c))).sum() / (n * (n - 1))

c_mel, c_mfcc = corr(log_mel), corr(mfcc)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for a, c, t in [(axes[0], c_mel,  f"80 log-mel bands\nmean |off-diagonal r| = {mean_offdiag(c_mel):.3f}"),
                (axes[1], c_mfcc, f"13 MFCCs after DCT\nmean |off-diagonal r| = {mean_offdiag(c_mfcc):.3f}")]:
    im = a.imshow(np.abs(c), cmap="viridis", vmin=0, vmax=1)
    a.set_title(t, fontsize=10); plt.colorbar(im, ax=a)
plt.tight_layout(); plt.show()

print(f"mel filterbank (80 bands) : {mean_offdiag(c_mel):.3f}   <- neighbouring filters overlap")
print(f"MFCC (13 coefficients)    : {mean_offdiag(c_mfcc):.3f}   <- DCT has decorrelated them")
print("\nThe bright off-diagonal structure in the left plot is the redundancy")
print("the DCT removes. That is why diagonal-covariance GMM-HMMs could use MFCCs")
print("but could not have used raw filterbank energies.")
""")
