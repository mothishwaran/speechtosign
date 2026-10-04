"""ASR wrapper around faster-whisper. See plans/02_SPEC.md section 3."""
import sys
import time

from faster_whisper import WhisperModel

MODEL_NAME = "base.en"
_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        load_start = time.perf_counter()
        _model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
        load_ms = int((time.perf_counter() - load_start) * 1000)
        print(f"[asr] model '{MODEL_NAME}' loaded in {load_ms}ms", file=sys.stderr)
    return _model


def transcribe(audio_path: str) -> dict:
    model = get_model()

    start = time.perf_counter()
    segments, info = model.transcribe(
        audio_path,
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
        "model": MODEL_NAME,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m src.asr <path.wav>", file=sys.stderr)
        sys.exit(1)
    result = transcribe(sys.argv[1])
    print(result)
