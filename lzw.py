from typing import List
import struct

from bitstream import Bitstream



def encode_uncompressed(pixels, palette_size=256):
    assert palette_size <= 128
    output = b''
    palette_size_bits = 1
    while 1 << palette_size_bits < palette_size:
        palette_size_bits += 1
    lzw_header = struct.pack("B", max(2, palette_size_bits))
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


def encode(pixels, max_compression_bits=None, palette_size=256, extra_entries=(("CLEAR",), ("END",))):
    output_buffer = b''
    palette_size_bits = 1
    while 1 << palette_size_bits < palette_size:
        palette_size_bits += 1
    if max_compression_bits == 1:
        return encode_uncompressed(pixels, palette_size=palette_size)
    output_bitstream = Bitstream(b'')
    lzw_header = struct.pack("B", max(2, palette_size_bits))
    output_buffer += lzw_header
    dictionary : List[tuple] = [(i,) for i in range(palette_size)]
    for i in extra_entries:
        dictionary.append(i)
    index = 0
    last_entry = None

    current_bits = palette_size_bits + 1
    output_bitstream.push_bits(dictionary.index(("CLEAR",)), current_bits)
    while index < len(pixels):
        if (1 << current_bits) < len(dictionary):
            current_bits += 1

        entry = (pixels[index],)
        for i in range(1,len(dictionary)+1):
            if tuple(pixels[index:index+len(dictionary[0-i])]) == dictionary[0-i]:
                if len(dictionary[0-i]) > len(entry):
                    entry = dictionary[0-i]

        output_bitstream.push_bits(dictionary.index(entry), current_bits)

        index += len(entry)

        if index < len(pixels) and len(dictionary) < 0x1000:
            dictionary.append(entry + (pixels[index],))

    output_bitstream.push_bits(dictionary.index(("END",)), current_bits)
    for i in range(0, len(output_bitstream.buffer), 255):
        chunk = output_bitstream.buffer[i:i+255]
        output_buffer += struct.pack("B%ds" % len(chunk), len(chunk), chunk)
    output_buffer += b'\0' # chunk len 0 == end
    return output_buffer
