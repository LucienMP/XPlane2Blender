"""
Makes the fixed props of the visual parity test (see README.md):

- palette.png: eight flat colour cells, 4 x 2 in a 512 x 256 image. A model's
  materials point their UVs at a cell, so every pixel of it is one known colour.
- booth.obj: a 60 m black box the model stands in. At night nothing lights it,
  so the background is dark and the model's self-lit colours have nothing to
  reflect. A lit green booth was tried first: its light reflected off the model
  as a white specular term, turning red faces yellow. GLOBAL_specular 0 keeps
  the floor from mirroring the model.

    python make_booth.py OUT_DIR
"""
import os
import struct
import sys
import zlib

# Name and RGB; black is the booth's, every other cell is for models
PALETTE = [
    ("red", (255, 0, 0)),
    ("blue", (0, 0, 255)),
    ("yellow", (255, 255, 0)),
    ("cyan", (0, 255, 255)),
    ("magenta", (255, 0, 255)),
    ("white", (255, 255, 255)),
    ("green", (0, 255, 0)),
    ("black", (0, 0, 0)),
]
BACKGROUND = "black"
COLUMNS, ROWS = 4, 2
CELL = 128
WIDTH, HEIGHT = COLUMNS * CELL, ROWS * CELL
BOOTH_HALF = 30.0
BOOTH_HEIGHT = 30.0
BOOTH_FLOOR = 0.05


def cell_uv(name):
    """The UV at the centre of a colour's cell; v = 0 is the image's bottom row"""
    index = [n for n, _ in PALETTE].index(name)
    column, row = index % COLUMNS, index // COLUMNS
    return (column + 0.5) / COLUMNS, 1.0 - (row + 0.5) / ROWS


def write_png(path, width, height, rows):
    """rows: list of bytes, each width * 3 RGB bytes"""
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + row for row in rows)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def write_palette(path):
    rows = []
    for y in range(HEIGHT):
        row = bytearray()
        for x in range(WIDTH):
            index = (y // CELL) * COLUMNS + x // CELL
            row += bytes(PALETTE[index][1])
        rows.append(bytes(row))
    write_png(path, WIDTH, HEIGHT, rows)


def write_booth(path):
    """
    An inside-out box, floor just above the ground, every face UV-mapped to the
    black cell. ATTR_no_cull so the winding doesn't matter from inside
    """
    u, v = cell_uv(BACKGROUND)
    h, top, floor = BOOTH_HALF, BOOTH_HEIGHT, BOOTH_FLOOR
    # OBJ coordinates: X east, Y up, Z south. The model origin is at (0, 0, 0)
    corners = {
        "fbl": (-h, floor, h), "fbr": (h, floor, h), "ftl": (-h, top, h), "ftr": (h, top, h),
        "bbl": (-h, floor, -h), "bbr": (h, floor, -h), "btl": (-h, top, -h), "btr": (h, top, -h),
    }
    faces = [
        ("fbl", "fbr", "ftr", "ftl", (0, 0, -1)),  # south wall, seen from inside
        ("bbr", "bbl", "btl", "btr", (0, 0, 1)),   # north wall
        ("bbl", "fbl", "ftl", "btl", (1, 0, 0)),   # west wall
        ("fbr", "bbr", "btr", "ftr", (-1, 0, 0)),  # east wall
        ("bbl", "bbr", "fbr", "fbl", (0, 1, 0)),   # floor
        ("ftl", "ftr", "btr", "btl", (0, -1, 0)),  # ceiling
    ]
    vts, idx = [], []
    for face in faces:
        normal = face[4]
        base = len(vts)
        for name in face[:4]:
            x, y, z = corners[name]
            vts.append(f"VT\t{x:g}\t{y:g}\t{z:g}\t{normal[0]}\t{normal[1]}\t{normal[2]}\t{u:g}\t{v:g}")
        idx += [base, base + 1, base + 2, base, base + 2, base + 3]
    lines = ["I", "800", "OBJ", "", "TEXTURE\tpalette.png", "TEXTURE_LIT\tpalette.png",
             "GLOBAL_no_shadow", "GLOBAL_specular	0", f"POINT_COUNTS\t{len(vts)}\t0\t0\t{len(idx)}", ""]
    lines += vts + [""]
    for i in range(0, len(idx) - len(idx) % 10, 10):
        lines.append("IDX10\t" + "\t".join(str(n) for n in idx[i : i + 10]))
    for n in idx[len(idx) - len(idx) % 10 :]:
        lines.append(f"IDX\t{n}")
    lines += ["", "ATTR_no_cull", f"TRIS\t0\t{len(idx)}", ""]
    with open(path, "w", newline="\n") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "work"
    os.makedirs(out, exist_ok=True)
    write_palette(os.path.join(out, "palette.png"))
    write_booth(os.path.join(out, "booth.obj"))
    print("wrote palette.png and booth.obj in", out)
