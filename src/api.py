"""FastAPI app: /translate, /log_frame, /health. See plans/02_SPEC.md section 7."""
import csv
import os
import string
import uuid
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src import asr, matcher

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_REPO_ROOT, "data")
FRONTEND_DIR = os.path.join(_REPO_ROOT, "frontend")
UPLOADS_DIR = os.path.join(_REPO_ROOT, "uploads")
RESULTS_CSV = os.path.join(_REPO_ROOT, "eval", "results.csv")
ALPHABET_LETTERS = string.ascii_lowercase  # any name can be fingerspelled
MISSING_CLIPS_SHOWN = 20  # cap /health output; a fresh clone without the data misses thousands

CSV_FIELDS = [
    "row_type", "run_id", "utterance_id", "timestamp", "transcript",
    "n_total", "n_sign", "n_spell", "n_uncovered", "coverage",
    "asr_ms", "match_ms", "server_ms", "e2e_ms", "note",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    asr.get_model()  # preload so the first request doesn't pay the load cost
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _append_result_row(row: dict) -> None:
    os.makedirs(os.path.dirname(RESULTS_CSV), exist_ok=True)
    file_exists = os.path.exists(RESULTS_CSV)
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


@app.get("/health")
def health():
    manifest_path = os.path.join(DATA_DIR, "manifest.csv")
    missing_clips = []
    manifest_rows = 0
    if os.path.exists(manifest_path):
        with open(manifest_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                manifest_rows += 1
                clip_path = os.path.join(_REPO_ROOT, row["local_path"])
                if not os.path.exists(clip_path):
                    missing_clips.append(row["local_path"])

    alphabet_present = sum(
        1 for letter in ALPHABET_LETTERS
        if os.path.exists(os.path.join(DATA_DIR, "alphabet", f"{letter}.mp4"))
    )

    return {
        "ok": True,
        "model_loaded": asr._model is not None,
        "manifest_rows": manifest_rows,
        "missing_count": len(missing_clips),
        "missing_clips": missing_clips[:MISSING_CLIPS_SHOWN],
        "alphabet_present": alphabet_present,
        "alphabet_expected": len(ALPHABET_LETTERS),
    }


def _clip_url(local_path: str) -> str:
    # Dictionary file names carry spaces, commas, brackets and '&'
    # ("MHSL - 259/...", "Ache, Pain.mp4") - percent-encode so the browser
    # requests exactly the file StaticFiles will serve.
    return "/" + quote(local_path)


@app.post("/translate")
async def translate(
    audio: UploadFile = File(...),
    client_t0: str = Form(...),
    utterance_id: str = Form("adhoc"),
):
    import time

    server_start = time.perf_counter()
    run_id = uuid.uuid4().hex[:12]

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    # Keep the real extension: the client falls back to raw WebM if in-browser
    # WAV encoding fails, and PyAV decodes by content either way.
    suffix = os.path.splitext(audio.filename or "")[1].lower() or ".wav"
    if suffix not in (".wav", ".webm", ".ogg", ".mp4", ".m4a"):
        suffix = ".wav"
    upload_path = os.path.join(UPLOADS_DIR, f"{run_id}{suffix}")
    with open(upload_path, "wb") as f:
        f.write(await audio.read())

    asr_result = asr.transcribe(upload_path)
    match_result = matcher.match(asr_result["text"])

    plan = [
        {
            "token": entry["token"],
            "type": entry["type"],
            "clips": [_clip_url(clip) for clip in entry["clips"]],
        }
        for entry in match_result["plan"]
    ]

    server_ms = int((time.perf_counter() - server_start) * 1000)

    _append_result_row({
        "row_type": "translate",
        "run_id": run_id,
        "utterance_id": utterance_id,
        "timestamp": time.time(),
        "transcript": asr_result["text"],
        "n_total": match_result["counts"]["total"],
        "n_sign": match_result["counts"]["sign"],
        "n_spell": match_result["counts"]["spell"],
        "n_uncovered": match_result["counts"]["uncovered"],
        "coverage": round(match_result["coverage"], 4),
        "asr_ms": asr_result["asr_ms"],
        "match_ms": match_result["match_ms"],
        "server_ms": server_ms,
        "e2e_ms": "",
        # Which client audio path ran: browser-side 16kHz WAV encode, or the
        # raw-container fallback (still resampled to 16kHz mono by PyAV).
        "note": f"upload{suffix}",
    })

    return {
        "run_id": run_id,
        "transcript": asr_result["text"],
        "normalized": match_result["normalized"],
        "plan": plan,
        "coverage": round(match_result["coverage"], 4),
        "counts": match_result["counts"],
        "timings": {
            "asr_ms": asr_result["asr_ms"],
            "match_ms": match_result["match_ms"],
            "server_ms": server_ms,
        },
    }


@app.post("/log_frame")
async def log_frame(payload: dict):
    import time

    _append_result_row({
        "row_type": "frame",
        "run_id": payload.get("run_id", ""),
        "utterance_id": payload.get("utterance_id", ""),
        "timestamp": time.time(),
        "e2e_ms": payload.get("e2e_ms", ""),
    })
    return {"ok": True}


# Static mounts LAST — mounting "/" before the API routes would swallow them.
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
