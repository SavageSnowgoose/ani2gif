import struct
import typing


class Color(typing.NamedTuple):
    blue: int
    green: int
    red: int
    alpha: int

    def __bytes__(self):
        return struct.pack(f"BBBB", self.blue, self.green, self.red, self.alpha)

    @classmethod
    def from_bytes(cls, data):
        fields = struct.unpack(f"BBBB", data[:4])
        return cls(*fields)


class BitmapInfoHeader(typing.NamedTuple):
    header_size: int
    width: int
    height: int
    color_planes: int
    bits_per_pixel: int
    compression_method: int
    image_size: int
    resolution_h: int
    resolution_v: int
    colors_in_pallete: int
    important_colors: int

    def __bytes__(self):
        return struct.pack(f"<IiiHHIIIIII", self.header_size, self.width, self.height, self.color_planes,
                           self.bits_per_pixel, self.compression_method, self.image_size, self.resolution_h,
                           self.resolution_h, self.colors_in_pallete, self.important_colors)

    @classmethod
    def from_bytes(cls, data):
        fields = struct.unpack(f"<IIIHHIIIIII", data[:40])
        return cls(*fields)
