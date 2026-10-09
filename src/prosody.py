"""Prosody: pitch (F0) track and final-rise question cue, from 16 kHz audio.

Same method as the live display in the page (normalised autocorrelation,
shortest strong peak to avoid octave errors), vectorised with numpy:
  - 40 ms frames, 10 ms hop; frames under SILENCE_DB are skipped.
  - autocorrelation via FFT, unbiased normalisation r[k] / (r[0] (N-k)/N).
  - voiced if the best normalised peak in 70-400 Hz is >= VOICED_R.
Final-rise cue: median F0 of the last FINAL_MS of voiced speech versus the
median F0 of the rest of the utterance, in semitones (12 log2 ratio), which
compares low and high voices fairly. English yes/no questions typically end
rising; wh-questions usually fall, so text cues handle those (src/isl_order.py).
RISE_THRESHOLD_ST is set by tools/question_study.py on Svarah TRAIN speakers.
"""
import numpy as np

SR = 16000
FRAME = 640          # 40 ms
HOP = 160            # 10 ms
F0_MIN, F0_MAX = 70, 400
VOICED_R = 0.5
SILENCE_DB = -45
FINAL_MS = 300
RISE_THRESHOLD_ST = 2.0   # overwritten below if tools/question_study.py calibrated it

try:   # calibrated value, committed by tools/question_study.py
    import json
    import os
    _cal = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "eval", "question_threshold.json")
    if os.path.exists(_cal):
        with open(_cal, encoding="utf-8") as _f:
            RISE_THRESHOLD_ST = float(json.load(_f)["threshold_st"])
except Exception:  # never let a bad calibration file break transcription
    pass


def f0_track(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (times_s, f0_hz) with NaN for unvoiced/silent frames."""
    x = np.asarray(x, dtype=np.float32)
    if len(x) < FRAME:
        return np.zeros(0), np.zeros(0)
    n_frames = 1 + (len(x) - FRAME) // HOP
    idx = np.arange(FRAME)[None, :] + HOP * np.arange(n_frames)[:, None]
    frames = x[idx] - x[idx].mean(axis=1, keepdims=True)
    energy_db = 10 * np.log10(np.mean(frames ** 2, axis=1) + 1e-12)

    spec = np.fft.rfft(frames, n=2 * FRAME, axis=1)
    acf = np.fft.irfft(np.abs(spec) ** 2, axis=1)[:, :FRAME]
    lags = np.arange(FRAME)
    acf = acf / np.maximum(acf[:, :1], 1e-12) / ((FRAME - lags) / FRAME)   # unbiased, r[0] = 1

    lo, hi = int(SR / F0_MAX), int(SR / F0_MIN)
    r = acf[:, lo:hi + 1]
    best = r.max(axis=1)
    f0 = np.full(n_frames, np.nan)
    for i in np.where((best >= VOICED_R) & (energy_db > SILENCE_DB))[0]:
        row = r[i]
        # shortest local peak within 10 % of the best (octave-error guard)
        peaks = np.where((row[1:-1] >= 0.9 * best[i]) & (row[1:-1] >= row[:-2]) & (row[1:-1] >= row[2:]))[0]
        if len(peaks):
            f0[i] = SR / (lo + 1 + peaks[0])
    times = (np.arange(n_frames) * HOP + FRAME / 2) / SR
    return times, f0


def final_rise(x: np.ndarray) -> dict:
    """Final pitch movement in semitones (+ = rising) and the question decision."""
    times, f0 = f0_track(x)
    voiced = ~np.isnan(f0)
    out = {"voiced_ratio": float(voiced.mean()) if len(f0) else 0.0,
           "median_f0": float(np.nanmedian(f0)) if voiced.any() else None,
           "final_rise_st": None, "rising": False}
    vt, vf = times[voiced], f0[voiced]
    if len(vf) < 15:                                   # < 150 ms of voicing: no decision
        return out
    end = vt[-1]
    final = vf[vt >= end - FINAL_MS / 1000]
    body = vf[vt < end - FINAL_MS / 1000]
    if len(final) < 5 or len(body) < 10:
        return out
    rise = 12 * np.log2(np.median(final) / np.median(body))
    out["final_rise_st"] = round(float(rise), 2)
    out["rising"] = bool(rise >= RISE_THRESHOLD_ST)
    return out
