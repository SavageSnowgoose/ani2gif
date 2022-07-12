import argparse
import struct
import typing

from ani import Ani
from ico import Ico


def make_gif(frames: typing.List[Ico]):
    frame = frames[0]
    width = frame.images[0].info.width
    height = frame.images[0].info.height

    MAX_COLOR = 0x7F
    magic = b'GIF89a'

    output = b''

    output += struct.pack("<6sHHBBB", magic, width, height, 0xE6, MAX_COLOR, 0)

    gct = []
    for i in frame.images[0].color_map:
        gct.append(struct.pack("BBB", i.red, i.green, i.blue))
    for i in range(16, 128):
        gct.append(struct.pack("BBB", 0, 0, 0))

    output += b''.join(gct)

    gce_ani_ext = struct.pack("<2sB11sBBHB", b'!\xff', 11, b'NETSCAPE2.0', 3, 1, 65535, 0)

    output += gce_ani_ext

    for frame in frames:

        gce_block = struct.pack('<2sBBHBB', b'!\xf9', 4, 0x4 | 0x1, 9, MAX_COLOR, 0)

        output += gce_block

        image_descriptor_block = struct.pack('<BHHHHB', 0x2c, 0, 0, width, height, 0)

        output += image_descriptor_block

        lzw_header = struct.pack("B", 7)
        output += lzw_header
        index = 0
        for i in range(height):
            output += struct.pack("BB", width + 1, 0x80)
            row = []
            for j in range(width):
                if frame.images[0].mask_data[index] == 1:
                    row.append(MAX_COLOR)
                else:
                    row.append(frame.images[0].image_data[index])
                index += 1
            output += bytes(row)
            output += struct.pack("BB", 0x1, 0x81)
        output += b'\0'
    output += b'\x3B'  # EOF
    return output


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("ani_file")
    parser.add_argument("output_file")

    args = parser.parse_args()

    with open(args.ani_file, "rb") as file:
        contents = file.read()

    ani = Ani(contents)

    # now convert to gif
    with open(args.output_file, "wb") as outfile:
        outfile.write(make_gif(ani.frames))

