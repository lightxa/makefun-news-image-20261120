#!/usr/bin/env python3
"""news-image-20261120: a newspaper front page summing up the world news
of Friday 20 November 2026. Pure stdlib, deterministic, no network.
Draws the page procedurally and writes it to /output/entry.png.
"""
import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (251, 248, 240)
INK = (17, 17, 17)
RED = (166, 25, 46)
BLUE = (31, 58, 110)
GOLD = (201, 141, 0)
GREY = (110, 110, 105)
LIGHT_BLUE = (214, 228, 244)
LIGHT_YELLOW = (250, 238, 200)
LIGHT_GREY = (232, 232, 228)
LIGHT_GREEN = (216, 238, 214)
LIGHT_RED = (246, 220, 222)
WHITE = (255, 255, 255)
GREEN = (28, 120, 60)
DARK_BLUE = (20, 40, 90)

# ------------------------------------------------------------------- canvas
px = bytearray(W * H * 3)


def set_pixel(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        px[i], px[i + 1], px[i + 2] = color


def fill_rect(x, y, w, h, color):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        r, g, b = color
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            px[i], px[i + 1], px[i + 2] = r, g, b


def rect_outline(x, y, w, h, color, t=2):
    fill_rect(x, y, w, t, color)
    fill_rect(x, y + h - t, w, t, color)
    fill_rect(x, y, t, h, color)
    fill_rect(x + w - t, y, t, h, color)


def draw_line(x0, y0, x1, y1, color, t=1):
    dx = x1 - x0
    dy = y1 - y0
    steps = max(abs(dx), abs(dy), 1)
    for s in range(steps + 1):
        x = x0 + dx * s // steps
        y = y0 + dy * s // steps
        half = t // 2
        for ox in range(-half, half + 1):
            for oy in range(-half, half + 1):
                set_pixel(x + ox, y + oy, color)


def fill_circle(cx, cy, r, color):
    for yy in range(cy - r, cy + r + 1):
        dy = yy - cy
        span = int(math.sqrt(max(0, r * r - dy * dy)))
        for xx in range(cx - span, cx + span + 1):
            set_pixel(xx, yy, color)


def circle_outline(cx, cy, r, color, t=3):
    for yy in range(cy - r - t, cy + r + t + 1):
        for xx in range(cx - r - t, cx + r + t + 1):
            d = math.hypot(xx - cx, yy - cy)
            if r - t <= d <= r + t * 0.5:
                set_pixel(xx, yy, color)


def fill_polygon(points, color):
    # Scanline fill for a simple polygon.
    ys = [p[1] for p in points]
    for yy in range(min(ys), max(ys) + 1):
        xs = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= yy < y1) or (y1 <= yy < y0):
                t = (yy - y0) / (y1 - y0)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for xx in range(int(math.ceil(xs[k])), int(xs[k + 1]) + 1):
                set_pixel(xx, yy, color)


def fill_triangle(x0, y0, x1, y1, x2, y2, color):
    fill_polygon([(x0, y0), (x1, y1), (x2, y2)], color)


def arc_points(cx, cy, r, a0, a1, step=4):
    pts = []
    a = a0
    while a <= a1:
        rad = math.radians(a)
        pts.append((int(cx + r * math.cos(rad)), int(cy + r * math.sin(rad))))
        a += step
    return pts


