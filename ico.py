import struct
import typing

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
        if self.bmp_header.bits_per_pixel <= 8:
            raise Exception
        elif self.bmp_header.bits_per_pixel < 32:
            raise Exception
        else:
            for i in range(8):
                palette = set()
                for index, j in enumerate(self.image_data):
                    r,g,b,o = struct.unpack("BBBB", j.to_bytes(4, 'big'))
                    r = r >> i
                    g = g >> i
                    b = b >> i
                    o = o >> max(i, alpha_bits)
                    if (o < (255 >> max(i, alpha_bits))) or (self.mask_data[index] == 1):
                        # is transparent, so make it a consistent shade
                        r = g = b = 0
                        o = 0
                    #o = 0
                    palette.add((r,g,b,o))
                    if len(palette) > color_count:
                        break
                if len(palette) <= color_count:
                    new_color_map = []
                    for r, g, b, o in palette:
                        new_color_map.append(Color(r << i, g << i, b << i, o << i))
                    return new_color_map

    def palettize(self, new_color_map):
        pixels = []
        for i in self.image_data:
            if self.bmp_header.bits_per_pixel <= 8:
                color = self.color_map[i]
            elif self.bmp_header.bits_per_pixel == 32:
                color = Color(*struct.unpack("BBBB", i.to_bytes(4, 'big')))
            else:
                raise Exception
            if color in new_color_map:
                pixels.append(new_color_map.index(color))
            else:
                # find nearest
                best = 0
                margin = 1000
                for index, palette_color in enumerate(new_color_map):
                    new_margin = max(max(color.red, palette_color.red)-min(color.red, palette_color.red),
                                 max(color.green, palette_color.green)-min(color.green, palette_color.green),
                                 max(color.blue, palette_color.blue)-min(color.blue, palette_color.blue),
                                 max(color.alpha, palette_color.alpha)-min(color.alpha, palette_color.alpha)
                                     )
                    if new_margin < margin:
                        margin = new_margin
                        best = index
                pixels.append(best)
        return pixels


class Bitstream:
    def __init__(self, buffer):
        self.buffer = buffer
        self.remainder = 8 if len(buffer) else 0

    def pop_bits(self, bits):
        result = 0
        while bits >= self.remainder:
            result = result << self.remainder
            result += self.buffer[0] & (0xFF >> (8-self.remainder))
            bits -= self.remainder
            self.remainder = 8
            self.buffer = self.buffer[1:]
        if bits:
            result = result << bits
            result += (self.buffer[0] & (0xFF >> (8-self.remainder))) >> (self.remainder - bits)
            self.remainder -= bits
        return result

    def remaining_buffer(self):
        if self.remainder < 8:
            return self.buffer[1:]
        return self.buffer


class Ico(typing.NamedTuple):
    reserved: int
    image_type: int
    image_count: int
    images: typing.List[IcoImage]

    def __bytes__(self):
        return struct.pack(f"HHH", self.reserved, self.image_type, self.image_count)

    @classmethod
    def from_bytes(cls, data):
        reserved, image_type, image_count = struct.unpack("<HHH", data[:6])
        images = []
        images_data = data[6:]
        for i in range(image_count):
            image_info = IcoImageInfo.from_bytes(images_data)
            bmp_header = BitmapInfoHeader.from_bytes(data[image_info.data_offset:image_info.data_offset+40])
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
                index = 7
                for i in range(bmp_header.height>>1):
                    row = []
                    for j in range(bmp_header.width):
                        row.append((remainder[0] >> index) & 1)
                        if index == 0:
                            remainder = remainder[1:]
                            index = 8
                        index -= 1
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


