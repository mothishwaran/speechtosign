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

from src import asr, drive_fetch, fingerspell, isl_order, matcher, prosody
from src.eval_sets import eval_sentences

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
    # added after Phase 0 - appended at the end so old rows keep their meaning
    "n_omitted", "content_coverage", "n_similar", "speaker",
    "n_related", "drive_ms",
    "question", "final_rise_st", "isl_rules", "denoise",
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


@app.middleware("http")
async def revalidate_clips(request, call_next):
    """Make browsers re-check sign clips and the page instead of guessing.

    Without Cache-Control a browser may reuse an old copy for hours, e.g.
    the letter clips after they were re-timed. "no-cache" still uses the
    cache - the server answers 304 Not Modified via the ETag - it only forces
    the check.
    """
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/data/") or path in ("/", "/index.html"):
        response.headers["Cache-Control"] = "no-cache"
    return response


def _upgrade_results_header(path: str) -> None:
    """Rewrite an older results CSV under the current header.

    The log is append-only evidence, so this never drops or edits a row: old
    rows are copied with the new columns left blank. Written to a temp file
    and swapped in atomically, so a crash cannot lose the original.
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames == CSV_FIELDS:
            return
        rows = list(reader)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows({k: r.get(k, "") for k in CSV_FIELDS} for r in rows)
    os.replace(tmp, path)


def _append_result_row(row: dict) -> None:
    os.makedirs(os.path.dirname(RESULTS_CSV), exist_ok=True)
    file_exists = os.path.exists(RESULTS_CSV)
    if file_exists:
        _upgrade_results_header(RESULTS_CSV)
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
        "asr_model": asr.MODEL_LABEL,
        "asr_device": asr.device,
        "manifest_rows": manifest_rows,
        "missing_count": len(missing_clips),
        "missing_clips": missing_clips[:MISSING_CLIPS_SHOWN],
        "alphabet_present": alphabet_present,
        "alphabet_expected": len(ALPHABET_LETTERS),
        "drive": {"fetchable_phrases": len(matcher._load_remote()),
                  "api_key": drive_fetch.api_key() is not None},
    }


def _fetch_drive_clips(plan: list, spell_fallback: bool = True) -> int:
    """Download the Drive clips a plan needs, in parallel; downgrade failures.

    Returns the wall-clock ms spent. Each fetched entry gets "source":
    "drive" and a status; one that cannot be fetched becomes "uncovered" with
    the reason, so the counts stay honest (recomputed by matcher.score).
    """
    import time
    from concurrent.futures import ThreadPoolExecutor

    todo = [e for e in plan if "drive" in e]
    if not todo:
        return 0
    t0 = time.perf_counter()
    # One download per file even when a word repeats in the sentence.
    unique = {e["drive"]["rel"]: e["drive"]["id"] for e in todo}
    with ThreadPoolExecutor(max_workers=4) as pool:
        fetched = dict(zip(unique, pool.map(lambda rel: drive_fetch.fetch(unique[rel], rel), unique)))
    for entry in todo:
        path, status = fetched[entry["drive"]["rel"]]
        info = entry.pop("drive")
        entry["source"] = "drive"
        entry["drive_status"] = status
        if path:
            entry["clips"] = [path]
        else:
            matcher.forget_remote(info["phrase"])
            entry.pop("means", None)
            letters = fingerspell.spell(entry["token"]) if spell_fallback else []
            if len(letters) > 1:      # not on disk, not fetchable -> spell it
                entry.update(type="spell", clips=letters, why="unknown",
                             drive_status=f"{status} - fingerspelled instead")
            else:
                entry.update(type="uncovered", clips=[], why=f"Drive: {status}")
    return int((time.perf_counter() - t0) * 1000)


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
    spell_unknown: str = Form("1"),
    speaker: str = Form(""),
    encode_error: str = Form(""),
    use_related: str = Form("0"),
    use_isl_order: str = Form("0"),
    denoise: str = Form("0"),
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

    from faster_whisper import decode_audio
    audio16k = decode_audio(upload_path, sampling_rate=16000)
    denoise_on = denoise.lower() in ("1", "true", "on")
    asr_result = asr.transcribe(audio16k, denoise=denoise_on)
    pitch = prosody.final_rise(audio16k)
    return _sign_and_log(
        run_id=run_id, server_start=server_start, asr_result=asr_result, pitch=pitch,
        note_source=f"upload{suffix}", utterance_id=utterance_id, speaker=speaker,
        spell_unknown=spell_unknown, use_related=use_related, use_isl_order=use_isl_order,
        denoise_on=denoise_on, encode_error=encode_error)


@app.post("/translate_text")
async def translate_text(
    text: str = Form(...),
    utterance_id: str = Form("adhoc"),
    spell_unknown: str = Form("1"),
    speaker: str = Form(""),
    use_related: str = Form("0"),
    use_isl_order: str = Form("0"),
):
    """Sign a typed (or corrected) transcript - the same pipeline without ASR.

    For when speech recognition mishears: the user fixes the text in the
    page and signs it, instead of re-recording. Logged with note "typed", so
    typed runs never count as ASR results.
    """
    import time
    server_start = time.perf_counter()
    asr_result = {"text": text.strip()[:500], "asr_ms": 0, "denoise_ms": 0,
                  "model": "typed", "device": "-"}
    pitch = {"voiced_ratio": 0.0, "median_f0": None, "final_rise_st": None, "rising": False}
    return _sign_and_log(
        run_id=uuid.uuid4().hex[:12], server_start=server_start, asr_result=asr_result,
        pitch=pitch, note_source="typed", utterance_id=utterance_id, speaker=speaker,
        spell_unknown=spell_unknown, use_related=use_related, use_isl_order=use_isl_order,
        denoise_on=False, encode_error="")


def _sign_and_log(*, run_id, server_start, asr_result, pitch, note_source, utterance_id,
                  speaker, spell_unknown, use_related, use_isl_order, denoise_on,
                  encode_error):
    """Text -> signs: match, Drive fetch, question, ISL order, log, response."""
    import time

    spell_unknown_on = spell_unknown.lower() in ("1", "true", "on")
    related_on = use_related.lower() in ("1", "true", "on")
    match_result = matcher.match(asr_result["text"], spell_unknown=spell_unknown_on,
                                 use_related=related_on)
    drive_ms = _fetch_drive_clips(match_result["plan"], spell_fallback=spell_unknown_on)
    if drive_ms:
        match_result.update(matcher.score(match_result["plan"]))

    question = isl_order.detect_question(asr_result["text"], match_result["plan"])
    question["pitch"] = pitch                     # evidence, not the decision (see isl_order)
    isl_on = use_isl_order.lower() in ("1", "true", "on")
    if isl_on:
        play_order, isl_rules = isl_order.reorder(match_result["plan"])
    else:
        play_order, isl_rules = list(range(len(match_result["plan"]))), []

    plan = [
        {
            "token": entry["token"],
            "type": entry["type"],
            "why": entry.get("why"),
            "means": entry.get("means"),
            "source": entry.get("source", "local"),
            "drive_status": entry.get("drive_status"),
            "clips": [_clip_url(clip) for clip in entry["clips"]],
        }
        for entry in match_result["plan"]
    ]

    server_ms = int((time.perf_counter() - server_start) * 1000)

    _append_result_row({
        "row_type": "translate",
        "run_id": run_id,
        "utterance_id": utterance_id,
        "speaker": speaker.strip()[:40],
        "timestamp": time.time(),
        "transcript": asr_result["text"],
        "n_total": match_result["counts"]["total"],
        "n_sign": match_result["counts"]["sign"],
        "n_spell": match_result["counts"]["spell"],
        "n_uncovered": match_result["counts"]["uncovered"],
        "coverage": round(match_result["coverage"], 4),
        "n_omitted": match_result["counts"]["omitted"],
        "content_coverage": round(match_result["content_coverage"], 4),
        "n_similar": match_result["counts"]["similar"],
        "n_related": match_result["counts"]["related"],
        "drive_ms": drive_ms,
        "question": question["type"] or "",
        "final_rise_st": "" if pitch["final_rise_st"] is None else pitch["final_rise_st"],
        "isl_rules": "; ".join(isl_rules),
        "denoise": int(denoise_on),
        "asr_ms": asr_result["asr_ms"],
        "match_ms": match_result["match_ms"],
        "server_ms": server_ms,
        "e2e_ms": "",
        # Which client audio path ran: browser-side 16kHz WAV encode, or the
        # raw-container fallback (still resampled to 16kHz mono by PyAV).
        "note": f"{note_source}; {asr_result['model']}@{asr_result['device']}"
                + ("; spell_unknown" if spell_unknown_on else "")
                + ("" if related_on else "; related_off")
                # Why the browser could not make the 16 kHz WAV, when it could not.
                + (f"; encode_error={encode_error[:120]}" if encode_error else ""),
    })

    return {
        "run_id": run_id,
        "transcript": asr_result["text"],
        "normalized": match_result["normalized"],
        "plan": plan,
        "coverage": round(match_result["coverage"], 4),
        "content_coverage": round(match_result["content_coverage"], 4),
        "content_coverage_with_similar": round(match_result["content_coverage_with_similar"], 4),
        "content_coverage_with_related": round(match_result["content_coverage_with_related"], 4),
        "question": question,
        "isl": {"enabled": isl_on, "order": play_order, "rules": isl_rules,
                "gloss": isl_order.gloss(match_result["plan"], play_order)},
        "counts": match_result["counts"],
        "timings": {
            "asr_ms": asr_result["asr_ms"],
            "match_ms": match_result["match_ms"],
            "drive_ms": drive_ms,
            "denoise_ms": asr_result["denoise_ms"],
            "server_ms": server_ms,
        },
        "asr": {"model": asr_result["model"], "device": asr_result["device"]},
    }



@app.get("/eval_sentences")
def get_eval_sentences():
    return {"sentences": eval_sentences()}


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
