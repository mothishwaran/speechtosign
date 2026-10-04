"""Dev tool: locate letter segment boundaries in the ISL alphabet video.

The video renders the current letter as a caption in the top-left corner. That
region is pixel-stable while a letter is held and only changes during the
crossfade between letters, so thresholding its frame-to-frame difference gives
precise segment boundaries without guessing.
"""
import sys

import av
import numpy as np

VIDEO = "data/alphabet/videoplayback.mp4"
# Caption glyph box only — must exclude the signer's hands, which drift high
# enough on some letters to break stability if the crop is too generous.
Y0, Y1, X0, X1 = (int(a) for a in (sys.argv[1:5] or (40, 105, 25, 95)))
STABLE_THRESH = float(sys.argv[5]) if len(sys.argv) > 5 else 1.2
MIN_SEG_S = 0.6


def main():
    container = av.open(VIDEO)
    stream = container.streams.video[0]
    stream.thread_type = "AUTO"

    times, diffs = [], []
    prev = None
    for frame in container.decode(stream):
        ts = float(frame.pts * stream.time_base)
        arr = frame.to_ndarray(format="gray")[Y0:Y1, X0:X1].astype(np.float32)
        if prev is not None:
            diffs.append(float(np.abs(arr - prev).mean()))
            times.append(ts)
        prev = arr
    container.close()

    diffs = np.array(diffs)
    times = np.array(times)
    stable = diffs < STABLE_THRESH

    # Contiguous stable runs = periods where one letter caption is displayed.
    segments = []
    start = None
    for i, s in enumerate(stable):
        if s and start is None:
            start = i
        elif not s and start is not None:
            if times[i - 1] - times[start] >= MIN_SEG_S:
                segments.append((times[start], times[i - 1]))
            start = None
    if start is not None and times[-1] - times[start] >= MIN_SEG_S:
        segments.append((times[start], times[-1]))

    print(f"found {len(segments)} stable segments\n")
    letters = "abcdefghijklmnopqrstuvwxyz"
    for i, (s, e) in enumerate(segments):
        tag = letters[i] if i < len(letters) else "?"
        print(f"{tag}  {s:7.2f} -> {e:7.2f}   ({e - s:.2f}s)")


if __name__ == "__main__":
    main()
