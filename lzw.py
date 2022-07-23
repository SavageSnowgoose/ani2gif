import struct


def encode_uncompressed(pixels, palette_size=256):
    assert palette_size <= 128
    output = b''
    lzw_header = struct.pack("B", 7)
    output += lzw_header

    remaining_pixels = pixels
    while len(remaining_pixels):
        chunk = remaining_pixels[:126]
        remaining_pixels = remaining_pixels[126:]

        output += struct.pack("BB", len(chunk) + 1, 0x80)
        row = []
        for j in chunk:
            row.append(j)
        output += bytes(row)

        # reset the color table, to ensure we do not grow more the table any more
        output += struct.pack("BB", 0x1, 0x81)
    output += b'\0'
    return output

def encode(pixels, max_compression_bits=None, palette_size=256):
    if max_compression_bits == 1:
        return encode_uncompressed(pixels, palette_size=palette_size)
    return encode_uncompressed(pixels, palette_size=palette_size)
