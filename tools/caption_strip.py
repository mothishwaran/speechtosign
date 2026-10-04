"""Dev tool: filmstrip of just the caption corner, so letter changes are readable.

Usage: python tools/caption_strip.py <start_s> <end_s> <out.png>
"""
import sys

import av
from PIL import Image, ImageDraw

VIDEO = "data/alphabet/videoplayback.mp4"
Y0, Y1, X0, X1 = 95, 190, 50, 150      # caption glyph box
TILE, BAR, COLS = 86, 15, 16
STEP = 0.5


def main():
    start_s, end_s, out_path = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]

    targets = []
    t = start_s
    while t < end_s:
        targets.append(round(t, 3))
        t += STEP

    container = av.open(VIDEO)
    stream = container.streams.video[0]
    stream.thread_type = "AUTO"

    grabbed, idx = {}, 0
    for frame in container.decode(stream):
        if idx >= len(targets):
            break
        ts = float(frame.pts * stream.time_base)
        while idx < len(targets) and ts >= targets[idx]:
            img = frame.to_ndarray(format="rgb24")[Y0:Y1, X0:X1]
            grabbed[targets[idx]] = Image.fromarray(img)
            idx += 1
    container.close()

    tiles = [(t, grabbed[t]) for t in targets if t in grabbed]
    rows = (len(tiles) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * TILE, rows * (TILE + BAR)), (10, 10, 12))
    draw = ImageDraw.Draw(sheet)

    for i, (ts, img) in enumerate(tiles):
        x, y = (i % COLS) * TILE, (i // COLS) * (TILE + BAR)
        sheet.paste(img.resize((TILE, TILE)), (x, y + BAR))
        draw.rectangle([x, y, x + TILE, y + BAR], fill=(240, 240, 90))
        draw.text((x + 3, y + 3), f"{ts:.1f}", fill=(0, 0, 0))

    sheet.save(out_path)
    print(f"wrote {out_path} ({len(tiles)} tiles)")


if __name__ == "__main__":
    main()
