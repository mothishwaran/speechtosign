"""Turn eval/results.csv into the tables that go on the Initial Results slide.

Joins the `translate` and `frame` rows on run_id, then reports latency and
coverage. Median plus range — never a lone best-case number.

Usage: python tools/analyze_results.py [path/to/results.csv]
"""
import csv
import statistics
import sys

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "eval/results.csv"

UTTERANCES = {
    "u1": "Hello, thank you. My name is Mothishwaran.",
    "u2": "Hello.",
    "u3": "Thank you.",
    "u4": "Sorry.",
    "u5": "Please.",
    "u6": "My name is Mothishwaran.",
}


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


def main():
    runs = {}
    try:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rid = row["run_id"]
                r = runs.setdefault(rid, {})
                if row["row_type"] == "translate":
                    r.update({
                        "utterance_id": row.get("utterance_id", "") or "adhoc",
                        "transcript": row["transcript"],
                        "coverage": num(row["coverage"]),
                        "n_total": num(row["n_total"], int),
                        "n_sign": num(row["n_sign"], int),
                        "n_spell": num(row["n_spell"], int),
                        "n_uncovered": num(row["n_uncovered"], int),
                        "asr_ms": num(row["asr_ms"]),
                        "match_ms": num(row["match_ms"]),
                        "server_ms": num(row["server_ms"]),
                        "note": row.get("note", ""),
                    })
                elif row["row_type"] == "frame":
                    r["e2e_ms"] = num(row["e2e_ms"])
    except FileNotFoundError:
        print(f"no results yet at {CSV_PATH} - record some runs first.")
        return

    complete = [r for r in runs.values() if "transcript" in r]
    if not complete:
        print("no completed runs in the log yet.")
        return

    evals = [r for r in complete if r["utterance_id"] in UTTERANCES]
    print(f"total runs: {len(complete)}   tagged eval runs: {len(evals)}\n")

    print("=" * 72)
    print("TABLE 1 - Latency (all completed runs)")
    print("=" * 72)
    for label, key in [
        ("ASR", "asr_ms"), ("Match", "match_ms"),
        ("Server total", "server_ms"), ("End-to-end", "e2e_ms"),
    ]:
        print(f"  {label:<14} {spread([r.get(key) for r in complete])}")

    if evals:
        print("\n" + "=" * 72)
        print("TABLE 2 - Coverage per eval utterance")
        print("=" * 72)
        print(f"  {'id':<4}{'coverage':>10}{'sign':>6}{'spell':>7}{'uncov':>7}{'tot':>5}   transcript")
        for uid in sorted(UTTERANCES):
            for r in [x for x in evals if x["utterance_id"] == uid]:
                cov = f"{r['coverage'] * 100:.1f}%" if r["coverage"] is not None else "-"
                print(f"  {uid:<4}{cov:>10}{r['n_sign']:>6}{r['n_spell']:>7}"
                      f"{r['n_uncovered']:>7}{r['n_total']:>5}   {r['transcript']}")

        covs = [r["coverage"] for r in evals if r["coverage"] is not None]
        if covs:
            print(f"\n  mean coverage across {len(covs)} eval runs: {statistics.mean(covs) * 100:.1f}%")

        print("\n" + "=" * 72)
        print("TABLE 3 - ASR accuracy check (read these yourself)")
        print("=" * 72)
        for uid in sorted(UTTERANCES):
            for r in [x for x in evals if x["utterance_id"] == uid]:
                expected = UTTERANCES[uid]
                exact = r["transcript"].strip().lower() == expected.strip().lower()
                mark = "exact" if exact else "DIFFERS"
                print(f"  {uid}  [{mark}]")
                print(f"      expected : {expected}")
                print(f"      got      : {r['transcript']}")

    paths = [r.get("note", "") for r in complete]
    wav = sum(1 for p in paths if p == "upload.wav")
    webm = sum(1 for p in paths if p == "upload.webm")
    if wav or webm:
        print("\n" + "=" * 72)
        print("Audio path used")
        print("=" * 72)
        print(f"  browser-encoded 16kHz WAV : {wav}")
        print(f"  raw container fallback    : {webm}   (PyAV resamples to 16kHz server-side)")


if __name__ == "__main__":
    main()
