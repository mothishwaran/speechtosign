"""Spectral subtraction noise reduction (Boll 1979; over-subtraction after Berouti 1979).

Pure numpy, 16 kHz mono float32 in and out. Steps:
  1. STFT: 32 ms Hann frames (512 samples), 8 ms hop (75 % overlap).
  2. Noise power spectrum = mean power of the quietest 10 % of frames.
     (No assumption that the recording starts with silence - push-to-talk
     often clips it.)
  3. Clean power = |Y|^2 - alpha * N, floored at beta * |Y|^2 so no bin goes
     negative; the floor limits "musical noise" (isolated spectral peaks).
  4. Keep the noisy phase (the ear is far less sensitive to phase), inverse
     STFT by weighted overlap-add.
Used by src/asr.py when the UI's "Noise reduction" switch is on, and by
tools/noise_study.py to measure whether it actually helps Whisper.
"""
import numpy as np

N_FFT = 512
HOP = 128
NOISE_QUANTILE = 0.10
ALPHA = 2.0      # over-subtraction factor
BETA = 0.02      # spectral floor


def _stft(x: np.ndarray, win: np.ndarray) -> np.ndarray:
    pad = N_FFT // 2
    xp = np.pad(x, (pad, pad + N_FFT), mode="reflect" if len(x) > pad else "constant")
    n_frames = 1 + (len(xp) - N_FFT) // HOP
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n_frames)[:, None]
    return np.fft.rfft(xp[idx] * win, axis=1)


def _istft(spec: np.ndarray, win: np.ndarray, length: int) -> np.ndarray:
    frames = np.fft.irfft(spec, n=N_FFT, axis=1) * win
    out_len = HOP * (len(frames) - 1) + N_FFT
    y = np.zeros(out_len)
    wsum = np.zeros(out_len)
    for i, f in enumerate(frames):
        y[i * HOP:i * HOP + N_FFT] += f
        wsum[i * HOP:i * HOP + N_FFT] += win ** 2
    y /= np.maximum(wsum, 1e-8)
    pad = N_FFT // 2
    return y[pad:pad + length]


def spectral_subtract(x: np.ndarray, alpha: float = ALPHA, beta: float = BETA) -> np.ndarray:
    """Return a denoised copy of x (float32, same length)."""
    x = np.asarray(x, dtype=np.float64)
    if len(x) < N_FFT:
        return x.astype(np.float32)
    win = np.hanning(N_FFT + 1)[:-1]          # periodic Hann
    Y = _stft(x, win)
    power = np.abs(Y) ** 2
    frame_energy = power.sum(axis=1)
    quiet = frame_energy <= np.quantile(frame_energy, NOISE_QUANTILE)
    noise = power[quiet].mean(axis=0)
    clean_power = np.maximum(power - alpha * noise, beta * power)
    S = np.sqrt(clean_power) * np.exp(1j * np.angle(Y))
    return _istft(S, win, len(x)).astype(np.float32)


def snr_db(clean: np.ndarray, test: np.ndarray) -> float:
    """SNR of `test` against the known clean signal (for evaluation only)."""
    err = test.astype(np.float64) - clean.astype(np.float64)
    return 10 * np.log10(np.sum(clean.astype(np.float64) ** 2) / (np.sum(err ** 2) + 1e-12))
