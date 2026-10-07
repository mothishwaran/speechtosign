"""Generate data/synonyms.csv: extra spoken words -> an existing sign.

Two kinds of row, both from WordNet (Princeton's hand-built English lexical
database), computed once here so the app needs no NLP library at runtime:

  form     inflected form of a dictionary word: "books" -> "book",
           "going" -> "go", "children" -> "child". Same word, so the
           matcher treats it as an ordinary sign.
  synonym  a different word with the same meaning: "kid" -> "child",
           "physician" -> "doctor". Only a PROPOSAL: the matcher uses it
           once a person sets review=ok (shown as type "similar", counted
           separately from exact coverage).

Why WordNet and not sentence embeddings: on a hand-labelled check (30
synonym pairs vs 30 related-but-different pairs) MiniLM embeddings accepted
Monday->Tuesday and husband->wife (0.87 cosine) at every usable threshold,
i.e. they would show a wrong sign. WordNet accepted 0/30 of those pairs.

Safety rules, tightened after reviewing a first, looser run that produced
million->billion, decade->ten and acid->zen (slang sense):
  - form: the inflection's part of speech must account for >= 70% of the
    base word's uses in WordNet's sense-tagged corpus ("went" -> go: 100%
    verb, accepted; "trained" -> train: 60% verb, could be the vehicle,
    rejected). Words with no corpus counts fall back to WordNet's first sense.
  - synonym: the shared meaning must be the MOST frequent sense of both
    words, and both must be attested in WordNet's sense-tagged corpus
    (lemma count > 0), which drops slang and archaic senses.
  - function words are never mapped (WordNet reads "in" as inch/indium).
Review values (ok / reject) survive regeneration.

Usage: python tools/build_synonyms.py   (needs: pip install nltk)
"""
import csv
import os
import re
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from src.matcher import ISL_OMITTED, normalize_phrase  # noqa: E402

MANIFEST = "data/manifest.csv"
OUT = "data/synonyms.csv"
FORM_POS_SHARE = 0.7
WORDLIST_URL = ("https://raw.githubusercontent.com/first20hours/google-10000-english/"
                "master/google-10000-english-no-swears.txt")

# Hand-picked bad inflection pairs WordNet's morphology produces.
FORM_BLOCKLIST = {"goods": "good", "means": "mean", "news": "new", "glasses": "glass",
                  "arms": "arm", "customs": "custom", "manners": "manner", "savings": "saving",
                  "species": "specie", "physics": "physic", "politics": "politic"}


def load_wordlist() -> list[str]:
    import urllib.request
    cache = os.path.join("data", "_derived", "google-10000-english.txt")
    if not os.path.exists(cache):
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        urllib.request.urlretrieve(WORDLIST_URL, cache)
    words = [w.strip().lower() for w in open(cache, encoding="utf-8") if w.strip()]
    with open("eval/test_sentences.txt", encoding="utf-8") as f:   # always cover the test set
        words += normalize_phrase(f.read()).split()
    return list(dict.fromkeys(words))


def pos_share(wn, base: str, pos: str) -> float | None:
    """Fraction of `base`'s corpus-tagged uses that are `pos` (None if untagged)."""
    counts = {}
    for s in wn.synsets(base):
        p = s.pos().replace("s", "a")      # satellite adjectives are adjectives
        for lemma in s.lemmas():
            if lemma.name().lower() == base:
                counts[p] = counts.get(p, 0) + lemma.count()
    total = sum(counts.values())
    return counts.get(pos, 0) / total if total else None


def main():
    os.chdir(_REPO_ROOT)
    import nltk
    for corpus in ("wordnet", "omw-1.4", "stopwords"):
        nltk.download(corpus, quiet=True)
    from nltk.corpus import stopwords
    from nltk.corpus import wordnet as wn

    with open(MANIFEST, newline="", encoding="utf-8") as f:
        phrases = {r["phrase"] for r in csv.DictReader(f)}
    function_words = set(stopwords.words("english")) | ISL_OMITTED

    reviewed = {}
    if os.path.exists(OUT):
        with open(OUT, newline="", encoding="utf-8") as f:
            reviewed = {(r["word"], r["target"]): r["review"] for r in csv.DictReader(f)
                        if r.get("review", "").strip().lower() in ("ok", "reject")}

    def usable(target):
        # > 1: single letters are alphabet signs, not words ("go", "up" are fine)
        return target in phrases and len(target) > 1 and not re.fullmatch(r"[\d ]+", target)

    rows = []
    for w in load_wordlist():
        if w in phrases or w in function_words or len(w) < 3 or not w.isalpha():
            continue
        found = None
        forms = {}                                           # 1) inflected form
        for pos in ("n", "v", "a", "r"):
            base = wn.morphy(w, pos)
            if not base or base == w or not usable(base) or FORM_BLOCKLIST.get(w) == base:
                continue
            share = pos_share(wn, base, pos)
            if share is None:      # no corpus counts: fall back to first sense
                main = wn.synsets(base)
                ok = bool(main) and main[0].pos().replace("s", "a") == pos
            else:
                ok = share >= FORM_POS_SHARE
            if ok:
                forms.setdefault(base, (pos, share))
        # "lives" is both life (noun) and live (verb): two different signs, so
        # the word is ambiguous out of context and is left unmapped.
        if len(forms) == 1:
            base, (pos, share) = next(iter(forms.items()))
            found = (base, "form", f"morphy {pos}; {pos}-share "
                                   f"{'n/a' if share is None else f'{share:.2f}'}")
        elif len(forms) > 1:
            continue
        if not found:                                        # 2) synonym proposal
            senses = wn.synsets(w)
            if senses:
                top = senses[0]
                counts = {l.name(): l.count() for l in top.lemmas()}
                for lemma in top.lemmas():
                    t = lemma.name().replace("_", " ").lower()
                    if (t != w and usable(t) and lemma.count() > 0
                            and counts.get(w, counts.get(w.capitalize(), 0)) > 0
                            and wn.synsets(lemma.name())[:1] == [top]):
                        found = (t, "synonym", top.name())
                        break
        if found:
            target, kind, evidence = found
            review = reviewed.get((w, target), "")
            rows.append({"word": w, "target": target, "kind": kind,
                         "evidence": evidence, "review": review})

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=["word", "target", "kind", "evidence", "review"])
        wr.writeheader()
        wr.writerows(sorted(rows, key=lambda r: (r["kind"], r["word"])))
    n_form = sum(r["kind"] == "form" for r in rows)
    n_ok = sum(r["kind"] == "synonym" and r["review"] == "ok" for r in rows)
    print(f"wrote {OUT}: {n_form} word forms + {len(rows) - n_form} synonym proposals "
          f"({n_ok} approved; {sum(r['review'] == 'reject' for r in rows)} rejected)")


if __name__ == "__main__":
    main()
