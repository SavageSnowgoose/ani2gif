import argparse
import struct
import typing

from ani import Ani, AniFrame
from ico import Ico, Color
import lzw


def make_gif(frames: typing.List[AniFrame]):
    frame = frames[0]
    width = frame.ico.images[0].info.width
    height = frame.ico.images[0].info.height

    BITS_PER_PRIMARY_COLOR = 8
    GCT_SIZE_BITS = 8
    MAX_COLOR = (1 << GCT_SIZE_BITS) - 1
    PIXEL_ASPECT_RATIO_0_0 = 0
    HAS_GCT = 1
    SORTED = 0

    palette = frame.ico.images[0].posterize(MAX_COLOR)

    # reduce palette size if input image uses a small number of colors, leaving room for a transparent one.
    while len(palette)+1 <= (1 << (GCT_SIZE_BITS-1)):
        GCT_SIZE_BITS -= 1

    BACKGROUND_COLOR = MAX_COLOR = (1 << GCT_SIZE_BITS) - 1

    # expand the empty spots at the end of the palette
    for i in range(len(palette), MAX_COLOR+1):
        palette.append(Color(0, 0, 0, 0))

    magic = b'GIF89a'

    output = b''

    output += struct.pack("<6sHHBBB", magic, width, height, HAS_GCT << 7 | (BITS_PER_PRIMARY_COLOR-1) << 4 | SORTED << 3 | (GCT_SIZE_BITS-1), BACKGROUND_COLOR, PIXEL_ASPECT_RATIO_0_0)

    gct = []
    for i in palette: #frame.images[0].color_map:
        gct.append(struct.pack("BBB", i.red, i.green, i.blue))
    for i in range(len(palette), MAX_COLOR + 1):
        gct.append(struct.pack("BBB", 0, 0, 0))

    output += b''.join(gct)

    REPETITIONS = 65535

    BLOCK_END = 0

    gce_ani_ext = struct.pack("<2sB11sBBHB", b'!\xff', 11, b'NETSCAPE2.0', 3, 1, REPETITIONS, BLOCK_END)

    output += gce_ani_ext

    for frame in frames:
        TRANSPARENT_BACKGROUND = 1
        DISPOSAL_METHOD = 2
        frame_delay_hundredths = int(100*frame.post_delay/60)
        gce_block_inner = struct.pack('<BHB', DISPOSAL_METHOD << 2 | TRANSPARENT_BACKGROUND, frame_delay_hundredths, MAX_COLOR)
        gce_block = struct.pack('<2sB%dsB' % len(gce_block_inner), b'!\xf9', len(gce_block_inner), gce_block_inner, 0)

        output += gce_block

        local_color_table_size = 0

        IMAGE_SEPARATOR = 0x2c
        left = top = 0

        image_descriptor_block = struct.pack('<BHHHHB', IMAGE_SEPARATOR, left, top, width, height, local_color_table_size)

        output += image_descriptor_block

        # TODO: move the mask processing to ICO decoding to turn ICO into RGBA
        palettized_frame = frame.ico.images[0].palettize(palette, mask=frame.ico.images[0].mask_data)

        output += lzw.encode(palettized_frame, max_compression_bits=100, palette_size=len(palette))

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

