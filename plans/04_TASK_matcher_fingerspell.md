# 04 · Block 2 — Matcher + Fingerspell

**Budget: ~1.5 hours.** Contracts: [02_SPEC.md](02_SPEC.md) §2, §4, §5.
**No audio in this block.** Everything is tested against hardcoded strings. This is the only part of the system that is pure logic, so it is the only part you can make genuinely correct — do that.

---

## `src/fingerspell.py` — do this first, it is 15 minutes

Per spec §5.

```python
ALPHABET_DIR = "data/alphabet"

def spell(word: str) -> list[str]:
    # lowercase, keep a-z only, -> ["data/alphabet/m.mp4", ...]
```

Self-test in `__main__`:
- `spell("Mothishwaran")` → 12 paths, first is `.../m.mp4`, last is `.../n.mp4`
- `spell("O'Brien-42")` → 6 paths (`o b r i e n`) — apostrophes, hyphens and digits all dropped
- `spell("")` → `[]`

---

## `src/matcher.py`

Per spec §4. Build it in this order, testing at each step:

**1 · Manifest loader.** Read `data/manifest.csv`, build `{phrase: id}` and `{phrase: local_path}`. Assert `int(ngram_len) == len(phrase.split())` on every row and raise a clear error naming the offending row if not. Load once at module level.

**2 · Tokeniser.** Produce three parallel arrays — `orig[]` (casing kept), `norm[]` (lowercased, punctuation stripped), `sentence_initial[]` (bool). Rules verbatim from spec §4. Empty-after-normalisation tokens are dropped from all three together.

Test it standalone before going further:
```
"Hello, thank you. My name is Mothishwaran."
orig             = [Hello, thank, you, My, name, is, Mothishwaran]
norm             = [hello, thank, you, my, name, is, mothishwaran]
sentence_initial = [True,  False, False, True, False, False, False]
```
`My` is `sentence_initial=True` because `you.` ended with a period. **If your tokeniser gets that wrong, the demo fingerspells M-Y and looks broken.** Verify this array before writing the matching loop.

**3 · Greedy longest-n-gram.** Left to right over `norm[]`; at each position try n=3, then 2, then 1; first hit wins and advances the cursor by n. Unmatched tokens advance by 1 and get classified per §4.

**4 · Assemble** `plan`, `counts`, `coverage`, `match_ms` (`time.perf_counter`, will be sub-millisecond — report it honestly as `0` or `1`, do not inflate it).

---

## Self-test block — this is the deliverable, not an extra

`if __name__ == "__main__":` with assertions. Minimum set:

| Input | Must produce |
|---|---|
| `"Hello, thank you. My name is Mothishwaran."` | the golden case, spec §4 — 7 total, 4 sign, 1 spell, 2 uncovered, coverage `0.571` |
| `"thank you"` | 1 plan entry, type `sign`, `thank_you` — **not** two entries |
| `"You thank me"` | zero sign matches — proves the bigram isn't matching loose word order |
| `""` | empty plan, coverage `0.0`, no exception |
| `"!!! ... ???"` | empty plan, no exception |
| `"Mothishwaran is here"` | `Mothishwaran` at index 0 is **sentence-initial → `uncovered`, not `spell`** |
| `"The cat sat"` | all `uncovered`, coverage `0.0`, **nothing fingerspelled** |

Last two rows are the ones that catch real bugs. The `"The cat sat"` case is what proves you did not take the lazy "fingerspell everything unknown" path — and that is viva question #15.

Print `OK` plus a formatted plan table for the golden case.

---

## Proof of done

```powershell
.\.venv\Scripts\python.exe -m src.fingerspell
.\.venv\Scripts\python.exe -m src.matcher
```

Both print `OK` with no assertion errors.

Acceptance:
- [ ] `thank you` matched as one bigram, id `thank_you`
- [ ] `Mothishwaran` → `spell`, 12 clip paths
- [ ] `my` and `is` → `uncovered`, `clips == []`
- [ ] coverage prints `0.571` (or `0.5714…`)
- [ ] every edge case above passes
- [ ] **Screenshot the passing output.** Deck asset — it is your "unit-tested components" evidence, and it took zero extra effort.

---

## Traps

- **Do not add stopwords for `my` and `is`.** They are *supposed* to be uncovered. That is the metric doing its job and it is what makes 57.1% an honest number instead of a decorative one.
- Do not lowercase before you have captured `sentence_initial` — you need the punctuation to compute it.
- Do not strip punctuation globally with one regex pass over the whole string. You will destroy sentence boundaries and `My` becomes `spell`.
- Do not import `asr` or `fastapi` here. This module must stay runnable and testable on its own.
