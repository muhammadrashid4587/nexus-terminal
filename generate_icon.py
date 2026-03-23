#!/usr/bin/env python3
"""Generate NEXUS app icon as an .icns file for macOS."""

import struct
import math
import os

def create_png(size):
    """Create a simple PNG icon with a hexagon."""
    import zlib

    width = height = size

    # RGBA pixel data
    pixels = bytearray(width * height * 4)

    cx, cy = width / 2, height / 2
    r = size * 0.38  # hex radius

    def in_hexagon(x, y):
        dx, dy = x - cx, y - cy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist == 0:
            return True
        angle = math.atan2(dy, dx)
        # Distance to hexagon edge at this angle
        section = angle % (math.pi / 3)
        hex_dist = r * math.cos(math.pi / 6) / math.cos(section - math.pi / 6)
        return dist <= hex_dist

    def in_inner_hex(x, y):
        dx, dy = x - cx, y - cy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist == 0:
            return True
        angle = math.atan2(dy, dx)
        section = angle % (math.pi / 3)
        inner_r = r * 0.7
        hex_dist = inner_r * math.cos(math.pi / 6) / math.cos(section - math.pi / 6)
        return dist <= hex_dist

    for y in range(height):
        for x in range(width):
            i = (y * width + x) * 4
            if in_hexagon(x, y):
                if in_inner_hex(x, y):
                    # Inner area - dark
                    pixels[i] = 5      # R
                    pixels[i+1] = 8    # G
                    pixels[i+2] = 15   # B
                    pixels[i+3] = 255  # A
                else:
                    # Hex border - cyan glow
                    dx, dy = x - cx, y - cy
                    dist = math.sqrt(dx*dx + dy*dy)
                    t = (dist - r * 0.7) / (r * 0.3)
                    t = max(0, min(1, t))
                    pixels[i] = int(0 + t * 0)
                    pixels[i+1] = int(180 + t * 32)
                    pixels[i+2] = int(220 + t * 35)
                    pixels[i+3] = 255
            else:
                # Transparent
                pixels[i] = 0
                pixels[i+1] = 0
                pixels[i+2] = 0
                pixels[i+3] = 0

    # Draw "N" letter in center
    letter_size = int(size * 0.3)
    letter_x = int(cx - letter_size / 2)
    letter_y = int(cy - letter_size / 2)

    for py in range(letter_size):
        for px in range(letter_size):
            sx, sy = letter_x + px, letter_y + py
            if 0 <= sx < width and 0 <= sy < height:
                t_x = px / letter_size
                t_y = py / letter_size
                thickness = 0.18
                draw = False

                # Left vertical
                if t_x < thickness:
                    draw = True
                # Right vertical
                elif t_x > 1 - thickness:
                    draw = True
                # Diagonal
                elif abs(t_x - t_y) < thickness:
                    draw = True

                if draw:
                    i = (sy * width + sx) * 4
                    pixels[i] = 0
                    pixels[i+1] = 212
                    pixels[i+2] = 255
                    pixels[i+3] = 255

    # Encode as PNG
    def make_png(w, h, rgba_data):
        def chunk(chunk_type, data):
            c = chunk_type + data
            crc = zlib.crc32(c) & 0xffffffff
            return struct.pack('>I', len(data)) + c + struct.pack('>I', crc)

        raw = b''
        for row in range(h):
            raw += b'\x00'  # filter byte
            raw += bytes(rgba_data[row * w * 4:(row + 1) * w * 4])

        compressed = zlib.compress(raw)

        png = b'\x89PNG\r\n\x1a\n'
        png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
        png += chunk(b'IDAT', compressed)
        png += chunk(b'IEND', b'')
        return png

    return make_png(width, height, pixels)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resources_dir = os.path.join(script_dir, "Nexus.app", "Contents", "Resources")

    # Generate PNGs at different sizes
    sizes = [16, 32, 64, 128, 256, 512]
    for s in sizes:
        png_data = create_png(s)
        path = os.path.join(resources_dir, f"icon_{s}.png")
        with open(path, 'wb') as f:
            f.write(png_data)
        print(f"  Generated {s}x{s} icon")

    # Also save a 512 as the main icon png
    png_data = create_png(512)
    with open(os.path.join(script_dir, "static", "icon.png"), 'wb') as f:
        f.write(png_data)

    print("  Icons generated!")


if __name__ == "__main__":
    main()
