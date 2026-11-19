# /// script
# requires-python = ">=3.9"
# dependencies = ["pillow>=10"]
# ///
"""Pixel-art avatars for Muse Corva: a masked magpie with a faint orange glory.

uv run art/corva.py        -> art/out/<variant>.png (512px) + <variant>-32.png + sheet.png
Deterministic: same code, same pixels. Shapes are sampled on a 32x32 grid.
"""
import math, pathlib
from PIL import Image

N = 32
OUT = pathlib.Path(__file__).parent / "out"
ORANGE = (217, 119, 87)      # Claude-ish terracotta orange
HOT = (246, 178, 132)        # eye/mouth light

THEMES = {
    "night": dict(bg=(18, 19, 26), rays=[(74, 42, 34), (143, 76, 53), ORANGE],
                  black=(10, 10, 14), sheen=(44, 58, 92), white=(236, 232, 224), shade=(150, 146, 140),
                  mask=(96, 44, 30), beak=(66, 66, 80), rim=(160, 84, 56), perch=(58, 44, 36)),
    "dawn":  dict(bg=(240, 233, 222), rays=[(246, 214, 196), (234, 169, 138), ORANGE],
                  black=(22, 22, 28), sheen=(52, 70, 110), white=(252, 250, 246), shade=(176, 170, 162),
                  mask=(140, 62, 38), beak=(40, 40, 48), rim=(226, 150, 116), perch=(120, 96, 78)),
}

# ray set: (angle deg, half-width deg, length) -- uneven on purpose, like a hand-drawn spark
RAYS = [(-90, 4, 17), (-66, 3, 12), (-42, 3.5, 16), (-20, 3, 10),
        (-114, 3, 12), (-138, 3.5, 16), (-160, 3, 10)]   # crown fan: upper half only


def inside_ellipse(x, y, cx, cy, rx, ry):
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1


def inside_tri(x, y, a, b, c):
    def s(p, q, r): return (p[0] - r[0]) * (q[1] - r[1]) - (q[0] - r[0]) * (p[1] - r[1])
    d1, d2, d3 = s((x, y), a, b), s((x, y), b, c), s((x, y), c, a)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def inside_rot_ellipse(x, y, cx, cy, rx, ry, deg):
    t = math.radians(deg)
    dx, dy = x - cx, y - cy
    u, v = dx * math.cos(t) + dy * math.sin(t), -dx * math.sin(t) + dy * math.cos(t)
    return (u / rx) ** 2 + (v / ry) ** 2 <= 1


def inside_quad(x, y, a, b, c, d):
    return inside_tri(x, y, a, b, c) or inside_tri(x, y, a, c, d)


HEAD = (18.5, 10.5)
EYE = (20, 10)
TIP = (27.5, 11.4)


def bird(open_beak):
    """-> dict (x,y) -> part name, for pixels the magpie covers (perched, facing right)."""
    px = {}
    for y in range(N):
        for x in range(N):
            X, Y = x + .5, y + .5
            part = None
            if inside_quad(X, Y, (10, 19.5), (12.5, 21.5), (4.2, 31.5), (1.8, 30.5)): part = "tail"
            if inside_rot_ellipse(X, Y, 14, 18.5, 7.2, 4.6, -32):  part = "black"   # body
            if inside_ellipse(X, Y, 17.6, 14, 3.6, 3.8):            part = "black"   # neck
            if inside_ellipse(X, Y, *HEAD, 4.6, 4.3):               part = "black"   # head
            if inside_rot_ellipse(X, Y, 16.6, 20.2, 3.6, 2.6, -32) and part == "black": part = "white"  # belly
            if inside_rot_ellipse(X, Y, 11.8, 16.2, 3.6, 1.3, -32): part = "white"   # scapular streak
            if inside_rot_ellipse(X, Y, 10.6, 18.6, 3.8, 1.5, -32): part = "sheen"   # wing
            if part == "black" and 9.2 <= Y <= 11.4 and X >= 15.5 and inside_ellipse(X, Y, *HEAD, 5, 4.7):
                part = "mask"
            if open_beak:
                if inside_tri(X, Y, (22, 9.4), TIP, (22, 11.4)):            part = "beak"
                if inside_tri(X, Y, (22, 12.4), (26.5, 12.8), (22, 13.6)):   part = "beak"
                if inside_tri(X, Y, (22, 11.4), (TIP[0] - .5, 11.9), (22, 12.4)): part = "mouth"
            elif inside_tri(X, Y, (22, 9.4), TIP, (22, 13.2)):
                part = "beak"
            if part:
                px[(x, y)] = part
    for lx in (15, 17):                                   # legs
        for ly in (24, 25):
            px[(lx, ly)] = "beak"
    for x in range(6, 28):                                # perch
        if (x, 26) not in px:
            px[(x, 26)] = "perch"
    px[(int(EYE[0]), int(EYE[1]))] = "eye"
    return px


