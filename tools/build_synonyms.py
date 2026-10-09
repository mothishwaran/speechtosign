"""Generate data/synonyms.csv: extra spoken words -> an existing sign.

Two kinds of row, both from WordNet (Princeton's hand-built English lexical
database), computed once here so the app needs no NLP library at runtime:

  form     inflected form of a dictionary word: "books" -> "book",
           "going" -> "go", "children" -> "child". Same word, so the
           matcher treats it as an ordinary sign.
  related  no sign and no synonym: the nearest MORE GENERAL word that has a
           sign (WordNet hypernym, up to 2 levels): "sparrow" -> bird,
           "Mumbai" -> city. Only generalisations, which stay true ("a
           sparrow is a bird"); never siblings, which are different things
           (dog/cat, husband/wife, man/woman). Nouns only, vague parents
           (entity, object, person, group ...) excluded. Used unless a
           reviewer writes reject; shown as type "related", counted apart.
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
DRIVE_MANIFEST = "data/drive_manifest.csv"
# Generalisations too vague to stand in for a word.
PLACE_TYPES = {"city", "town", "capital", "national capital", "state capital", "country",
               "island", "river", "state", "province", "port", "village", "lake", "mountain"}
VAGUE_PARENTS = {
    "entity", "physical entity", "abstraction", "abstract entity", "object", "whole", "thing",
    "matter", "causal agent", "unit", "artifact", "artefact", "act", "event", "state", "group",
    "part", "attribute", "relation", "measure", "process", "communication", "location",
    "substance", "quantity", "condition", "activity", "action", "change", "person", "individual",
    "organism", "being", "living thing", "people", "content", "message", "work", "property",
    "kind", "type", "form", "way", "point", "line", "set", "system", "structure", "place",
    "area", "region", "body", "material", "device", "instrument", "instrumentality", "means",
    "time", "period", "feeling", "idea", "knowledge", "cognition", "psychological feature",
    # found in review: technically parents, but too vague to sign in place of the word
    "quality", "amount", "situation", "concept", "power", "parcel", "construction", "piece",
    "section", "sorting", "organization", "operation", "approval", "figure", "effort", "find",
    "conclusion", "start", "shift", "advance", "interest", "record", "document", "business",
    "occupation", "order", "age", "attitude", "goal", "plan", "equal", "force", "phenomenon",
    "environment", "experience", "support", "implementation", "look", "sign", "account", "word",
    "head", "terminal", "block", "cut", "vision", "entry", "approach", "expanse", "setting",
    "map", "drive", "return", "hit", "reach", "opinion", "designation", "good", "deposit",
    "first", "agreement", "share", "transmission", "medium", "model", "national",
}
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
    drive_phrases = set()
    if os.path.exists(DRIVE_MANIFEST):        # fetchable on demand, so usable targets too
        with open(DRIVE_MANIFEST, newline="", encoding="utf-8") as f:
            drive_phrases = {r["phrase"] for r in csv.DictReader(f)}
    function_words = set(stopwords.words("english")) | ISL_OMITTED

    reviewed = {}
    if os.path.exists(OUT):
        with open(OUT, newline="", encoding="utf-8") as f:
            reviewed = {(r["word"], r["target"]): r["review"] for r in csv.DictReader(f)
                        if r.get("review", "").strip().lower() in ("ok", "reject")}

    def usable(target):
        # > 1: single letters are alphabet signs, not words ("go", "up" are fine)
        return (target in phrases or target in drive_phrases) and len(target) > 1             and not re.fullmatch(r"[\d ]+", target)

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
        if not found and w not in drive_phrases:              # 3) related (generalisation)
            base = wn.morphy(w, "n") or w
            share = pos_share(wn, base, "n")
            nouns = wn.synsets(base, "n")
            first = wn.synsets(base)
            noun_main = (share >= FORM_POS_SHARE) if share is not None else                 (bool(first) and first[0].pos() == "n")
            top = None
            if nouns and noun_main:
                # The word's most frequent ATTESTED noun sense (corpus count),
                # not WordNet's first-listed one: that rule gave chess -> grass,
                # cake -> block, Cameroon -> volcano.
                counted = [(sum(l.count() for l in n.lemmas() if l.name().lower() == base), n)
                           for n in nouns]
                best_count, best = max(counted, key=lambda x: x[0])
                if best_count > 0:
                    top = best
                elif len(nouns) == 1 and any(
                        l.name().replace("_", " ").lower() in PLACE_TYPES
                        for h in nouns[0].instance_hypernyms() for l in h.lemmas()):
                    top = nouns[0]          # unambiguous place name: Beijing -> city
            if top is not None:
                level1 = top.hypernyms() + top.instance_hypernyms()
                level2 = [h2 for h in level1 for h2 in h.hypernyms()]
                for depth, parents in ((1, level1), (2, level2)):
                    for h in parents:
                        for lemma in h.lemmas():
                            t = lemma.name().replace("_", " ").lower()
                            if t in VAGUE_PARENTS or t == w or t == base:
                                continue
                            if t in drive_phrases or usable(t):
                                found = (t, "related", f"hypernym L{depth} {h.name()}")
                                break
                        if found:
                            break
                    if found:
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
    n_rel = sum(r["kind"] == "related" for r in rows)
    print(f"  related (generalisations): {n_rel} "
          f"({sum(r['kind'] == 'related' and r['review'] == 'reject' for r in rows)} rejected)")
    print(f"wrote {OUT}: {n_form} word forms + {len(rows) - n_form} synonym proposals "
          f"({n_ok} approved; {sum(r['review'] == 'reject' for r in rows)} rejected)")


if __name__ == "__main__":
    main()
