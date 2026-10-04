"""Name fingerspelling fallback. See plans/02_SPEC.md section 5."""

ALPHABET_DIR = "data/alphabet"


def spell(word: str) -> list[str]:
    letters = [c for c in word.lower() if "a" <= c <= "z"]
    return [f"{ALPHABET_DIR}/{letter}.mp4" for letter in letters]


if __name__ == "__main__":
    result = spell("Mothishwaran")
    assert len(result) == 12, result
    assert result[0] == "data/alphabet/m.mp4", result
    assert result[-1] == "data/alphabet/n.mp4", result

    result = spell("O'Brien-42")
    assert result == [
        "data/alphabet/o.mp4",
        "data/alphabet/b.mp4",
        "data/alphabet/r.mp4",
        "data/alphabet/i.mp4",
        "data/alphabet/e.mp4",
        "data/alphabet/n.mp4",
    ], result

    assert spell("") == []

    print("OK")
    print(spell("Mothishwaran"))
