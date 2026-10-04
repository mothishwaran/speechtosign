"""Longest-n-gram lookup against the manifest. See plans/02_SPEC.md section 4."""
import csv
import os
import string
import time

from src import fingerspell

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(_REPO_ROOT, "data", "manifest.csv")

_SENTENCE_END = (".", "?", "!", ":", ";")
_STRIP_CHARS = string.punctuation

_manifest: dict | None = None


def _load_manifest() -> dict:
    global _manifest
    if _manifest is not None:
        return _manifest

    manifest = {}
    with open(MANIFEST_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            phrase = row["phrase"].strip().lower()
            expected_len = len(phrase.split())
            declared_len = int(row["ngram_len"])
            if declared_len != expected_len:
                raise ValueError(
                    f"manifest row {row['id']!r}: ngram_len={declared_len} "
                    f"but phrase {phrase!r} has {expected_len} word(s)"
                )
            manifest[phrase] = {"id": row["id"], "local_path": row["local_path"]}
    _manifest = manifest
    return manifest


def max_ngram() -> int:
    """Longest phrase in the manifest, in words.

    Derived rather than hardcoded so adding a longer phrase to manifest.csv
    needs no code change — e.g. the 4-word "so far so good".
    """
    manifest = _load_manifest()
    return max((len(p.split()) for p in manifest), default=1)


def _ends_sentence(token: str) -> bool:
    stripped = token.rstrip()
    return bool(stripped) and stripped[-1] in _SENTENCE_END


def _normalize(token: str) -> str:
    lowered = token.lower()
    return "".join(c for c in lowered if c.isalnum() or c == "'")


def _tokenize(text: str):
    raw = text.split()
    orig, norm, sentence_initial = [], [], []
    for i, tok in enumerate(raw):
        stripped = tok.strip(_STRIP_CHARS)
        n = _normalize(stripped)
        if n == "":
            continue
        orig.append(stripped)
        norm.append(n)
        sentence_initial.append(i == 0 or _ends_sentence(raw[i - 1]))
    return orig, norm, sentence_initial


def match(text: str) -> dict:
    manifest = _load_manifest()
    start = time.perf_counter()

    orig, norm, sentence_initial = _tokenize(text)
    n_tokens = len(norm)

    longest = max_ngram()
    plan = []
    n_sign = n_spell = n_uncovered = 0
    i = 0
    while i < n_tokens:
        matched = False
        for gram in range(longest, 0, -1):
            if i + gram > n_tokens:
                continue
            candidate = " ".join(norm[i:i + gram])
            if candidate in manifest:
                entry = manifest[candidate]
                plan.append({
                    "token": candidate,
                    "type": "sign",
                    "clips": [entry["local_path"]],
                })
                n_sign += gram
                i += gram
                matched = True
                break
        if matched:
            continue

        tok_orig = orig[i]
        if tok_orig[0].isupper() and not sentence_initial[i]:
            plan.append({
                "token": tok_orig,
                "type": "spell",
                "clips": fingerspell.spell(tok_orig),
            })
            n_spell += 1
        else:
            plan.append({"token": tok_orig, "type": "uncovered", "clips": []})
            n_uncovered += 1
        i += 1

    coverage = (n_sign / n_tokens) if n_tokens else 0.0
    match_ms = int((time.perf_counter() - start) * 1000)

    return {
        "normalized": " ".join(norm),
        "plan": plan,
        "coverage": coverage,
        "counts": {
            "total": n_tokens,
            "sign": n_sign,
            "spell": n_spell,
            "uncovered": n_uncovered,
        },
        "match_ms": match_ms,
    }


if __name__ == "__main__":
    golden = match("Hello, thank you. My name is Mothishwaran.")
    assert golden["counts"] == {"total": 7, "sign": 4, "spell": 1, "uncovered": 2}, golden["counts"]
    assert abs(golden["coverage"] - 4 / 7) < 1e-9, golden["coverage"]
    assert [p["type"] for p in golden["plan"]] == [
        "sign", "sign", "uncovered", "sign", "uncovered", "spell",
    ], golden["plan"]
    assert golden["plan"][1]["token"] == "thank you", golden["plan"][1]
    assert golden["plan"][5]["token"] == "Mothishwaran", golden["plan"][5]
    assert len(golden["plan"][5]["clips"]) == 12, golden["plan"][5]["clips"]

    ty = match("thank you")
    assert len(ty["plan"]) == 1 and ty["plan"][0]["type"] == "sign", ty

    loose = match("You thank me")
    assert loose["counts"]["sign"] == 0, loose["counts"]

    empty = match("")
    assert empty["plan"] == [] and empty["coverage"] == 0.0, empty

    punct_only = match("!!! ... ???")
    assert punct_only["plan"] == [] and punct_only["coverage"] == 0.0, punct_only

    initial_name = match("Mothishwaran is here")
    assert initial_name["plan"][0]["type"] == "uncovered", initial_name["plan"][0]

    # Phrase longer than a trigram must still match as one unit (n-gram length
    # is derived from the manifest, not hardcoded).
    if "so far so good" in _load_manifest():
        long_phrase = match("So far so good")
        assert len(long_phrase["plan"]) == 1, long_phrase["plan"]
        assert long_phrase["plan"][0]["type"] == "sign", long_phrase["plan"]
        assert long_phrase["counts"]["sign"] == 4, long_phrase["counts"]
        assert long_phrase["coverage"] == 1.0, long_phrase

    no_match = match("The cat sat")
    assert all(p["type"] == "uncovered" for p in no_match["plan"]), no_match["plan"]
    assert no_match["coverage"] == 0.0, no_match

    print("OK")
    print(f"{'token':<15}{'type':<12}clips")
    for p in golden["plan"]:
        print(f"{p['token']:<15}{p['type']:<12}{p['clips']}")
    print(f"coverage={golden['coverage']:.3f}  counts={golden['counts']}")
