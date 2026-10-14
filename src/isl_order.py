"""ISL word order and question marking for a matched sign plan.

The matcher returns signs in English order. Indian Sign Language orders some
things differently (Zeshan, "Indo-Pakistani Sign Language Grammar", 2003);
three well-attested, low-risk rules are applied within each sentence:

  1. Time first   - time expressions open the sentence:
                    "I go to school tomorrow" -> TOMORROW I GO SCHOOL
  2. Negation last - no / never / nothing / don't move to the end:
                    "I never eat meat" -> I EAT MEAT NEVER
  3. Question word last - in a wh-question the question sign closes it:
                    "Where is the hospital?" -> HOSPITAL WHERE
Full SOV verb placement is NOT attempted: it needs reliable verb/object
detection, and a wrong reorder is worse than English order.

Question detection (detect_question) uses text cues - wh-word first,
auxiliary first ("Can you ...", "Do I ..."), or a final "?" - because
tools/question_study.py measured them at 85 % recall / 97 % precision on
unseen Svarah speakers even with the "?" removed, while the pitch rise was
66 % balanced accuracy alone and only added false alarms when combined. The
pitch measurement (src/prosody.py) is still reported as evidence. Yes/no
questions are marked in ISL by raised eyebrows (non-manual), which isolated
dictionary clips cannot show; the UI states this instead of faking it.
"""

WH = {"what", "what's", "where", "where's", "when", "who", "who's", "why", "how", "how's",
      "which", "whose", "whom", "how much", "how many"}
AUX = {"can", "could", "will", "would", "shall", "should", "do", "does", "did", "is", "are",
       "am", "was", "were", "have", "has", "had", "may", "might", "must", "isn't", "aren't",
       "don't", "doesn't", "didn't", "can't", "won't"}
TIME = {"today", "tomorrow", "yesterday", "tonight", "now", "morning", "evening", "night",
        "afternoon", "soon", "later", "next week", "last week", "every day", "this morning",
        "next month", "last month", "next year", "last year", "always", "sometimes"}
NEG = {"no", "not", "never", "nothing", "don't", "doesn't", "didn't", "can't", "cannot",
       "won't", "isn't", "aren't"}
SIGNED = {"sign", "similar", "related", "spell"}
MOVABLE = {"sign", "similar", "related"}   # fingerspelled words are never moved


def _key(entry: dict) -> str:
    return (entry.get("means") or entry["token"]).lower()


def _first_word(entries: list) -> str:
    for e in entries:
        return e["token"].lower().split()[0]
    return ""


def _sentence_question(entries: list) -> tuple[str | None, str]:
    first = _first_word(entries)
    first_phrase = entries[0]["token"].lower() if entries else ""
    nxt = entries[1]["token"].lower() if len(entries) > 1 else ""
    asked = bool(entries) and entries[0].get("sent_q")
    # wh-word counts when the sentence ends in "?" or a verb follows it
    # ("Where is ..."), not for a time clause ("When I was young ...")
    if (first in WH or first_phrase in WH) and (asked or nxt in AUX or first_phrase in WH and " " in first_phrase):
        return "wh", f'starts with "{entries[0]["token"]}"'
    if first in AUX:
        return "yesno", f'starts with "{entries[0]["token"]}" (verb first)'
    if asked:
        return "yesno", 'ends with "?"'
    return None, ""


def detect_question(transcript: str, plan: list) -> dict:
    """Is any sentence a question? Returns the first one found: wh / yesno / None."""
    for s in sorted({e.get("sent", 0) for e in plan}):
        kind, why = _sentence_question([e for e in plan if e.get("sent", 0) == s])
        if kind:
            n = len({e.get("sent", 0) for e in plan})
            where = f"sentence {s + 1}: " if n > 1 else ""
            return {"type": kind, "sentence": s, "evidence": where + why}
    return {"type": None, "sentence": None, "evidence": "no question word, verb-first order or ?"}


