"""WER of faster-whisper models on the held-out Svarah test speakers.

Decodes exactly as the app does (faster-whisper, greedy, language=en, same
initial prompt), so the number reflects what the demo would hear. Run it on
the stock model and the fine-tuned export to get the before/after table.

Usage:
  python -m tools.train.evaluate base.en models/whisper-base-en-svarah
Writes eval/asr_svarah_test.csv (per model: WER, utterances, speakers) and,
with --save-hyps, eval/asr_svarah_test_hyps.csv (every transcription, so
per-speaker tables and significance tests can be recomputed without a GPU).
"""
import argparse
import csv
import os
import sys
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

from tools.train import data  # noqa: E402
from tools.train.metrics import wer_corpus  # noqa: E402

OUT_CSV = "eval/asr_svarah_test.csv"
HYPS_CSV = "eval/asr_svarah_test_hyps.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+", help="faster-whisper model names or exported folders")
    ap.add_argument("--split", default="test")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--save-hyps", action="store_true")
    ap.add_argument("--no-summary", action="store_true", help="don't append to the WER summary")
    args = ap.parse_args()
    os.chdir(_REPO_ROOT)

    os.environ.setdefault("SPEECH_ISL_DEVICE", "auto")
    from src import asr
    from faster_whisper import WhisperModel
    asr._register_pip_cuda_libs()

    rows = data.load_splits()[args.split][:args.limit]
    speakers = len({r["speaker"] for r in rows})
    print(f"{args.split}: {len(rows)} utterances, {speakers} speakers, "
          f"{sum(r['duration'] for r in rows) / 3600:.2f} h")

    results, hyp_rows = [], []
    for name in args.models:
        model = WhisperModel(name, device="cuda", compute_type="float16")
        refs, hyps, t0 = [], [], time.time()
        for i, r in enumerate(rows, 1):
            segs, _ = model.transcribe(data.load_audio(r), language="en", beam_size=1,
                                       initial_prompt="Mothishwaran")
            hyps.append(" ".join(s.text.strip() for s in segs))
            refs.append(r["text"])
            hyp_rows.append({"model": os.path.basename(name.rstrip("/\\")), "idx": r["idx"],
                             "speaker": r["speaker"], "reference": r["text"], "hypothesis": hyps[-1]})
            if i % 200 == 0:
                print(f"  {name}: {i}/{len(rows)}", flush=True)
        w = wer_corpus(refs, hyps)
        results.append({"model": name, "split": args.split, "wer": round(w, 4),
                        "utterances": len(rows), "speakers": speakers,
                        "seconds": int(time.time() - t0)})
        print(f"{name:40} WER {w * 100:.2f}%")
        del model

    if args.save_hyps:
        with open(HYPS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(hyp_rows[0].keys()))
            w.writeheader()
            w.writerows(hyp_rows)
        print(f"wrote {HYPS_CSV} ({len(hyp_rows)} transcriptions)")
    if args.no_summary:
        return
    exists = os.path.exists(OUT_CSV)
    with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        if not exists:
            w.writeheader()
        w.writerows(results)
    print(f"appended -> {OUT_CSV}")


if __name__ == "__main__":
    main()
