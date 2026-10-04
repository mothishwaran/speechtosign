"""Dev tool: build a labelled contact sheet from a video so boundaries can be eyeballed.

Not part of the runtime pipeline. Usage:
    python tools/contact_sheet.py <video> <start_s> <end_s> <step_s> <out.png>
"""
import sys

import av
from PIL import Image, ImageDraw

TILE_W, TILE_H = 240, 180
COLS = 8
BAR = 22


def main():
    video_path, start_s, end_s, step_s, out_path = (
        sys.argv[1], float(sys.argv[2]), float(sys.argv[3]),
        float(sys.argv[4]), sys.argv[5],
    )

    targets = []
    t = start_s
    while t < end_s:
        targets.append(round(t, 3))
        t += step_s

    container = av.open(video_path)
    stream = container.streams.video[0]
    stream.thread_type = "AUTO"

    grabbed = {}
    idx = 0
    for frame in container.decode(stream):
        if idx >= len(targets):
            break
        ts = float(frame.pts * stream.time_base)
        while idx < len(targets) and ts >= targets[idx]:
            grabbed[targets[idx]] = frame.to_image()
            idx += 1
    container.close()

    tiles = [(t, grabbed[t]) for t in targets if t in grabbed]
    rows = (len(tiles) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * TILE_W, rows * (TILE_H + BAR)), (18, 18, 22))
    draw = ImageDraw.Draw(sheet)

    for i, (ts, img) in enumerate(tiles):
        col, row = i % COLS, i // COLS
        x, y = col * TILE_W, row * (TILE_H + BAR)
        sheet.paste(img.resize((TILE_W, TILE_H)), (x, y + BAR))
        draw.rectangle([x, y, x + TILE_W, y + BAR], fill=(230, 230, 60))
        draw.text((x + 5, y + 5), f"{ts:.2f}s", fill=(0, 0, 0))

    sheet.save(out_path)
    print(f"wrote {out_path}  ({len(tiles)} tiles, {rows} rows)")


if __name__ == "__main__":
    main()
