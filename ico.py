import struct
import typing

from bmp import BitmapInfoHeader, Color


class IcoImageInfo(typing.NamedTuple):
    width: int
    height: int
    colors_count: int
    reserved: int
    color_planes: int
    bits_per_pixel: int
    data_size: int
    data_offset: int

    def __bytes__(self):
        return struct.pack(f"<BBBBHHII", self.width, self.height, self.colors_count, self.reserved, self.color_planes,
                           self.bits_per_pixel, self.data_size, self.data_offset)

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
            remainder = data[image_info.data_offset+40:image_info.data_offset+image_info.data_size]
            color_map = []
            for i in range(2**bmp_header.bits_per_pixel):
                color_map.append(Color.from_bytes(remainder[:4]))
                remainder = remainder[4:]
            image_data = []
            rows = []
            odd = True
            for i in range(bmp_header.height>>1):
                row = []
                for j in range(bmp_header.width):
                    if odd:
                        row.append((remainder[0] & 0xf0) >> 4)
                    else:
                        row.append(remainder[0] & 0x0f)
                        remainder = remainder[1:]
                    odd = not odd
                rows.append(row)
                #print("".join(hex(x)[-1] for x in row))
            rows.reverse()
            for row in rows:
                image_data.extend(row)
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
                #print("".join(hex(x)[-1] for x in row))
            rows.reverse()
            for row in rows:
                map_data.extend(row)

            image = IcoImage(image_info, bmp_header,
                             color_map, image_data, map_data)
            images.append(image)
            images_data = images_data[len(bytes(image_info[-1])):]
        return cls(reserved, image_type, image_count, images)


