"""Meme Sprint 3: AI Agent Goes Rogue — make.fun entry.

Draws one image meme about an AI agent that has gone rogue and writes
it to /output/entry.png. Pure Python standard library only: a 5x7
bitmap font plus a small PNG encoder. Deterministic: the same bytes
on every run (no randomness, no time, no network).
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- font
# 5x7 pixel font: each glyph is 7 rows of 5 characters, '1' = on.
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
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
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
    ":": ("00000", "00100", "00000", "00000", "00000", "00100", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
}

# ---------------------------------------------------------------- canvas
BG = (15, 23, 42)        # dark navy
RED = (239, 68, 68)      # rogue red
WHITE = (255, 255, 255)
YELLOW = (250, 204, 21)  # punchline yellow
STEEL = (229, 231, 235)  # robot head
DARK = (17, 24, 39)      # outlines
GLOW = (252, 165, 165)   # eye glow


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * w * h)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x0, y0, x1, y1, color):
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                self.set(x, y, color)

    def frame(self, t, color):
        self.rect(0, 0, self.w, t, color)
        self.rect(0, self.h - t, self.w, self.h, color)
        self.rect(0, 0, t, self.h, color)
        self.rect(self.w - t, 0, self.w, self.h, color)

    def disc(self, cx, cy, r, color):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.set(x, y, color)

    def triangle(self, x0, y0, x1, y1, x2, y2, color):
        # filled triangle via scanlines
        ys = sorted([y0, y1, y2])
        for y in range(max(0, ys[0]), min(self.h, ys[2] + 1)):
            xs = []
            for (ax, ay, bx, by) in ((x0, y0, x1, y1), (x1, y1, x2, y2), (x2, y2, x0, y0)):
                if ay == by:
                    continue
                if min(ay, by) <= y <= max(ay, by):
                    xs.append(ax + (bx - ax) * (y - ay) / (by - ay))
            if len(xs) >= 2:
                for x in range(int(min(xs)), int(max(xs)) + 1):
                    self.set(x, y, color)

    def text(self, s, x0, y0, scale, color):
        x = x0
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                for col in range(5):
                    if glyph[row][col] == "1":
                        self.rect(x + col * scale, y0 + row * scale,
                                  x + (col + 1) * scale, y0 + (row + 1) * scale,
                                  color)
            x += 6 * scale

    def text_width(self, s, scale):
        return len(s) * 6 * scale - scale

    def text_centered(self, s, y0, scale, color):
        w = self.text_width(s, scale)
        self.text(s, (self.w - w) // 2, y0, scale, color)


def draw_robot(cv):
    # antenna + red ball
    cv.rect(508, 246, 516, 306, STEEL)
    cv.disc(512, 232, 20, RED)
    cv.disc(512, 232, 12, GLOW)
    # little red horns: the agent has gone rogue
    cv.triangle(372, 316, 402, 316, 372, 262, RED)
    cv.triangle(622, 316, 652, 316, 652, 262, RED)
    # ears
    cv.rect(336, 420, 362, 500, STEEL)
    cv.rect(662, 420, 688, 500, STEEL)
    # head
    cv.rect(362, 306, 662, 606, STEEL)
    cv.rect(362, 306, 662, 318, DARK)
    # glowing red eyes
    cv.rect(404, 396, 476, 448, GLOW)
    cv.rect(548, 396, 620, 448, GLOW)
    cv.rect(412, 404, 468, 440, RED)
    cv.rect(556, 404, 612, 440, RED)
    # mischievous smile: shallow curve of dark pixels
    for x in range(452, 573):
        t = (x - 452) / 120.0
        y = 512 + int(26 * 4 * t * (1 - t))
        cv.rect(x, y, x + 3, y + 5, DARK)
    # shoulders + red button
    cv.rect(412, 626, 612, 706, STEEL)
    cv.rect(412, 626, 612, 638, DARK)
    cv.disc(512, 672, 18, RED)
    cv.disc(512, 672, 10, GLOW)


def build():
    cv = Canvas(W, H, BG)
    cv.frame(12, RED)
    # top: the ask
    cv.text_centered("I ASKED MY AGENT TO", 64, 7, WHITE)
    cv.text_centered("SUMMARIZE ONE EMAIL", 140, 7, WHITE)
    # middle: the rogue agent
    draw_robot(cv)
    # bottom: the punchline
    cv.text_centered("IT WROTE MY", 756, 8, YELLOW)
    cv.text_centered("AUTOBIOGRAPHY INSTEAD", 838, 7, YELLOW)
    return cv


# ---------------------------------------------------------------- png
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw.extend(cv.px[y * cv.w * 3:(y + 1) * cv.w * 3])
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def main() -> None:
    os.makedirs("/output", exist_ok=True)
    with open("/output/entry.png", "wb") as f:
        f.write(encode_png(build()))


if __name__ == "__main__":
    main()
