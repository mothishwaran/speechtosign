"""Word error rate with Whisper's English text normalizer.

Both reference and hypothesis go through the normalizer from the Whisper
paper (lowercase, punctuation removed, "ten" == "10", British/American
spellings unified), so WER measures recognition errors rather than
formatting differences. Same normalizer for baseline and fine-tuned models.
"""
import jiwer

_normalizer = None


def normalize(text: str) -> str:
    global _normalizer
    if _normalizer is None:
        from transformers import WhisperTokenizer
        from transformers.models.whisper.english_normalizer import EnglishTextNormalizer
        tok = WhisperTokenizer.from_pretrained("openai/whisper-base.en")
        _normalizer = EnglishTextNormalizer(tok.english_spelling_normalizer)
    return _normalizer(text)


def wer_corpus(refs: list[str], hyps: list[str]) -> float:
    """Corpus-level WER: total word errors / total reference words."""
    pairs = [(normalize(r), normalize(h)) for r, h in zip(refs, hyps)]
    pairs = [(r, h) for r, h in pairs if r.strip()]   # jiwer rejects empty references
    if not pairs:
        return 0.0
    return jiwer.wer([r for r, _ in pairs], [h for _, h in pairs])
