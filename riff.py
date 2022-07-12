import struct
import typing


class Chunk(typing.NamedTuple):
    ckID: bytes
    ckSize: int
    ckData: bytes
    pad: bytes

    def __bytes__(self):
        return struct.pack(f"<4sI{self.ckSize}s", self.ckID, self.ckSize, self.ckData) + self.pad

    @classmethod
    def from_bytes(cls, data):
        ckID, ckSize = struct.unpack("<4sI", data[:8])
        ckData = data[8:8+ckSize]
        pad = data[8+ckSize:8+ckSize+1] if ckSize % 2 else b''
        return cls(ckID, ckSize, ckData, pad)


class Riff(typing.NamedTuple):
    ckID: bytes
    ckSize: int
    identifier: bytes
    subChunks: typing.List[Chunk]
    pad: bytes

    def __bytes__(self):
        result = struct.pack(f"<4sI4s", self.ckID, self.ckSize, self.identifier)
        for item in self.subChunks:
            result += bytes(item)
        result += self.pad
        return result

    @classmethod
    def from_bytes(cls, data):
        ckID, ckSize, identifier = struct.unpack("<4sI4s", data[:12])
        inner_data = data[12:12+ckSize]
        pad = data[12+ckSize:12+ckSize+1] if ckSize % 2 else b''
        ckData = []
        while len(inner_data):
            item = Chunk.from_bytes(inner_data)
            if item.ckID in (b"RIFF", b"LIST"):
                item = Riff.from_bytes(bytes(item))
            inner_data = inner_data[len(bytes(item)):]
            ckData.append(item)
        return cls(ckID, ckSize, identifier, ckData, pad)