def ray_level(x, y, cx, cy, rays, scale=1.0, ring=None):
    dx, dy = x + .5 - cx, y + .5 - cy
    d = math.hypot(dx, dy)
    ang = math.degrees(math.atan2(dy, dx))
    best = 0.0
    for a, w, ln in rays:
        da = abs((ang - a + 180) % 360 - 180)
        if da < w and d < ln * scale:
            best = max(best, (1 - da / w) * (1 - d / (ln * scale)) ** 0.7)
    if ring and abs(d - ring) < 0.7 and dy < 1.5:
        best = max(best, 0.35)
    if best > 0.62: return 3
    if best > 0.34: return 2
    if best > 0.12 and (x + y) % 2 == 0: return 1    # dithered faint edge
    return 0


def render(theme, glow, open_beak=False, ring=None, mask=True):
    t = THEMES[theme]
    img = Image.new("RGB", (N, N), t["bg"])
    b = bird(open_beak)
    up = [(a, w, l) for a, w, l in RAYS if -170 <= a <= -10]
    halo_c = (HEAD[0] - .5, HEAD[1] - .5)
    centers = {"halo": (halo_c, RAYS, 1.0), "eyes": ((EYE[0] - 1.5, EYE[1]), up, 0.75),
               "mouth": ((TIP[0] - 1, TIP[1] + .3), [(-24, 5, 12), (-8, 5, 15), (8, 5, 15), (24, 5, 12)], 1.0)}
    on = lambda k: glow == "all" or k in glow.split("+")
    layers = [centers[k] for k in ("halo", "eyes", "mouth") if on(k)]
    for y in range(N):
        for x in range(N):
            if (x, y) in b:
                continue
            lvl = max([ray_level(x, y, c[0], c[1], r, s, ring) for c, r, s in layers] or [0])
            if lvl:
                img.putpixel((x, y), t["rays"][lvl - 1])
    glowing = on("eyes")
    for (x, y), part in b.items():
        col = {"black": t["black"], "white": t["white"], "shade": t["shade"], "sheen": t["sheen"],
               "tail": t["sheen"], "perch": t["perch"],
               "mask": (ORANGE if glowing else t["mask"]) if mask else t["black"],
               "beak": t["beak"], "mouth": HOT, "eye": HOT}[part]
        img.putpixel((x, y), col)
    if on("halo"):                                        # faint rim only on the crown
        for (x, y), part in b.items():
            if part == "black" and y <= HEAD[1] - 2 and (x, y - 1) not in b:
                img.putpixel((x, y), t["rim"])
    return img


VARIANTS = {
    "glory-eyes-night": dict(theme="night", glow="halo+eyes"),   # halo + glowing mask
    "glory-night":      dict(theme="night", glow="halo"),
    "eyes-night":       dict(theme="night", glow="eyes"),
    "full-night":       dict(theme="night", glow="all", open_beak=True),
    "glory-eyes-dawn":  dict(theme="dawn", glow="halo+eyes"),
    "glory-dawn":       dict(theme="dawn", glow="halo"),
    "eyes-dawn":        dict(theme="dawn", glow="eyes"),
    "song-night":       dict(theme="night", glow="mouth+eyes", open_beak=True),
}

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    tiles = []
    for name, kw in VARIANTS.items():
        im = render(**kw)
        im.save(OUT / f"{name}-32.png")
        big = im.resize((512, 512), Image.NEAREST)
        big.save(OUT / f"{name}.png")
        tiles.append(im.resize((256, 256), Image.NEAREST))
    cols = 4
    sheet = Image.new("RGB", (cols * 264 + 8, ((len(tiles) + cols - 1) // cols) * 264 + 8), (40, 40, 44))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, (8 + (i % cols) * 264, 8 + (i // cols) * 264))
    sheet.save(OUT / "sheet.png")
    print("\n".join(VARIANTS))
