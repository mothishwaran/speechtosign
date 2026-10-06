"""Evaluate the dictionary-scale pipeline on eval/test_sentences.txt.

Two levels, both reported per sentence:

  text  - matcher only, on the reference sentence. Pure lexicon coverage:
          what the dictionary can cover if ASR were perfect.
  tts   - (--tts, Windows only) each sentence is spoken by a Windows SAPI
          voice, sent through the real /translate endpoint (in-process
          TestClient, so the full API runs), and every returned clip URL is
          fetched back through the /data static mount. Reports WER, coverage
          on the actual transcript, ASR latency, and any clip that fails to
          serve.

SAPI voices are US-accented synthetic speech: the WER here is a pipeline
sanity check, not a measure of accuracy on Indian-accented speakers. Real
microphone runs still go through the browser and eval/results.csv.

/translate rows from this script go to eval/results_tts.csv, never to the
human-run evidence in eval/results.csv.

Usage: python tools/eval_dataset.py [--tts] [--voice "Microsoft Zira Desktop"]
"""
import argparse
import csv
import os
import statistics
import subprocess
import sys
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from src import matcher  # noqa: E402

SENTENCES = "eval/test_sentences.txt"
OUT_CSV = "eval/dataset_eval.csv"
TTS_RESULTS_CSV = "eval/results_tts.csv"
TTS_DIR = "data/_derived/tts"


def wer(ref: str, hyp: str) -> float:
    r = matcher.normalize_phrase(ref).split()
    h = matcher.normalize_phrase(hyp).split()
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(h)] / max(len(r), 1)


def synthesize(text: str, path: str, voice: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ps = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        f"$s.SelectVoice('{voice}');"
        f"$s.SetOutputToWaveFile('{os.path.abspath(path)}');"
        "$s.Speak($env:TTS_TEXT); $s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True,
                   env={**os.environ, "TTS_TEXT": text})


def plan_str(plan) -> str:
    return " ".join(
        f"[{p['token']}]" if p["type"] == "sign"
        else f"<{p['token']}>" if p["type"] == "spell" else p["token"]
        for p in plan
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tts", action="store_true", help="also run spoken end-to-end tests")
    ap.add_argument("--voice", default="Microsoft Zira Desktop")
    args = ap.parse_args()
    os.chdir(_REPO_ROOT)

    with open(SENTENCES, encoding="utf-8") as f:
        sentences = [s.strip() for s in f if s.strip()]

    rows = []
    for i, ref in enumerate(sentences, 1):
        m = matcher.match(ref)
        rows.append({"id": f"s{i:02d}", "reference": ref,
                     "text_coverage": round(m["coverage"], 4),
                     "text_plan": plan_str(m["plan"])})

    if args.tts:
        from fastapi.testclient import TestClient
        from src import api
        api.RESULTS_CSV = os.path.join(_REPO_ROOT, TTS_RESULTS_CSV)

        with TestClient(api.app) as client:
            for row in rows:
                wav = f"{TTS_DIR}/{args.voice.split()[1].lower()}/{row['id']}.wav"
                if not os.path.exists(wav):
                    synthesize(row["reference"], wav, args.voice)
                with open(wav, "rb") as f:
                    resp = client.post(
                        "/translate",
                        files={"audio": (f"{row['id']}.wav", f, "audio/wav")},
                        data={"client_t0": str(int(time.time() * 1000)),
                              "utterance_id": f"tts_{row['id']}"},
                    )
                resp.raise_for_status()
                out = resp.json()

                bad = []
                for p in out["plan"]:
                    for url in p["clips"]:
                        r = client.get(url)
                        if r.status_code != 200 or not r.headers.get("content-type", "").startswith("video/"):
                            bad.append(f"{url} -> {r.status_code}")
                row.update({
                    "transcript": out["transcript"],
                    "wer": round(wer(row["reference"], out["transcript"]), 4),
                    "speech_coverage": out["coverage"],
                    "speech_plan": plan_str(out["plan"]),
                    "asr_ms": out["timings"]["asr_ms"],
                    "n_clips": sum(len(p["clips"]) for p in out["plan"]),
                    "n_failed": len(bad),
                    "clips_failed": "; ".join(bad),
                })

    fields = list(rows[0].keys())
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"{'id':<5}{'text':>6}", end="")
    print(f"{'speech':>8}{'WER':>7}{'asr ms':>8}  " if args.tts else "  ", end="")
    print("plan   ([sign] <spelled> uncovered)")
    for r in rows:
        print(f"{r['id']:<5}{r['text_coverage'] * 100:>5.0f}%", end="")
        if args.tts:
            print(f"{r['speech_coverage'] * 100:>7.0f}%{r['wer'] * 100:>6.0f}%{r['asr_ms']:>8}  ", end="")
            print(r["speech_plan"])
            if r["transcript"].strip().lower() != r["reference"].strip().lower():
                print(f"{'':<36}heard: {r['transcript']}")
            if r["clips_failed"]:
                print(f"{'':<36}CLIP FAILURES: {r['clips_failed']}")
        else:
            print("  " + r["text_plan"])

    print(f"\nmean text coverage   : {statistics.mean(r['text_coverage'] for r in rows) * 100:.1f}%")
    if args.tts:
        print(f"mean speech coverage : {statistics.mean(r['speech_coverage'] for r in rows) * 100:.1f}%")
        print(f"mean WER             : {statistics.mean(r['wer'] for r in rows) * 100:.1f}%  (synthetic {args.voice})")
        print(f"median ASR latency   : {statistics.median(r['asr_ms'] for r in rows):.0f} ms")
        total = sum(r["n_clips"] for r in rows)
        failed = sum(r["n_failed"] for r in rows)
        print(f"clips served OK      : {total - failed}/{total}")
    print(f"wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
