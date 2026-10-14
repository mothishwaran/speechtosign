"""Export fine-tuned Whisper weights to the CTranslate2 format faster-whisper loads.

int8 weights keep the model under GitHub's 100 MB file limit (~75 MB for
base.en), so the exported folder is committed and a teammate gets the trained
model with a plain `git pull`. faster-whisper still computes in float16 on a
GPU / int8 on CPU (src/asr.py picks).

Usage: python -m tools.train.export [--src checkpoints/base_en_svarah/best]
                                    [--out models/whisper-base-en-svarah]
Then:  set SPEECH_ISL_MODEL=models/whisper-base-en-svarah  (or it is picked
       up automatically if present - see src/asr.py)
"""
import argparse
import os
import shutil
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="checkpoints/base_en_svarah/best")
    ap.add_argument("--out", default="models/whisper-base-en-svarah")
    ap.add_argument("--quantization", default="int8")
    args = ap.parse_args()
    os.chdir(_REPO_ROOT)

    if not os.path.isdir(args.src):
        sys.exit(f"{args.src} not found - train first (python -m tools.train.train)")

    from ctranslate2.converters import TransformersConverter

    if not os.path.exists(os.path.join(args.src, "preprocessor_config.json")):
        from transformers import WhisperFeatureExtractor
        WhisperFeatureExtractor.from_pretrained(args.src).save_pretrained(args.src)

    tmp = args.out + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    TransformersConverter(
        args.src, copy_files=["tokenizer.json", "preprocessor_config.json"],
    ).convert(tmp, quantization=args.quantization, force=True)
    card = os.path.join(args.out, "README.md")
    if os.path.exists(card):          # keep the hand-written model card
        shutil.copy2(card, os.path.join(tmp, "README.md"))
    shutil.rmtree(args.out, ignore_errors=True)
    os.replace(tmp, args.out)

    for fn in sorted(os.listdir(args.out)):
        size = os.path.getsize(os.path.join(args.out, fn)) / 1e6
        print(f"  {fn:28} {size:8.1f} MB{'   <-- over GitHub 100 MB limit!' if size > 100 else ''}")
    print(f"exported -> {args.out}")


if __name__ == "__main__":
    main()
