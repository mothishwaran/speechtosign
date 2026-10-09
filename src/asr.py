"""ASR wrapper around faster-whisper. See plans/02_SPEC.md section 3.

Model: models/whisper-base-en-svarah (Whisper base.en fine-tuned on Svarah
Indian-accented English) when that folder exists, otherwise stock base.en.

Device selection (env SPEECH_ISL_DEVICE = auto | cuda | cpu, default auto):
  auto - use the NVIDIA GPU (float16) when CTranslate2 sees one and the CUDA
         libraries load; otherwise fall back to CPU int8 with a warning. The
         same code therefore runs on a GPU laptop and on one without.
  cuda - GPU or fail loudly.
  cpu  - the original Phase 0 configuration.

CUDA libraries come from the pip packages in requirements-gpu.txt
(nvidia-cublas-cu12, nvidia-cudnn-cu12), not a system CUDA install; their DLL
folders are put on the search path below.
"""
import glob
import os
import sys
import time

import numpy as np
from faster_whisper import WhisperModel

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Fine-tuned on Indian-accented English (tools/train/); committed to the repo.
FINETUNED_DIR = "models/whisper-base-en-svarah"


def _default_model() -> str:
    if os.path.isfile(os.path.join(_REPO_ROOT, FINETUNED_DIR, "model.bin")):
        return os.path.join(_REPO_ROOT, FINETUNED_DIR)
    return "base.en"


# SPEECH_ISL_MODEL overrides: "base.en" for the stock model, or any
# faster-whisper model name / exported folder.
MODEL_NAME = os.environ.get("SPEECH_ISL_MODEL") or _default_model()
MODEL_LABEL = os.path.basename(MODEL_NAME.rstrip("/\\"))  # short name for UI and logs
DEVICE_PREF = os.environ.get("SPEECH_ISL_DEVICE", "auto").lower()

_model: WhisperModel | None = None
device: str | None = None        # "cuda" or "cpu" once loaded
compute_type: str | None = None


def _register_pip_cuda_libs() -> None:
    """Make DLLs from the nvidia-* pip wheels loadable by CTranslate2."""
    try:
        import nvidia
    except ImportError:
        return
    for root in nvidia.__path__:
        for libdir in glob.glob(os.path.join(root, "*", "bin")) + glob.glob(os.path.join(root, "*", "lib")):
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(libdir)
            # CTranslate2 loads cuBLAS/cuDNN lazily via the normal search
            # path, which add_dll_directory alone does not cover.
            os.environ["PATH"] = libdir + os.pathsep + os.environ.get("PATH", "")


def _load(dev: str, ctype: str) -> WhisperModel:
    model = WhisperModel(MODEL_NAME, device=dev, compute_type=ctype)
    # Warm-up on one second of silence: forces the CUDA libraries to load now
    # (a missing cuDNN otherwise only surfaces on the first real request) and
    # keeps first-request latency out of the results table.
    segments, _ = model.transcribe(np.zeros(16000, dtype=np.float32), language="en", beam_size=1)
    list(segments)
    return model


def get_model() -> WhisperModel:
    global _model, device, compute_type
    if _model is not None:
        return _model

    load_start = time.perf_counter()
    candidates = []
    if DEVICE_PREF in ("auto", "cuda"):
        candidates.append(("cuda", "float16"))
    if DEVICE_PREF in ("auto", "cpu"):
        candidates.append(("cpu", "int8"))

    last_err = None
    for dev, ctype in candidates:
        if dev == "cuda":
            import ctranslate2
            if ctranslate2.get_cuda_device_count() == 0:
                last_err = "no CUDA device visible"
                print("[asr] no CUDA GPU found, using CPU", file=sys.stderr)
                continue
            _register_pip_cuda_libs()
        try:
            _model = _load(dev, ctype)
            device, compute_type = dev, ctype
            break
        except Exception as e:  # missing cuBLAS/cuDNN, driver mismatch, OOM
            last_err = e
            print(f"[asr] {dev} unavailable ({e}); trying next option", file=sys.stderr)

    if _model is None:
        raise RuntimeError(f"could not load Whisper on {DEVICE_PREF}: {last_err}")

    load_ms = int((time.perf_counter() - load_start) * 1000)
    print(f"[asr] model '{MODEL_LABEL}' loaded on {device} ({compute_type}) in {load_ms}ms",
          file=sys.stderr)
    return _model


def transcribe(audio, denoise: bool = False) -> dict:
    """Transcribe a file path or a 16 kHz mono float32 array.

    denoise=True runs spectral subtraction (src/denoise.py) first; see
    tools/noise_study.py for when that helps Whisper and when it does not.
    """
    model = get_model()

    denoise_ms = 0
    if denoise:
        from faster_whisper import decode_audio
        from src.denoise import spectral_subtract
        if isinstance(audio, str):
            audio = decode_audio(audio, sampling_rate=16000)
        t0 = time.perf_counter()
        audio = spectral_subtract(audio)
        denoise_ms = int((time.perf_counter() - t0) * 1000)

    start = time.perf_counter()
    segments, info = model.transcribe(
        audio,
        language="en",
        beam_size=1,
        initial_prompt="Mothishwaran",
    )
    text = " ".join(segment.text.strip() for segment in segments).strip()
    asr_ms = int((time.perf_counter() - start) * 1000)

    return {
        "text": text,
        "language": info.language,
        "asr_ms": asr_ms,
        "denoise_ms": denoise_ms,
        "model": MODEL_LABEL,
        "device": device,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m src.asr <path.wav>", file=sys.stderr)
        sys.exit(1)
    result = transcribe(sys.argv[1])
    print(result)
