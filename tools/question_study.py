"""Can pitch tell a spoken question from a statement? Measured on Svarah.

Items: every Svarah utterance whose transcript ends in "?" (387: wh-questions
starting what/where/when/who/why/how/which, and yes/no questions such as
"Can you ...?"), plus the same number of statements ending in "." drawn from
the same splits.
Feature: final pitch rise in semitones (src/prosody.final_rise).
Threshold: chosen on TRAIN speakers only (maximise balanced accuracy of
yes/no questions vs statements); reported on the unseen DEV + TEST speakers.

Writes eval/question_study.csv (one row per utterance) and
eval/question_threshold.json (the threshold src/prosody.py loads).
"""
import csv
import json
import os
import random
import sys

import numpy as np

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from src import prosody  # noqa: E402
from tools.train import data  # noqa: E402

WH = {"what", "what's", "where", "where's", "when", "who", "who's", "why", "how", "how's",
      "which", "whose", "whom"}
OUT = "eval/question_study.csv"
OUT_THR = "eval/question_threshold.json"


def kind_of(text: str) -> str | None:
    t = text.strip()
    if t.endswith("?"):
        first = t.lower().split()[0].strip(",.") if t.split() else ""
        return "wh" if first in WH else "yesno"
    if t.endswith("."):
        return "statement"
    return None


def balanced_acc(pos, neg, thr):
    tpr = np.mean(np.array(pos) >= thr) if pos else 0
    tnr = np.mean(np.array(neg) < thr) if neg else 0
    return (tpr + tnr) / 2, tpr, tnr


def main():
    os.chdir(_REPO_ROOT)
    rows = [r for split in data.load_splits().values() for r in split]
    qs = [r for r in rows if kind_of(r["text"]) in ("wh", "yesno")]
    stm = [r for r in rows if kind_of(r["text"]) == "statement"]
    rng = random.Random(0)
    items = qs + rng.sample(stm, len(qs))
    print(f"{len(qs)} questions + {len(qs)} statements")

    out = []
    for i, r in enumerate(items, 1):
        fr = prosody.final_rise(data.load_audio(r))
        out.append({"idx": r["idx"], "split": r["split"], "kind": kind_of(r["text"]),
                    "final_rise_st": fr["final_rise_st"], "median_f0": fr["median_f0"],
                    "text": r["text"]})
        if i % 200 == 0:
            print(f"  {i}/{len(items)}", flush=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    def feats(kind, splits):
        return [o["final_rise_st"] for o in out
                if o["kind"] == kind and o["split"] in splits and o["final_rise_st"] is not None]

    train_yn, train_st = feats("yesno", {"train"}), feats("statement", {"train"})
    grid = np.arange(-3, 8.01, 0.25)
    thr = max(grid, key=lambda t: balanced_acc(train_yn, train_st, t)[0])
    held = {"dev", "test"}
    res = {
        "threshold_st": round(float(thr), 2),
        "chosen_on": "train speakers: yes/no questions vs statements",
        "train": dict(zip(("balanced_acc", "yesno_recall", "statement_specificity"),
                          map(lambda v: round(float(v), 3), balanced_acc(train_yn, train_st, thr)))),
        "heldout_dev_test": dict(zip(("balanced_acc", "yesno_recall", "statement_specificity"),
                                     map(lambda v: round(float(v), 3),
                                         balanced_acc(feats("yesno", held), feats("statement", held), thr)))),
        "heldout_wh_recall_by_pitch": round(float(np.mean(np.array(feats("wh", held)) >= thr)), 3),
        "median_rise_st": {k: round(float(np.median(feats(k, {"train", "dev", "test"}))), 2)
                           for k in ("yesno", "wh", "statement")},
        "n_heldout": {k: len(feats(k, held)) for k in ("yesno", "wh", "statement")},
        "no_decision": sum(o["final_rise_st"] is None for o in out),
    }
    with open(OUT_THR, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
