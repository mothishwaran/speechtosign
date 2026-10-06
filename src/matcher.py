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

# Whisper emits typographic apostrophes as often as ASCII ones ("don’t"); fold
# them so contractions still match the manifest's "don't".
_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "`": "'"})

_manifest: dict | None = None
_max_ngram: int | None = None


def _load_manifest() -> dict:
    global _manifest, _max_ngram
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
            if phrase in manifest:
                raise ValueError(
                    f"manifest row {row['id']!r}: phrase {phrase!r} already "
                    f"defined by row {manifest[phrase]['id']!r}"
                )
            manifest[phrase] = {"id": row["id"], "local_path": row["local_path"]}
    _manifest = manifest
    _max_ngram = None
    return manifest


def max_ngram() -> int:
    """Longest phrase in the manifest, in words.

    Derived rather than hardcoded so adding a longer phrase to manifest.csv
    needs no code change — e.g. the 4-word "so far so good". Cached, since the
    full ISLRTC manifest has thousands of rows and this runs on every match.
    """
    global _max_ngram
    manifest = _load_manifest()
    if _max_ngram is None:
        _max_ngram = max((len(p.split()) for p in manifest), default=1)
    return _max_ngram


def _ends_sentence(token: str) -> bool:
    stripped = token.rstrip()
    return bool(stripped) and stripped[-1] in _SENTENCE_END


def _normalize(token: str) -> str:
    lowered = token.lower().translate(_APOSTROPHES)
    return "".join(c for c in lowered if c.isalnum() or c == "'")


def _is_pronoun_i(norm_token: str) -> bool:
    # English always capitalises "I" (and I'm, I'll, I've, I'd), so the
    # capitalised-mid-sentence name rule must not fingerspell it.
    return norm_token == "i" or norm_token.startswith("i'")


def normalize_phrase(text: str) -> str:
    """Normalize a phrase exactly as match() normalizes a transcript.

    tools/build_manifest.py writes every manifest phrase through this, so a
    dictionary entry and a spoken utterance can never disagree on spelling
    rules (hyphens, apostrophes, casing).
    """
    return " ".join(n for n in (_normalize(t.strip(_STRIP_CHARS)) for t in text.split()) if n)


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
        if tok_orig[0].isupper() and not sentence_initial[i] and not _is_pronoun_i(norm[i]):
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
    # --- Part 1: algorithm tests against the frozen Phase 0 vocabulary ------
    # A fixed fixture, not data/manifest.csv, so the spec's golden case (§4,
    # coverage 4/7) stays verifiable however large the real dictionary grows.
    _manifest = {
        p: {"id": p.replace(" ", "_"), "local_path": f"data/clips/{p.replace(' ', '_')}.mp4"}
        for p in ("hello", "thank you", "sorry", "please", "name", "so far so good")
    }
    _max_ngram = None

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

    pronoun = match("Today I am sure I'm right, said Ravi")
    assert [p["type"] for p in pronoun["plan"]].count("spell") == 1, pronoun["plan"]
    assert pronoun["plan"][-1]["token"] == "Ravi", pronoun["plan"]

    # Phrase longer than a trigram must still match as one unit (n-gram length
    # is derived from the manifest, not hardcoded).
    long_phrase = match("So far so good")
    assert len(long_phrase["plan"]) == 1, long_phrase["plan"]
    assert long_phrase["plan"][0]["type"] == "sign", long_phrase["plan"]
    assert long_phrase["counts"]["sign"] == 4, long_phrase["counts"]
    assert long_phrase["coverage"] == 1.0, long_phrase

    no_match = match("The cat sat")
    assert all(p["type"] == "uncovered" for p in no_match["plan"]), no_match["plan"]
    assert no_match["coverage"] == 0.0, no_match

    assert normalize_phrase("I Don’t Know!") == "i don't know"
    assert normalize_phrase("Non-bailable  Offence") == "nonbailable offence"

    print("OK  (part 1: Phase 0 fixture)")
    print(f"{'token':<15}{'type':<12}clips")
    for p in golden["plan"]:
        print(f"{p['token']:<15}{p['type']:<12}{p['clips']}")
    print(f"coverage={golden['coverage']:.3f}  counts={golden['counts']}")

    # --- Part 2: the real manifest built from the ISLRTC dictionary ---------
    _manifest = None
    _max_ngram = None
    real = _load_manifest()
    assert len(real) > 1000, f"manifest has only {len(real)} phrases - run tools/build_manifest.py"

    demo = match("Hello, thank you. My name is Mothishwaran.")
    assert [(p["token"], p["type"]) for p in demo["plan"]] == [
        ("hello", "sign"), ("thank you", "sign"),
        ("my name is", "sign"), ("Mothishwaran", "spell"),
    ], demo["plan"]
    assert demo["counts"] == {"total": 7, "sign": 6, "spell": 1, "uncovered": 0}, demo["counts"]

    curly = match("I don’t know.")
    assert [(p["token"], p["type"]) for p in curly["plan"]] == [("i don't know", "sign")], curly["plan"]

    every_clip = [c for p in demo["plan"] for c in p["clips"]]
    missing = [c for c in every_clip if not os.path.exists(os.path.join(_REPO_ROOT, c))]
    assert not missing, f"demo clips missing on disk: {missing}"

    print(f"\nOK  (part 2: real manifest, {len(real)} phrases, longest {max_ngram()} words)")
    for p in demo["plan"]:
        print(f"{p['token']:<15}{p['type']:<12}{p['clips'][:1]}{' ...' if len(p['clips']) > 1 else ''}")
    print(f"coverage={demo['coverage']:.3f}  counts={demo['counts']}")
