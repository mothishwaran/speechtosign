"""Noise robustness study: WER vs SNR, stock vs fine-tuned Whisper, with and
without spectral subtraction (src/denoise.py).

Speech: 200 utterances from the Svarah TEST speakers (never trained on),
sampled evenly across the 16 speakers.
Noise:  white  - Gaussian, flat spectrum (fan / hiss stand-in)
        babble - 4 other Svarah speakers from the TRAIN split talking at once
                 (crowd / classroom stand-in; the hardest kind for ASR,
                 because it is speech too)
Mixed at 20, 10, 5, 0 dB SNR (signal power over noise power, whole
utterance), plus the clean baseline.
Decoding is exactly the app's (greedy, Whisper's default temperature fallback).
A smoke test with the fallback switched off showed why it matters: at 0 dB
babble Whisper fell into a repetition loop (WER > 400 %), which the fallback's
compression-ratio check exists to catch. The fallback adds a little run-to-run
randomness (~±0.2 WER points on clean speech), far below the effects measured.

Usage: python tools/noise_study.py [--n 200]
Writes eval/noise_study.csv (one row per condition) and
eval/noise_study_snr.csv (SNR before/after spectral subtraction).
"""
import argparse
import csv
import os
import random
import sys
import time

import numpy as np

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from src.denoise import snr_db, spectral_subtract  # noqa: E402
from tools.train import data  # noqa: E402
from tools.train.metrics import wer_corpus  # noqa: E402

MODELS = ["base.en", "models/whisper-base-en-svarah"]
SNRS = [20, 10, 5, 0]
NOISES = ["white", "babble"]
OUT = "eval/noise_study.csv"
OUT_SNR = "eval/noise_study_snr.csv"


def pick_test(n: int) -> list:
    test = data.load_splits()["test"]
    by_spk = {}
    for r in test:
        by_spk.setdefault(r["speaker"], []).append(r)
    rng = random.Random(0)
    for rows in by_spk.values():
        rng.shuffle(rows)
    picked, i = [], 0
    while len(picked) < n:                       # round-robin over speakers
        for rows in by_spk.values():
            if i < len(rows) and len(picked) < n:
                picked.append(rows[i])
        i += 1
    return picked


def make_noise(kind: str, length: int, rng: np.random.Generator, babble_pool: list) -> np.ndarray:
    if kind == "white":
        return rng.standard_normal(length).astype(np.float32)
    out = np.zeros(length, dtype=np.float32)
    for k in rng.choice(len(babble_pool), size=4, replace=False):
        b = babble_pool[k]
        reps = int(np.ceil(length / len(b)))
        b = np.tile(b, reps)[:length]
        out += b / (np.sqrt(np.mean(b ** 2)) + 1e-9)
    return out


def mix(clean: np.ndarray, noise: np.ndarray, snr: float) -> np.ndarray:
    ps, pn = np.mean(clean ** 2), np.mean(noise ** 2) + 1e-12
    return (clean + noise * np.sqrt(ps / (pn * 10 ** (snr / 10)))).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    args = ap.parse_args()
    os.chdir(_REPO_ROOT)

    from src import asr
    from faster_whisper import WhisperModel
    asr._register_pip_cuda_libs()

    rows = pick_test(args.n)
    print(f"{len(rows)} test utterances from {len({r['speaker'] for r in rows})} unseen speakers")
    clean = [data.load_audio(r) for r in rows]
    refs = [r["text"] for r in rows]

    train = data.load_splits()["train"]
    pool_rows = random.Random(1).sample(train, 60)
    babble_pool = [data.load_audio(r) for r in pool_rows]

    # Build every noisy version once, so all models hear identical audio.
    conditions = [("clean", None)] + [(k, s) for k in NOISES for s in SNRS]
    audio = {}
    snr_rows = []
    for kind, snr in conditions:
        # fixed per-condition seed (str hash() is randomised per process)
        rng = np.random.default_rng(0 if kind == "clean" else 1000 * NOISES.index(kind) + snr)
        noisy = [x if kind == "clean" else mix(x, make_noise(kind, len(x), rng, babble_pool), snr)
                 for x in clean]
        den = [spectral_subtract(x) for x in noisy]
        audio[(kind, snr, False)] = noisy
        audio[(kind, snr, True)] = den
        if kind != "clean":
            snr_rows.append({"noise": kind, "snr_in": snr,
                             "snr_noisy": round(float(np.mean([snr_db(c, n) for c, n in zip(clean, noisy)])), 2),
                             "snr_denoised": round(float(np.mean([snr_db(c, d) for c, d in zip(clean, den)])), 2)})
    with open(OUT_SNR, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(snr_rows[0].keys()))
        w.writeheader()
        w.writerows(snr_rows)
    print(f"wrote {OUT_SNR}")

    results = []
    for name in MODELS:
        model = WhisperModel(name, device="cuda", compute_type="float16")
        for (kind, snr, denoise), clips in audio.items():
            t0 = time.time()
            hyps = []
            for x in clips:
                segs, _ = model.transcribe(x, language="en", beam_size=1,
                                           initial_prompt="Mothishwaran")
                hyps.append(" ".join(s.text.strip() for s in segs))
            wer = wer_corpus(refs, hyps)
            row = {"model": os.path.basename(name), "noise": kind, "snr_db": "" if snr is None else snr,
                   "denoise": int(denoise), "wer": round(wer, 4), "n": len(clips)}
            results.append(row)
            print(f"{row['model']:24} {kind:6} {str(snr):>4} dB  denoise={int(denoise)}  "
                  f"WER {wer * 100:6.2f}%  ({time.time() - t0:.0f}s)", flush=True)
        del model

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
