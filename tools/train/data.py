"""Svarah (Indian-accented English, AI4Bharat, CC BY 4.0) for fine-tuning.

Svarah ships as a single 'test' split (6,656 utterances, 117 speakers). We
re-split it BY SPEAKER - every utterance of a speaker lands in the same split
- so the test WER is measured on voices the model never trained on. Speakers
are identified by demographic profile (see speaker_of). Assignment is a hash
of that id: deterministic, reproducible on any machine, and recorded in
eval/svarah_speaker_split.csv (committed).

Layout (all under data/_derived/, gitignored):
  svarah/raw/        parquet files as downloaded
  svarah/audio/      one audio file per utterance, extracted once
  svarah/index.csv   idx, path, text, duration, speaker, split, demographics

Usage:
  hf auth login                       # once; accept the dataset terms first
  python -m tools.train.data          # download + extract + split
"""
import csv
import glob
import hashlib
import os
import sys
from collections import Counter, defaultdict

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ID = "ai4bharat/Svarah"
ROOT = os.path.join(_REPO_ROOT, "data", "_derived", "svarah")
RAW_DIR = os.path.join(ROOT, "raw")
AUDIO_DIR = os.path.join(ROOT, "audio")
# TRAIN_INDEX lets a smoke test point the pipeline at a tiny stand-in index.
INDEX = os.environ.get("TRAIN_INDEX", os.path.join(ROOT, "index.csv"))
SPLIT_RECORD = os.path.join(_REPO_ROOT, "eval", "svarah_speaker_split.csv")

TEST_FRACTION, DEV_FRACTION = 0.15, 0.10
META_FIELDS = ["gender", "age-group", "primary_language", "native_place_state"]
SPEAKER_FIELDS = ["gender", "age-group", "primary_language", "native_place_state",
                  "native_place_district", "highest_qualification", "job_category",
                  "occupation_domain"]


def speaker_of(meta: dict) -> str:
    """Speaker group for an utterance.

    Svarah has no speaker column, and the audio file names are NOT speaker
    ids: "281474976885573_f2194_chunk_0.wav" has ~2,900 distinct prefixes for
    117 speakers, so splitting on them would leak speakers into the test set.

    The full demographic profile is used instead. A speaker's profile never
    changes, so one speaker can never straddle two splits; two speakers who
    happen to share a profile are kept together, which errs on the safe side.
    """
    return "|".join(str(meta.get(k, "")).strip() for k in SPEAKER_FIELDS)


def split_of(speaker: str) -> str:
    h = int(hashlib.md5(speaker.encode()).hexdigest(), 16) % 10000 / 10000
    return "test" if h < TEST_FRACTION else "dev" if h < TEST_FRACTION + DEV_FRACTION else "train"


def prepare():
    import pyarrow.parquet as pq
    from huggingface_hub import snapshot_download

    snapshot_download(REPO_ID, repo_type="dataset", allow_patterns=["data/*.parquet"],
                      local_dir=RAW_DIR)
    files = sorted(glob.glob(os.path.join(RAW_DIR, "data", "*.parquet")))
    if not files:
        sys.exit("no parquet files downloaded - did you accept the dataset terms and run `hf auth login`?")

    os.makedirs(AUDIO_DIR, exist_ok=True)
    rows, idx = [], 0
    for fp in files:
        pf = pq.ParquetFile(fp)
        for batch in pf.iter_batches(batch_size=256):
            for rec in batch.to_pylist():
                audio = rec["audio_filepath"]          # {"bytes": ..., "path": ...}
                src_name = audio.get("path") or f"{idx}.wav"
                ext = os.path.splitext(src_name)[1] or ".wav"
                out = os.path.join(AUDIO_DIR, f"{idx:05d}{ext}")
                if not os.path.exists(out):
                    with open(out, "wb") as f:
                        f.write(audio["bytes"])
                spk = speaker_of(rec)
                rows.append({
                    "idx": idx, "path": os.path.relpath(out, _REPO_ROOT).replace(os.sep, "/"),
                    "source_name": src_name, "text": rec["text"].strip(),
                    "duration": round(float(rec["duration"]), 3), "speaker": spk,
                    "split": split_of(spk), **{k: rec.get(k, "") for k in META_FIELDS},
                })
                idx += 1
        print(f"  {os.path.basename(fp)}: {idx} utterances so far", flush=True)

    with open(INDEX, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Committed record of which speaker went where (no audio, no transcripts).
    per_spk = defaultdict(lambda: {"utts": 0, "hours": 0.0})
    for r in rows:
        per_spk[(r["speaker"], r["split"])]["utts"] += 1
        per_spk[(r["speaker"], r["split"])]["hours"] += r["duration"] / 3600
    with open(SPLIT_RECORD, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["speaker", "split", "utterances", "hours"])
        for (spk, sp), v in sorted(per_spk.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            w.writerow([spk, sp, v["utts"], round(v["hours"], 4)])

    summary()


def load_splits() -> dict:
    if not os.path.exists(INDEX):
        sys.exit(f"{INDEX} missing - run `python -m tools.train.data` first")
    out = {"train": [], "dev": [], "test": []}
    with open(INDEX, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["duration"] = float(r["duration"])
            out[r["split"]].append(r)
    return out


def load_audio(row):
    """16 kHz mono float32, decoded and resampled by PyAV (no ffmpeg needed)."""
    from faster_whisper import decode_audio
    return decode_audio(os.path.join(_REPO_ROOT, row["path"]), sampling_rate=16000)


def summary():
    s = load_splits()
    for name, rows in s.items():
        spk = {r["speaker"] for r in rows}
        print(f"{name:5}: {len(rows):5} utts  {sum(r['duration'] for r in rows) / 3600:5.2f} h  "
              f"{len(spk):3} speakers  {dict(Counter(r['gender'] for r in rows))}")
    leaks = ({r["speaker"] for r in s["train"]} & {r["speaker"] for r in s["test"]}) | \
            ({r["speaker"] for r in s["train"]} & {r["speaker"] for r in s["dev"]})
    print("speaker overlap between splits:", "NONE (ok)" if not leaks else f"LEAK: {sorted(leaks)[:5]}")


if __name__ == "__main__":
    prepare()
