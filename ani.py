import typing

from riff import Riff
from ico import Ico


class Ani:
    def __init__(self, contents: bytes):
        self.riff = Riff.from_bytes(contents)
        file_type = self.riff.identifier
        assert file_type == b'ACON'

    @property
    def frames(self) -> typing.List[Ico]:
        frames = []

        for chunk in self.riff.subChunks:
            if chunk.ckID == b'LIST' and chunk.identifier == b'fram':
                # process the frames
                for subChunk in chunk.subChunks:
                    frames.append(Ico.from_bytes(subChunk.ckData))
        return frames