def draw_arc(cx, cy, r, a0, a1, color, t=5):
    for (x, y) in arc_points(cx, cy, r, a0, a1, step=3):
        for ox in range(-t // 2, t // 2 + 1):
            for oy in range(-t // 2, t // 2 + 1):
                set_pixel(x + ox, y + oy, color)


# --------------------------------------------------------------------- font
# 5x7 bitmap font. Each glyph is 7 rows of 5 bits ("1" = ink).
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "|": ("00100", "00100", "00100", "00100", "00100", "00100", "00100"),
}


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text(text, x, y, scale, color):
    cx = x
    for ch in text.upper():
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    fill_rect(cx + col * scale, y + row * scale, scale, scale, color)
        cx += 6 * scale
    return cx


def draw_text_centered(text, cx, y, scale, color):
    w = text_width(text, scale)
    draw_text(text, cx - w // 2, y, scale, color)


def wrap_text(text, scale, max_width):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_text_block(text, x, y, scale, color, max_width, line_gap=4):
    lines = wrap_text(text, scale, max_width)
    yy = y
    for line in lines:
        draw_text(line, x, yy, scale, color)
        yy += 7 * scale + line_gap
    return yy


# ------------------------------------------------------------------ PNG out
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    raw = bytearray()
    for yy in range(H):
        raw.append(0)
        start = yy * W * 3
        raw += px[start:start + W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", ihdr)
    data += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    data += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)
    return len(data)

# --------------------------------------------------------------- pictograms
# Each draws inside a 150x150 box whose top-left is (x, y).

def pic_clock(x, y):
    # A waiting clock: the Iran decision is put off to 2027.
    fill_circle(x + 75, y + 62, 52, WHITE)
    circle_outline(x + 75, y + 62, 52, INK, 4)
    circle_outline(x + 75, y + 62, 40, GREY, 1)
    for ang in range(0, 360, 30):
        rad = math.radians(ang)
        px0 = x + 75 + int(44 * math.cos(rad))
        py0 = y + 62 + int(44 * math.sin(rad))
        fill_circle(px0, py0, 3, INK)
    draw_line(x + 75, y + 62, x + 75, y + 28, INK, 5)   # to 12
    draw_line(x + 75, y + 62, x + 52, y + 44, INK, 5)   # to 11
    fill_circle(x + 75, y + 62, 6, RED)
    draw_text_centered("2027", x + 75, y + 122, 3, RED)


def pic_cyclone(x, y):
    # Spiral storm + rain over a coastline.
    cx, cy = x + 75, y + 68
    for r, a0, a1 in ((46, 10, 330), (36, 200, 140), (26, 30, 320),
                      (16, 180, 120), (8, 0, 300)):
        draw_arc(cx, cy, r, a0, a1, BLUE, 5)
    fill_circle(cx, cy, 7, RED)
    for dx in (-52, -20, 12, 44):
        draw_line(x + 75 + dx, y + 128, x + 70 + dx, y + 146, BLUE, 4)
    draw_line(x + 8, y + 118, x + 142, y + 118, INK, 3)


def pic_talks(x, y):
    # Two speech bubbles: EU blue with stars, Ukraine blue/yellow.
    # Left bubble (EU).
    fill_rect(x + 8, y + 18, 74, 56, BLUE)
    fill_triangle(x + 22, y + 74, x + 44, y + 74, x + 26, y + 96, BLUE)
    for sx, sy in ((22, 32), (45, 28), (66, 34), (30, 56), (58, 56)):
        fill_circle(x + sx, y + sy, 3, GOLD)
    # Right bubble (Ukraine).
    fill_rect(x + 68, y + 62, 74, 56, (245, 200, 40))
    fill_rect(x + 68, y + 62, 74, 28, (0, 91, 187))
    fill_triangle(x + 104, y + 118, x + 126, y + 118, x + 122, y + 140, (245, 200, 40))


def pic_probe(x, y):
    # Asteroid, probe with solar panels, dashed path curving away, red X.
    pts = [(x + 18, y + 96), (x + 34, y + 62), (x + 66, y + 52),
           (x + 96, y + 66), (x + 104, y + 96), (x + 84, y + 122),
           (x + 48, y + 126), (x + 24, y + 116)]
    fill_polygon(pts, (150, 148, 142))
    fill_circle(x + 52, y + 92, 9, (120, 118, 112))
    fill_circle(x + 80, y + 84, 6, (120, 118, 112))
    fill_circle(x + 66, y + 108, 5, (120, 118, 112))
    # Probe.
    fill_rect(x + 96, y + 16, 20, 16, GOLD)
    fill_rect(x + 78, y + 20, 16, 8, BLUE)
    fill_rect(x + 118, y + 20, 16, 8, BLUE)
    # Dashed path away from the asteroid.
    for i in range(6):
        t = i / 6.0
        dx = int(96 + t * 40)
        dy = int(48 - t * 22)
        fill_circle(x + dx, y + dy, 3, RED)
    draw_line(x + 118, y + 12, x + 136, y + 30, RED, 5)
    draw_line(x + 136, y + 12, x + 118, y + 30, RED, 5)


def pic_ship(x, y):
    # Container ship + rising arrow: exports hit $1 trillion.
    fill_rect(x + 14, y + 96, 122, 26, (40, 60, 90))
    fill_triangle(x + 136, y + 96, x + 150, y + 96, x + 136, y + 122, (40, 60, 90))
    for cx0, col in ((22, RED), (52, BLUE), (82, GREEN), (112, GOLD)):
        fill_rect(x + cx0, y + 66, 26, 30, col)
        fill_rect(x + cx0, y + 66, 26, 4, WHITE)
    # Rising arrow.
    draw_line(x + 34, y + 52, x + 74, y + 14, GREEN, 6)
    draw_line(x + 74, y + 14, x + 74, y + 34, GREEN, 6)
    draw_line(x + 74, y + 14, x + 54, y + 14, GREEN, 6)
    fill_triangle(x + 74, y + 6, x + 62, y + 22, x + 86, y + 22, GREEN)
    draw_text_centered("$1 TRILLION", x + 75, y + 128, 2, GREEN)


def pic_controller(x, y):
    # Game controller + gold star: GTA 6 outsells The Odyssey.
    pts = [(x + 18, y + 58), (x + 18, y + 104), (x + 40, y + 118),
           (x + 58, y + 104), (x + 92, y + 104), (x + 110, y + 118),
           (x + 132, y + 104), (x + 132, y + 58), (x + 75, y + 48)]
    fill_polygon(pts, INK)
    # D-pad.
    fill_rect(x + 32, y + 66, 8, 24, WHITE)
    fill_rect(x + 24, y + 74, 24, 8, WHITE)
    # Buttons.
    for bx, by, col in ((102, 70, RED), (114, 80, GOLD),
                        (102, 90, GREEN), (90, 80, BLUE)):
        fill_circle(x + bx, y + by, 6, col)
    # Gold star above.
    sx, sy = x + 75, y + 26
    star = []
    for i in range(10):
        r = 20 if i % 2 == 0 else 8
        ang = math.radians(-90 + i * 36)
        star.append((int(sx + r * math.cos(ang)), int(sy + r * math.sin(ang))))
    fill_polygon(star, GOLD)


# ------------------------------------------------------------------ stories
# Six stories, each first reported on Friday 20 November 2026.
# Sources: Reuters / Times of India, The Hindu, BBC, Space.com,
# 20 Nov daily news digests, Mezha.
STORIES = [
    ("USA / MIDDLE EAST", "TRUMP: NO RUSH ON IRAN",
     "Decision on war put off to 2027", pic_clock, LIGHT_RED),
    ("INDIA", "CYCLONE AKVAN HITS INDIA",
     "300,000 evacuated in Odisha", pic_cyclone, LIGHT_BLUE),
    ("EUROPE", "EUROPE READY FOR UKRAINE TALKS",
     "Leaders open to talks with Russia", pic_talks, LIGHT_YELLOW),
    ("JAPAN / SPACE", "HAYABUSA2 LANDING IS OFF",
     "Engine trouble ends asteroid plan", pic_probe, LIGHT_GREY),
    ("ECONOMY", "KOREA EXPORTS TOP $1 TRILLION",
     "A first for South Korea", pic_ship, LIGHT_GREEN),
    ("ENTERTAINMENT", "GTA 6 SALES PASS $1.8 BN",
     "Beats The Odyssey's global run", pic_controller, LIGHT_YELLOW),
]


def draw_cell(idx, x, y, w, h):
    tag, headline, sub, pic, tint = STORIES[idx]
    fill_rect(x, y, w, h, tint)
    rect_outline(x, y, w, h, INK, 2)
    draw_text(tag, x + 12, y + 10, 2, RED)
    fill_rect(x + 12, y + 30, w - 24, 2, INK)
    pic(x + 10, y + 44)
    tx = x + 172
    tw = w - 172 - 12
    draw_text_block(headline, tx, y + 48, 3, INK, tw, line_gap=6)
    # Sub sits under the headline block (3 lines max at scale 3).
    draw_text_block(sub, tx, y + 48 + 3 * (7 * 3 + 6), 2, (60, 60, 60), tw,
                    line_gap=4)
    # Kicker line at the bottom of the cell.
    draw_text("20 NOV 2026", x + 12, y + h - 24, 2, GREY)


def main():
    fill_rect(0, 0, W, H, PAPER)
    # Masthead.
    draw_text_centered("THE WORLD TODAY", W // 2, 26, 7, INK)
    fill_rect(24, 108, W - 48, 4, RED)
    draw_text_centered("FRIDAY 20 NOVEMBER 2026", W // 2, 126, 5, RED)
    draw_text_centered("SIX STORIES FROM AROUND THE WORLD",
                       W // 2, 172, 2, INK)
    fill_rect(24, 198, W - 48, 3, INK)
    # Story grid: 2 columns x 3 rows.
    gx, gy = 24, 214
    cw = (W - 48 - 16) // 2
    ch = 240
    for row in range(3):
        for col in range(2):
            idx = row * 2 + col
            draw_cell(idx, gx + col * (cw + 16), gy + row * (ch + 12),
                      cw, ch)
    # Footer.
    fy = gy + 3 * ch + 2 * 12 + 8
    draw_text_centered(
        "ALL STORIES FIRST REPORTED FRIDAY 20 NOVEMBER 2026",
        W // 2, fy, 2, INK)
    draw_text_centered(
        "SOURCES: REUTERS - BBC - THE HINDU - SPACE.COM",
        W // 2, fy + 20, 2, GREY)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path)
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
