"""Turn eval/results.csv into the tables for the results slides.

Joins the `translate` and `frame` rows on run_id, then reports:
  1. latency (median + range - never a lone best-case number)
  2. real-voice ASR accuracy: WER of every tagged recording against its
     reference sentence (src/eval_sets.py), per speaker and per sentence set
  3. coverage per speaker and set
  4. which browser audio path ran, and why the fallback happened if it did

Usage: python tools/analyze_results.py [path/to/results.csv] [--since YYYY-MM-DD]
"""
import argparse
import csv
import datetime as dt
import os
import statistics
import sys
from collections import defaultdict

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from src.eval_sets import eval_sentences  # noqa: E402
from src.matcher import normalize_phrase  # noqa: E402


def num(v, cast=float):
    try:
        return cast(v)
    except (TypeError, ValueError):
        return None


def spread(values, unit="ms"):
    vals = [v for v in values if v is not None]
    if not vals:
        return "-"
    med = statistics.median(vals)
    if len(vals) == 1:
        return f"{med:.0f} {unit}"
    return f"{med:.0f} {unit}  (range {min(vals):.0f}-{max(vals):.0f}, n={len(vals)})"


def word_errors(ref: str, hyp: str) -> tuple[int, int]:
    """(edit distance in words, reference length) after matcher normalization."""
    r, h = normalize_phrase(ref).split(), normalize_phrase(hyp).split()
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
    return d[len(h)], len(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", default=os.path.join(_REPO_ROOT, "eval", "results.csv"))
    ap.add_argument("--since", help="only runs on/after this date (YYYY-MM-DD)")
    args = ap.parse_args()

    refs = {s["id"]: s for s in eval_sentences()}
    since = dt.datetime.fromisoformat(args.since).timestamp() if args.since else 0

    runs = {}
    try:
        with open(args.csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                r = runs.setdefault(row["run_id"], {})
                if row["row_type"] == "translate":
                    r.update({
                        "ts": num(row["timestamp"]) or 0,
                        "utterance_id": row.get("utterance_id", "") or "adhoc",
                        "speaker": (row.get("speaker") or "").strip() or "(unnamed)",
                        "transcript": row["transcript"],
                        "coverage": num(row["coverage"]),
                        "content_coverage": num(row.get("content_coverage")),
                        "asr_ms": num(row["asr_ms"]), "match_ms": num(row["match_ms"]),
                        "server_ms": num(row["server_ms"]), "note": row.get("note", ""),
                    })
                elif row["row_type"] == "frame":
                    r["e2e_ms"] = num(row["e2e_ms"])
    except FileNotFoundError:
        print(f"no results yet at {args.csv} - record some runs first.")
        return

    complete = [r for r in runs.values() if "transcript" in r and r["ts"] >= since]
    if not complete:
        print("no completed runs in range.")
        return
    evals = [r for r in complete if r["utterance_id"] in refs]
    print(f"runs: {len(complete)}   tagged with a reference sentence: {len(evals)}\n")

    print("=" * 72 + "\nTABLE 1 - Latency (all runs)\n" + "=" * 72)
    for label, key in [("ASR", "asr_ms"), ("Match", "match_ms"),
                       ("Server total", "server_ms"), ("End-to-end", "e2e_ms")]:
        print(f"  {label:<14} {spread([r.get(key) for r in complete])}")

    if evals:
        print("\n" + "=" * 72 + "\nTABLE 2 - Real-voice ASR accuracy and coverage\n" + "=" * 72)
        groups = defaultdict(list)
        for r in evals:
            groups[(r["speaker"], refs[r["utterance_id"]]["set"])].append(r)
        print(f"  {'speaker':<16}{'set':<14}{'runs':>5}{'WER':>8}{'exact':>7}"
              f"{'coverage':>10}{'ISL-signed':>12}")
        for (spk, st), rs in sorted(groups.items()):
            errs = [word_errors(refs[r["utterance_id"]]["text"], r["transcript"]) for r in rs]
            wer = sum(e for e, _ in errs) / max(sum(n for _, n in errs), 1)
            exact = sum(e == 0 for e, _ in errs)
            cov = statistics.mean(r["coverage"] for r in rs if r["coverage"] is not None)
            cc = [r["content_coverage"] for r in rs if r["content_coverage"] is not None]
            isl = f"{statistics.mean(cc) * 100:.1f}%" if cc else "-"   # pre-Group-B rows lack it
            print(f"  {spk[:15]:<16}{st:<14}{len(rs):>5}{wer * 100:>7.1f}%{exact:>4}/{len(rs):<2}"
                  f"{cov * 100:>9.1f}%{isl:>12}")

        print("\n  Misrecognised recordings (reference vs heard):")
        shown = 0
        for r in sorted(evals, key=lambda x: (x["speaker"], x["utterance_id"])):
            e, n = word_errors(refs[r["utterance_id"]]["text"], r["transcript"])
            if e:
                print(f"    {r['speaker'][:12]:<13}{r['utterance_id']:<5} {e}/{n} words wrong")
                print(f"        expected: {refs[r['utterance_id']]['text']}")
                print(f"        heard   : {r['transcript']}")
                shown += 1
        if not shown:
            print("    none - every tagged recording was transcribed exactly")

    print("\n" + "=" * 72 + "\nAudio path used by the browser\n" + "=" * 72)
    first = [r["note"].split(";")[0] for r in complete]
    print(f"  browser-encoded 16 kHz WAV : {first.count('upload.wav')}")
    print(f"  raw-container fallback     : {len(first) - first.count('upload.wav')}"
          f"   (PyAV still resamples to 16 kHz mono server-side)")
    reasons = [r["note"].split("encode_error=", 1)[1] for r in complete if "encode_error=" in r["note"]]
    for why in sorted(set(reasons)):
        print(f"    fallback reason x{reasons.count(why)}: {why}")


if __name__ == "__main__":
    main()
