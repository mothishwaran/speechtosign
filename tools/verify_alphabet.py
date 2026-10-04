"""Dev tool: contact sheet of the middle frame of every letter clip, to confirm
each file actually contains the letter its filename claims."""
import os

import av
from PIL import Image, ImageDraw

OUT_DIR = "data/alphabet"
TILE, BAR, COLS = 200, 24, 7


def middle_frame(path):
    c = av.open(path)
    s = c.streams.video[0]
    frames = [f for f in c.decode(s)]
    c.close()
    return frames[len(frames) // 2].to_image() if frames else None


def main():
    letters = "abcdefghijklmnopqrstuvwxyz"
    tiles = []
    for ch in letters:
        p = os.path.join(OUT_DIR, f"{ch}.mp4")
        if os.path.exists(p):
            img = middle_frame(p)
            if img:
                tiles.append((ch, img))

    rows = (len(tiles) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * TILE, rows * (TILE + BAR)), (10, 10, 12))
    draw = ImageDraw.Draw(sheet)
    for i, (ch, img) in enumerate(tiles):
        x, y = (i % COLS) * TILE, (i // COLS) * (TILE + BAR)
        sheet.paste(img.resize((TILE, TILE)), (x, y + BAR))
        draw.rectangle([x, y, x + TILE, y + BAR], fill=(90, 220, 120))
        draw.text((x + 6, y + 7), f"file: {ch}.mp4", fill=(0, 0, 0))
    sheet.save("tools/verify.png")
    print(f"wrote tools/verify.png ({len(tiles)} clips)")


if __name__ == "__main__":
    main()