def reorder(plan: list) -> tuple[list, list]:
    """Return (play order as plan indices, rules applied). English order if no rule fires."""
    order, rules = [], []
    sentences = sorted({e.get("sent", 0) for e in plan})
    for s in sentences:
        idx = [i for i, e in enumerate(plan) if e.get("sent", 0) == s]
        front = [i for i in idx if plan[i]["type"] in MOVABLE and _key(plan[i]) in TIME]
        neg = [i for i in idx if plan[i]["type"] in MOVABLE and _key(plan[i]) in NEG]
        wh = []
        first_signed = next((i for i in idx if plan[i]["type"] in MOVABLE), None)
        # A sentence-initial question word is a question only if the sentence ends
        # in "?" or the next word is a verb ("Where is ...", "Who are ...");
        # "When I was young ..." opens a time clause and stays put. A one-sign
        # sentence ("What is your name" is a single dictionary sign) stays too.
        if first_signed is not None and _key(plan[first_signed]) in WH and \
                any(plan[i]["type"] in SIGNED for i in idx if i != first_signed):
            pos_first = idx.index(first_signed)
            nxt = plan[idx[pos_first + 1]]["token"].lower() if pos_first + 1 < len(idx) else ""
            if plan[first_signed].get("sent_q") or nxt in AUX:
                wh = [first_signed]
        moved = set(front) | set(neg) | set(wh)
        middle = [i for i in idx if i not in moved]
        new = front + middle + neg + wh
        if front and idx.index(front[0]) != 0:
            rules.append("time first: " + ", ".join(plan[i]["token"] for i in front))
        if neg and new != idx:
            rules.append("negation last: " + ", ".join(plan[i]["token"] for i in neg))
        if wh:
            rules.append(f'question word last: {plan[wh[0]]["token"]}')
        order += new
    return order, rules


def gloss(plan: list, order: list) -> str:
    """Capitalised sign sequence in play order (the conventional way to write signs)."""
    def word(e):
        if e["type"] == "spell":   # fingerspelled: show the letters, H-O-W
            return "-".join(c.upper() for c in e["token"] if c.isalpha())
        return _key(e).upper()
    return " ".join(word(plan[i]) for i in order if plan[i]["type"] in SIGNED and plan[i]["clips"])


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src import matcher

    def run(text):
        m = matcher.match(text, use_drive=False)
        order, rules = reorder(m["plan"])
        return gloss(m["plan"], order), rules, detect_question(text, m["plan"])

    g, r, q = run("Where is the hospital?")
    assert g == "HOSPITAL WHERE" and q["type"] == "wh", (g, q)
    g, r, q = run("I go to school tomorrow.")
    assert g.startswith("TOMORROW") and q["type"] is None, (g, r)
    g, r, q = run("I never eat rice.")
    assert g.endswith("NEVER"), g
    g, r, q = run("What is your name?")
    assert g == "WHAT IS YOUR NAME" and r == [], (g, r)        # one dictionary sign: untouched
    g, r, q = run("Can you help me")                           # no "?" (fine-tuned ASR drops it)
    assert q["type"] == "yesno", q
    g, r, q = run("When I was young I lived in a village.")
    assert not any("question" in x for x in r), r              # subordinate "when" stays
    g, r, q = run("Hello. Where is the market? Thank you.")
    assert g == "HELLO MARKET WHERE THANK YOU", g              # reorder stays inside sentence 2
    g, r, q = run("Where is the hospital? I go to school tomorrow.")
    assert q["type"] == "wh" and q["sentence"] == 0, q        # question in sentence 1 is found
    g, r, q = run("When I was young I lived in a village.")
    assert q["type"] is None, q
    plain = matcher.match("My mother is a teacher.", use_drive=False)["plan"]
    assert reorder(plain) == (list(range(len(plain))), [])     # nothing to move -> English order
    print("OK")
    for t in ["Where is the hospital?", "I go to school tomorrow.", "I never eat rice.",
              "Can you help me", "Today my friend is coming. Who are you?"]:
        g, r, q = run(t)
        print(f"{t:42} -> {g:32} {r}  question={q['type']}")
