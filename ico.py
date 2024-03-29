import struct
import typing

from bitstream import Bitstream
from bmp import BitmapInfoHeader, Color


class IcoImageInfo(typing.NamedTuple):
    width: int
    height: int
    colors_count: int
    reserved: int
    color_planes__hotspot_x: int
    bits_per_pixel__hotspot_y: int
    data_size: int
    data_offset: int

    def __bytes__(self):
        return struct.pack(f"<BBBBHHII", self.width, self.height, self.colors_count, self.reserved, self.color_planes__hotspot_x,
                           self.bits_per_pixel__hotspot_y, self.data_size, self.data_offset)

    @classmethod
    def from_bytes(cls, data):
        fields = struct.unpack("<BBBBHHII", data[:16])
        return cls(*fields)


class IcoImage(typing.NamedTuple):
    info: IcoImageInfo
    bmp_header: BitmapInfoHeader
    color_map: typing.List[Color]
    image_data: typing.List[int]
    mask_data: typing.List[int]

    def posterize(self, color_count, alpha_bits=1):
        if len(self.color_map) and color_count >= len(self.color_map):
            return self.color_map
        for i in range(8):
            palette = set()
            for index, j in enumerate(self.image_data):
                if self.bmp_header.bits_per_pixel <= 8:
                    r,g,b,a = self.color_map[j].values()
                elif self.bmp_header.bits_per_pixel == 24:
                    r,g,b = struct.unpack("BBB", j.to_bytes(3, 'big'))
                    a = 255
                elif self.bmp_header.bits_per_pixel == 32:
                    r,g,b,a = struct.unpack("BBBB", j.to_bytes(4, 'big'))
                else:
                    raise NotImplemented

                r = r >> i
                g = g >> i
                b = b >> i
                if (a < 128) or (self.mask_data[index] == 1):
                    # is transparent, so make it a consistent shade
                    r = g = b = 0
                    a = 0
                else:
                    a = a >> max(i, 8-alpha_bits)
                palette.add((r,g,b,a))
                if len(palette) > color_count:
                    break
            if len(palette) <= color_count:
                new_color_map = []
                for r, g, b, a in palette:
                    new_color_map.append(Color(r << i, g << i, b << i, a << max(i, 8-alpha_bits)))
                return new_color_map

    def palettize(self, new_color_map, transparency_index=-1, mask=None):
        if transparency_index == -1:
            transparency_index = len(new_color_map) - 1
        pixels = []
        for index, i in enumerate(self.image_data):
            if self.bmp_header.bits_per_pixel <= 8:
                color = self.color_map[i]
            elif self.bmp_header.bits_per_pixel == 32:
                color = Color(*struct.unpack("BBBB", i.to_bytes(4, 'big')))
            elif self.bmp_header.bits_per_pixel == 24:
                color = Color(*struct.unpack("BBB", i.to_bytes(3, 'big')))
            else:
                raise Exception
            if color.alpha < 128 or mask and mask[index] == 1:
                pixels.append(transparency_index)
            elif color in new_color_map:
                pixels.append(new_color_map.index(color))
            else:
                # find nearest
                best = 0
                margin = 1000
                for index, palette_color in enumerate(new_color_map):
                    new_margin = max(max(color.red, palette_color.red)-min(color.red, palette_color.red),
                                 max(color.green, palette_color.green)-min(color.green, palette_color.green),
                                 max(color.blue, palette_color.blue)-min(color.blue, palette_color.blue),
                                 #max(color.alpha, palette_color.alpha)-min(color.alpha, palette_color.alpha)
                                     )
                    if new_margin < margin:
                        margin = new_margin
                        best = index
                pixels.append(best)
        return pixels


class Ico(typing.NamedTuple):
    reserved: int
    image_type: int
    image_count: int
    images: typing.List[IcoImage]

    def __bytes__(self):
        return struct.pack(f"HHH", self.reserved, self.image_type, self.image_count)

    @classmethod
    def from_bytes(cls, data, verbose=False):
        reserved, image_type, image_count = struct.unpack("<HHH", data[:6])
        images = []
        images_data = data[6:]
        for _ in range(image_count):
            image_info = IcoImageInfo.from_bytes(images_data)
            bmp_header = BitmapInfoHeader.from_bytes(data[image_info.data_offset:image_info.data_offset+40])
            # now repeat with the deciphered size
            bmp_header = BitmapInfoHeader.from_bytes(data[image_info.data_offset:image_info.data_offset+bmp_header.header_size])
            remainder = data[image_info.data_offset+bmp_header.header_size:image_info.data_offset+image_info.data_size]
            color_map = []
            if bmp_header.bits_per_pixel <= 8:
                for i in range(2**bmp_header.bits_per_pixel):
                    color = Color.from_bytes(remainder[:4])
                    # convert RGB0 to RGBA
                    color.alpha = 255
                    color_map.append(color)
                    remainder = remainder[4:]
            image_data = []
            rows = []

            bitstream = Bitstream(remainder)
            for i in range(bmp_header.height>>1):
                row = []
                for j in range(bmp_header.width):
                    row.append(bitstream.pop_bits(bmp_header.bits_per_pixel))
                excess_bits = (32 - ((bmp_header.width * bmp_header.bits_per_pixel) % 32)) & 31
                # rows always round to nearest 4 bytes
                if excess_bits:
                    bitstream.pop_bits(excess_bits)
                rows.append(row)
            remainder = bitstream.remaining_buffer()
            rows.reverse()
            for row in rows:
                image_data.extend(row)
            if bmp_header.bits_per_pixel == 32:
                map_data = [0] * len(image_data)
            else:
                map_data = []
                rows = []
                bitstream = Bitstream(remainder)
                for i in range(bmp_header.height>>1):
                    row = []
                    for j in range(bmp_header.width):
                        row.append(bitstream.pop_bits(1))
                    # rows always round to nearest 4 bytes
                    excess_bits = (32 - ((bmp_header.width * 1) % 32)) & 31
                    if excess_bits:
                        bitstream.pop_bits(excess_bits)
                    rows.append(row)
                rows.reverse()
                for row in rows:
                    map_data.extend(row)

            image = IcoImage(image_info, bmp_header,
                             color_map, image_data, map_data)
            images.append(image)
            images_data = images_data[len(bytes(image_info[-1])):]

            #TODO: support more than 1 image per ico (currently seems to not always work...
            break


        return cls(reserved, image_type, image_count, images)


