from dataclasses import dataclass
import struct

class sized_type:
    struct_type = ""

class uint_1byte(int, sized_type):
    struct_type = "B"
class uint_2byte(int, sized_type):
    struct_type = "H"
class uint_4byte(int, sized_type):
    struct_type = "I"
class int_4byte(int, sized_type):
    struct_type = "i"


class StructuredNamedTuple:
    def __bytes__(self):
        return struct.pack(self.format_string(), *self.values())

    def values(self):
        return (v for k,v in self.__dict__.items() if k in self.__annotations__)

    @classmethod
    def format_string(cls):
        format = ""
        for field in cls.__annotations__.values():
            assert issubclass(field, sized_type)
            format += field.struct_type
        return format

    @classmethod
    def from_bytes(cls, data):
        format = cls.format_string()
        fields = struct.unpack(format, data[:struct.calcsize(format)])
        return cls(*fields)


@dataclass
class Color(StructuredNamedTuple):
    blue: uint_1byte
    green: uint_1byte
    red: uint_1byte
    alpha: uint_1byte


@dataclass
class BitmapInfoHeader(StructuredNamedTuple):
    header_size: uint_4byte
    width: int_4byte
    height: int_4byte
    color_planes: uint_2byte
    bits_per_pixel: uint_2byte
    compression_method: uint_4byte
    image_size: uint_4byte
    resolution_h: uint_4byte
    resolution_v: uint_4byte
    colors_in_pallete: uint_4byte
    important_colors: uint_4byte
