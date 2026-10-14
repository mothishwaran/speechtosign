"""Split the ISL alphabet video into one clip per letter.

Boundaries were read off tools/cap_a.png and tools/cap_b.png — filmstrips of the
video's on-screen letter caption sampled every 0.5s. Each (first, last) pair
below is the range over which that letter's caption was displayed, so the
letter is unambiguously on screen across the whole span.

Clips are cut as a centred window of CLIP_S seconds so the held handshape is
kept and the crossfades either side are excluded. Encoded H.264, no audio.

Usage: python tools/split_alphabet.py [letters] [clip_seconds]
       python tools/split_alphabet.py mothiswarn 1.5
"""
import os
import sys
from fractions import Fraction

import av

VIDEO = "data/alphabet/videoplayback.mp4"
OUT_DIR = "data/alphabet"
CROSSFADE_PAD = 0.15   # stay this far inside the caption span

# letter -> (first caption sample, last caption sample) in seconds
SPANS = {
    "a": (0.0, 3.0),    "b": (3.5, 6.0),    "c": (6.5, 9.5),
    "d": (10.0, 13.0),  "e": (13.5, 16.0),  "f": (16.5, 19.0),
    "g": (19.5, 22.0),  "h": (22.5, 25.0),  "i": (25.5, 27.5),
    "j": (28.0, 31.0),  "k": (31.5, 33.5),  "l": (34.0, 36.5),
    "m": (37.0, 39.5),  "n": (40.0, 42.5),  "o": (43.0, 46.0),
    "p": (46.5, 48.5),  "q": (49.0, 51.5),  "r": (52.0, 55.0),
    "s": (55.5, 58.0),  "t": (58.5, 61.0),  "u": (61.5, 64.0),
    "v": (64.5, 67.0),  "w": (67.5, 70.0),  "x": (70.5, 73.5),
    "y": (74.0, 76.5),  "z": (77.0, 80.0),
}


def window(letter: str, clip_s: float) -> tuple[float, float]:
    first, last = SPANS[letter]
    lo, hi = first + CROSSFADE_PAD, last + CROSSFADE_PAD
    span = hi - lo
    if span <= clip_s:
        return lo, hi
    mid = (lo + hi) / 2.0
    return mid - clip_s / 2.0, mid + clip_s / 2.0


def extract(letter: str, start_s: float, end_s: float) -> float:
    src = av.open(VIDEO)
    in_stream = src.streams.video[0]
    in_stream.thread_type = "AUTO"

    out_path = os.path.join(OUT_DIR, f"{letter}.mp4")
    dst = av.open(out_path, "w")
    out_stream = dst.add_stream("libx264", rate=int(round(float(in_stream.average_rate))))
    out_stream.width = in_stream.codec_context.width
    out_stream.height = in_stream.codec_context.height
    out_stream.pix_fmt = "yuv420p"
    out_stream.options = {"crf": "20", "preset": "veryfast"}

    # Seek slightly early, then filter precisely by PTS.
    src.seek(int(max(0.0, start_s - 1.0) / in_stream.time_base), stream=in_stream)

    written = 0
    rate = int(round(float(in_stream.average_rate)))
    for frame in src.decode(in_stream):
        ts = float(frame.pts * in_stream.time_base)
        if ts < start_s:
            continue
        if ts > end_s:
            break
        # Explicit, evenly spaced timestamps. pts=None made the encoder stamp
        # 45 frames into 0.03 s, so browsers flashed each letter instantly.
        frame.pts, frame.time_base = written, Fraction(1, rate)
        for packet in out_stream.encode(frame):
            dst.mux(packet)
        written += 1

    for packet in out_stream.encode():
        dst.mux(packet)
    dst.close()
    src.close()

    return written / float(in_stream.average_rate)


def main():
    letters = (sys.argv[1] if len(sys.argv) > 1 else "".join(sorted(SPANS))).lower()
    clip_s = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5

    os.makedirs(OUT_DIR, exist_ok=True)
    for letter in letters:
        if letter not in SPANS:
            print(f"  {letter}: no span defined, skipped")
            continue
        start_s, end_s = window(letter, clip_s)
        dur = extract(letter, start_s, end_s)
        print(f"  {letter}.mp4  cut {start_s:6.2f}->{end_s:6.2f}  duration {dur:.2f}s")

    print(f"\ndone: {len(letters)} clip(s) in {OUT_DIR}/")


if __name__ == "__main__":
    main()
