# /// script
# requires-python = ">=3.9"
# dependencies = ["pillow>=10"]
# ///
"""Identicon -> glory magpie in 10% notches, for a slowly changing app logo.

uv run art/transition.py   -> art/transition/{dissolve,fade}-00..10.png (512px) + sheets
dissolve: exactly k*10% of pixels show the magpie; mask+eyes first, then rays,
          then bird, then background; Bayer order within each group.
fade:     identicon laid over the magpie, alpha 1 - k/10.
emerge:   bird/mask/rays dissolve in (mask first) while the identicon
          background fades to night: crisp subject, no dithered sky.
Step 00 is the identicon; step 10 is art/out/glory-eyes-night.
"""
import pathlib, sys
from PIL import Image
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import corva

ART = pathlib.Path(__file__).parent
OUT = ART / "transition"
N = corva.N
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def identicon32():
    src = Image.open(ART / "default-avatar.png").convert("RGB")
    w = src.width
    im = Image.new("RGB", (N, N))
    for y in range(N):
        for x in range(N):
            im.putpixel((x, y), src.getpixel((int((x + .5) * w / N), int((y + .5) * w / N))))
    return im


def order(target, parts):
    bg = corva.THEMES["night"]["bg"]
    def group(x, y):
        p = parts.get((x, y))
        if p in ("mask", "eye"): return 0
        if p is None and target.getpixel((x, y)) != bg: return 1     # rays
        if p is not None: return 2                                    # bird, perch
        return 3                                                      # night sky
    px = [(x, y) for y in range(N) for x in range(N)]
    return sorted(px, key=lambda p: (group(*p), BAYER[p[1] % 4][p[0] % 4], p[1], p[0]))


def main():
    OUT.mkdir(exist_ok=True)
    start = identicon32()
    target = corva.render(**corva.VARIANTS["glory-eyes-night"])
    parts = corva.bird(False)
    seq = order(target, parts)
    bg = corva.THEMES["night"]["bg"]
    fg = [p for p in seq if p in parts or target.getpixel(p) != bg]
    for style in ("dissolve", "fade", "emerge"):
        frames = []
        for k in range(11):
            if style == "dissolve":
                im = start.copy()
                for p in seq[: round(len(seq) * k / 10)]:
                    im.putpixel(p, target.getpixel(p))
            elif style == "fade":
                im = Image.blend(target, start, 1 - k / 10)
            else:
                sky = Image.new("RGB", (N, N), bg)
                im = Image.blend(sky, start, 1 - k / 10)
                for p in fg[: round(len(fg) * k / 10)]:
                    im.putpixel(p, target.getpixel(p))
            im.resize((512, 512), Image.NEAREST).save(OUT / f"{style}-{k:02d}.png")
            frames.append(im.resize((128, 128), Image.NEAREST))
        sheet = Image.new("RGB", (11 * 136 + 8, 144), (40, 40, 44))
        for i, f in enumerate(frames):
            sheet.paste(f, (8 + i * 136, 8))
        sheet.save(OUT / f"{style}-sheet.png")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
