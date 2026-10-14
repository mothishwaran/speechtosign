"""Longest-n-gram lookup against the manifest. See plans/02_SPEC.md section 4."""
import csv
import os
import string
import time

from src import fingerspell

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(_REPO_ROOT, "data", "manifest.csv")
# word -> sign for inflected forms and WordNet synonyms (tools/build_synonyms.py)
SYNONYMS_PATH = os.path.join(_REPO_ROOT, "data", "synonyms.csv")
# phrase -> Drive file for signs not on this machine yet (src/drive_fetch.py)
DRIVE_MANIFEST_PATH = os.path.join(_REPO_ROOT, "data", "drive_manifest.csv")

_SENTENCE_END = (".", "?", "!", ":", ";")
_STRIP_CHARS = string.punctuation

# Whisper emits typographic apostrophes as often as ASCII ones ("don’t"); fold
# them so contractions still match the manifest's "don't".
_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "`": "'"})

_manifest: dict | None = None
_max_ngram: int | None = None
_synonyms: dict | None = None
_remote: dict | None = None
_max_ngram_remote: int | None = None


def _load_remote() -> dict:
    """phrase -> {"drive_id", "rel"} for dictionary signs fetchable from Drive."""
    global _remote, _max_ngram_remote
    if _remote is None:
        from src import drive_fetch
        bad = drive_fetch.rejected()
        _remote = {}
        if os.path.exists(DRIVE_MANIFEST_PATH):
            with open(DRIVE_MANIFEST_PATH, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r["rel"] not in bad:
                        _remote[r["phrase"]] = {"drive_id": r["drive_id"], "rel": r["rel"]}
        _max_ngram_remote = max((len(p.split()) for p in _remote), default=1)
    return _remote


def forget_remote(phrase: str) -> None:
    """Drop a Drive phrase whose clip turned out unusable (no retry this session)."""
    if _remote is not None:
        _remote.pop(phrase, None)


def _load_synonyms() -> dict:
    """word -> (target phrase, "form" | "synonym" | "related").

    Word forms and related words are used unless a reviewer rejected them;
    synonyms are proposals and are used only once a reviewer marked them ok.
    """
    global _synonyms
    if _synonyms is None:
        _synonyms = {}
        if os.path.exists(SYNONYMS_PATH):
            with open(SYNONYMS_PATH, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    review = r.get("review", "").strip().lower()
                    if review == "ok" or (r["kind"] in ("form", "related") and review != "reject"):
                        _synonyms[r["word"]] = (r["target"], r["kind"])
    return _synonyms


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


# English function words that ISL does not sign: articles, forms of "be",
# and the infinitive/possessive particles. Leaving them out is correct ISL,
# not a gap in the dictionary, so they get their own type and are excluded
# from content_coverage. Checked only AFTER dictionary matching, so phrases
# that contain them ("my name is") still match as one sign.
ISL_OMITTED = frozenset({
    "a", "an", "the",
    "is", "am", "are", "was", "were", "be", "been", "being",
    "to", "of",
})


_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
         "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_WORD_VALUE = {w: i for i, w in enumerate(_ONES)} | {w: 10 * i for i, w in enumerate(_TENS) if w}


def number_words(n: int) -> list[str]:
    """Spoken English words for 0 <= n < 1,00,000 (thousand-based, as said aloud)."""
    if n < 20:
        return [_ONES[n]]
    if n < 100:
        return [_TENS[n // 10]] + ([_ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [_ONES[n // 100], "hundred"] + (number_words(n % 100) if n % 100 else [])
    return number_words(n // 1000) + ["thousand"] + (number_words(n % 1000) if n % 1000 else [])


def _digit_words(digits: str) -> list[str]:
    return [_ONES[int(d)] for d in digits]


def number_signs(token: str, manifest: dict) -> list[str] | None:
    """Dictionary phrases that sign a spoken number, or None if `token` isn't one.

    "25" -> twenty five; "2026" -> two thousand twenty six; "7:30" -> seven
    thirty; "twenty-five" -> twenty five. The dictionary has no sign for
    forty / eighty / ninety (or lakh / crore on their own), so when any word
    of the reading is missing the number is signed digit by digit instead
    ("45" -> four five), which ISL signers also do. Only local signs are
    used, so numbers never wait on a Drive download.
    """
    t = token.replace(",", "")
    if ":" in t:                                     # clock time
        parts = t.split(":")
        if len(parts) == 2 and all(p.isdigit() for p in parts) and len(parts[1]) == 2:
            words = number_words(int(parts[0])) + (number_words(int(parts[1])) if int(parts[1]) else [])
            return words if all(w in manifest for w in words) else \
                _digit_words(parts[0]) + _digit_words(parts[1])
        return None
    if "-" in t:                                     # "twenty-five"
        parts = t.lower().split("-")
        if len(parts) > 1 and all(p in _WORD_VALUE for p in parts):
            return parts if all(p in manifest for p in parts) else None
        return None
    if not t.isdigit() or len(t) > 9:
        return None
    n = int(t)
    if n < 100000:
        words = number_words(n)
        if all(w in manifest for w in words):
            return words
    return _digit_words(t) if all(w in manifest for w in _digit_words(t)) else None


def _clip_for(phrase: str, manifest: dict, remote: dict) -> dict | None:
    """Clip for a dictionary phrase: local file, or a Drive file to fetch."""
    if phrase in manifest:
        return {"clips": [manifest[phrase]["local_path"]]}
    if phrase in remote:
        from src import drive_fetch
        r = remote[phrase]
        cached = drive_fetch.playable_path(r["rel"])
        if cached:                       # fetched earlier: plays from disk
            return {"clips": [cached]}
        return {"clips": [drive_fetch.local_path(r["rel"])],
                "drive": {"id": r["drive_id"], "rel": r["rel"], "phrase": phrase}}
    return None


def match(text: str, spell_unknown: bool = False, use_drive: bool = True,
          use_related: bool = True) -> dict:
    """Plan the sign sequence for a transcript.

    Token types: sign (dictionary clip, including inflected forms such as
    "books" -> book; may need fetching from Drive, marked by a "drive" key),
    similar (a reviewed synonym's sign, e.g. "physician" -> doctor), related
    (closest more general sign, e.g. "sparrow" -> bird), spell (fingerspelled
    - a name, or any unknown word when spell_unknown=True), omitted (not
    signed in ISL), uncovered (no sign available, dropped).
    Every entry carries "n_words", the transcript words it accounts for.
    """
    manifest = _load_manifest()
    synonyms = _load_synonyms()
    remote = _load_remote() if use_drive else {}
    start = time.perf_counter()

    orig, norm, sentence_initial = _tokenize(text)
    n_tokens = len(norm)

    longest = max(max_ngram(), _max_ngram_remote or 1) if use_drive else max_ngram()
    plan = []
    i = 0
    while i < n_tokens:
        matched = False
        for gram in range(longest, 0, -1):
            if i + gram > n_tokens:
                continue
            candidate = " ".join(norm[i:i + gram])
            clip = _clip_for(candidate, manifest, remote)
            if clip:
                plan.append({"token": candidate, "type": "sign", "n_words": gram, **clip})
                i += gram
                matched = True
                break
        if matched:
            continue

        tok_orig = orig[i]
        spoken_number = number_signs(tok_orig, manifest)
        if spoken_number:
            plan.append({"token": tok_orig, "type": "sign", "means": " ".join(spoken_number),
                         "n_words": 1, "clips": [manifest[w]["local_path"] for w in spoken_number]})
            i += 1
            continue
        is_name = tok_orig[0].isupper() and not sentence_initial[i] and not _is_pronoun_i(norm[i])
        mapped = synonyms.get(norm[i])
        if mapped and mapped[1] == "related" and not use_related:
            mapped = None
        clip = _clip_for(mapped[0], manifest, remote) if mapped else None
        if is_name:
            plan.append({"token": tok_orig, "type": "spell", "why": "name", "n_words": 1,
                         "clips": fingerspell.spell(tok_orig)})
        elif norm[i] in ISL_OMITTED:
            plan.append({"token": tok_orig, "type": "omitted", "n_words": 1, "clips": []})
        elif clip:
            kind = mapped[1]
            # form = same word inflected; synonym = same meaning; related =
            # closest more general sign (an approximation, labelled as such)
            entry_type = {"form": "sign", "synonym": "similar", "related": "related"}[kind]
            plan.append({"token": tok_orig, "type": entry_type, "means": mapped[0],
                         "n_words": 1, **clip})
        # len > 1: a lone letter ("I") spelled as its alphabet sign would
        # read as the letter, not the word.
        elif spell_unknown and len(fingerspell.spell(tok_orig)) > 1:
            plan.append({"token": tok_orig, "type": "spell", "why": "unknown", "n_words": 1,
                         "clips": fingerspell.spell(tok_orig)})
        else:
            plan.append({"token": tok_orig, "type": "uncovered", "n_words": 1, "clips": []})
        i += 1

    # Sentence index of every entry (src/isl_order.py reorders within a
    # sentence, never across): a new sentence starts after . ? ! : ;
    sent_of_token, s = [], -1
    for k in range(n_tokens):
        s += 1 if (k == 0 or sentence_initial[k]) else 0
        sent_of_token.append(s)
    # ...and whether that sentence ended with "?" (same token filter as _tokenize)
    q_sents, k = set(), 0
    for tok in text.split():
        if _normalize(tok.strip(_STRIP_CHARS)):
            if tok.rstrip().endswith("?"):
                q_sents.add(sent_of_token[k])
            k += 1
    pos = 0
    for entry in plan:
        entry["sent"] = sent_of_token[pos] if pos < n_tokens else s
        entry["sent_q"] = entry["sent"] in q_sents
        pos += entry["n_words"]

    out = {"normalized": " ".join(norm), "plan": plan, **score(plan)}
    out["match_ms"] = int((time.perf_counter() - start) * 1000)
    return out


def score(plan: list) -> dict:
    """Counts and coverage figures for a plan (recomputed if the server
    downgrades an entry, e.g. a Drive clip that could not be fetched)."""
    counts = {"total": 0, "sign": 0, "similar": 0, "related": 0,
              "spell": 0, "omitted": 0, "uncovered": 0}
    for p in plan:
        counts["total"] += p["n_words"]
        counts[p["type"]] += p["n_words"] if p["type"] == "sign" else 1
    n = counts["total"]
    content = n - counts["omitted"]
    # coverage keeps its Phase 0 definition (signed tokens / all tokens) so
    # results stay comparable; content_coverage leaves out the words ISL does
    # not sign. Synonym and related signs are approximations, so each gets
    # its own cumulative figure rather than being mixed into the exact one.
    return {
        "coverage": counts["sign"] / n if n else 0.0,
        "content_coverage": counts["sign"] / content if content else 0.0,
        "content_coverage_with_similar":
            (counts["sign"] + counts["similar"]) / content if content else 0.0,
        "content_coverage_with_related":
            (counts["sign"] + counts["similar"] + counts["related"]) / content if content else 0.0,
        "counts": counts,
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
    _synonyms = {}   # fixture tests exercise exact matching only
    _remote, _max_ngram_remote = {}, 1

    golden = match("Hello, thank you. My name is Mothishwaran.")
    # Spec §4 golden case. Coverage is unchanged at 4/7; "is" is now typed
    # "omitted" (ISL does not sign it) where Phase 0 called it "uncovered".
    assert golden["counts"] == {"total": 7, "sign": 4, "similar": 0, "related": 0, "spell": 1, "omitted": 1, "uncovered": 1}, golden["counts"]
    assert abs(golden["coverage"] - 4 / 7) < 1e-9, golden["coverage"]
    assert abs(golden["content_coverage"] - 4 / 6) < 1e-9, golden["content_coverage"]
    assert [p["type"] for p in golden["plan"]] == [
        "sign", "sign", "uncovered", "sign", "omitted", "spell",
    ], golden["plan"]
    assert golden["plan"][5]["why"] == "name", golden["plan"][5]
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
    assert [p["type"] for p in no_match["plan"]] == ["omitted", "uncovered", "uncovered"], no_match["plan"]
    assert no_match["coverage"] == 0.0, no_match

    # Omitted words never shadow a dictionary phrase that contains them.
    phrase_first = match("so far so good is the best")
    assert phrase_first["plan"][0]["token"] == "so far so good", phrase_first["plan"]
    assert [p["type"] for p in phrase_first["plan"][1:3]] == ["omitted", "omitted"], phrase_first["plan"]

    # Optional fingerspelling of unknown words: off by default, labelled
    # "unknown" (not "name") when on, and never applied to omitted words.
    off = match("please sit")
    assert off["plan"][1]["type"] == "uncovered", off["plan"]
    on = match("please sit is", spell_unknown=True)
    assert [(p["type"], p.get("why")) for p in on["plan"]] == [
        ("sign", None), ("spell", "unknown"), ("omitted", None)], on["plan"]
    assert len(on["plan"][1]["clips"]) == 3, on["plan"][1]
    digits = match("please 42", spell_unknown=True)
    assert digits["plan"][1]["type"] == "uncovered", digits["plan"]   # nothing to spell
    lone = match("I sit", spell_unknown=True)
    assert lone["plan"][0]["type"] == "uncovered", lone["plan"]       # not the letter I

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
    _synonyms = None
    _remote = None
    real = _load_manifest()
    assert len(real) > 1000, f"manifest has only {len(real)} phrases - run tools/build_manifest.py"

    demo = match("Hello, thank you. My name is Mothishwaran.")
    assert [(p["token"], p["type"]) for p in demo["plan"]] == [
        ("hello", "sign"), ("thank you", "sign"),
        ("my name is", "sign"), ("Mothishwaran", "spell"),
    ], demo["plan"]
    assert demo["counts"] == {"total": 7, "sign": 6, "similar": 0, "related": 0, "spell": 1, "omitted": 0, "uncovered": 0}, demo["counts"]

    # Word forms count as the same sign; synonyms are typed "similar" and kept
    # out of exact coverage.
    forms = match("My children like books")
    kinds = {p["token"]: (p["type"], p.get("means")) for p in forms["plan"]}
    assert kinds["children"] == ("sign", "child"), forms["plan"]
    assert kinds["books"] == ("sign", "book"), forms["plan"]
    doc = match("my physician")
    assert (doc["plan"][1]["type"], doc["plan"][1]["means"]) == ("similar", "doctor"), doc["plan"]
    assert doc["counts"]["similar"] == 1 and doc["coverage"] == 0.5, doc
    assert doc["content_coverage_with_similar"] == 1.0, doc
    # A synonym proposal a reviewer rejected must never be used.
    assert match("miss")["plan"][0]["type"] != "similar", match("miss")["plan"]

    # Numbers: spoken reading when every word has a sign, else digit by digit.
    assert number_words(25) == ["twenty", "five"]
    assert number_words(2026) == ["two", "thousand", "twenty", "six"]
    assert number_words(150) == ["one", "hundred", "fifty"]
    n25 = match("I am 25 years old")["plan"][2]
    assert (n25["type"], n25["means"], len(n25["clips"])) == ("sign", "twenty five", 2), n25
    n45 = match("He is 45")["plan"][2]
    assert n45["means"] == "four five", n45               # no sign for "forty"
    t730 = match("Meet me at 7:30")["plan"][-1]
    assert t730["means"] == "seven thirty", t730
    hy = match("I have twenty-five books")["plan"][2]
    assert hy["means"] == "twenty five", hy
    big = match("It costs 1,000 rupees")["plan"]
    assert any(p["token"] in ("1,000", "1000") and p["type"] == "sign" for p in big), big
    assert number_signs("hello", _load_manifest()) is None

    # Drive catalogue: a sign not on disk matches with a "drive" key for the
    # server to fetch; with use_drive=False it is uncovered. (No network here.)
    remote = _load_remote()
    assert len(remote) > 1000, f"drive catalogue has {len(remote)} phrases"
    from src import drive_fetch as _df
    probe = next(p for p, r in sorted(remote.items())
                 if len(p.split()) == 1 and not _df.playable_path(r["rel"]))
    on = match(f"my {probe}")["plan"][1]
    assert on["type"] == "sign" and on["drive"]["phrase"] == probe, on
    off = match(f"my {probe}", use_drive=False)["plan"][1]
    assert off["type"] in ("uncovered", "related", "similar"), off
    # score() is what the server uses to recount after a failed fetch.
    downgraded = match(f"my {probe}")
    downgraded["plan"][1].update(type="uncovered", clips=[])
    assert score(downgraded["plan"])["counts"]["uncovered"] == 1

    boy = match("How are you my boy?")
    assert [p["type"] for p in boy["plan"] if p["token"].lower() == "are"] == ["omitted"], boy["plan"]

    curly = match("I don’t know.")
    assert [(p["token"], p["type"]) for p in curly["plan"]] == [("i don't know", "sign")], curly["plan"]

    every_clip = [c for p in demo["plan"] for c in p["clips"]]
    missing = [c for c in every_clip if not os.path.exists(os.path.join(_REPO_ROOT, c))]
    assert not missing, f"demo clips missing on disk: {missing}"

    print(f"\nOK  (part 2: real manifest, {len(real)} phrases, longest {max_ngram()} words)")
    for p in demo["plan"]:
        print(f"{p['token']:<15}{p['type']:<12}{p['clips'][:1]}{' ...' if len(p['clips']) > 1 else ''}")
    print(f"coverage={demo['coverage']:.3f}  counts={demo['counts']}")
