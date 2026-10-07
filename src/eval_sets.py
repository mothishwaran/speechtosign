"""Reference sentences for spoken evaluation, with stable ids.

Shared by the API (the UI's "Eval utterance" list) and
tools/analyze_results.py (scoring each recording against its reference), so
the two can never disagree on what an id means.
"""
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (id prefix, label, file). u = Phase 0 demo set, s = everyday, h = held-out.
EVAL_SETS = [
    ("u", "Phase 0 demo", "eval/test_utterances.txt"),
    ("s", "everyday", "eval/test_sentences.txt"),
    ("h", "held-out", "eval/test_sentences_heldout.txt"),
]


def eval_sentences() -> list[dict]:
    out = []
    for prefix, label, rel in EVAL_SETS:
        path = os.path.join(_REPO_ROOT, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        for i, text in enumerate(lines, 1):
            sid = f"u{i}" if prefix == "u" else f"{prefix}{i:02d}"   # u1..u6 predate the padding
            out.append({"id": sid, "set": label, "text": text})
    return out
