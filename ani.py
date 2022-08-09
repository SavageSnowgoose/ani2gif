import struct
import typing

from riff import Riff
from ico import Ico


DEFAULT_DELAY = 1


class AniFrame:
    def __init__(self, ico, post_delay=DEFAULT_DELAY):
        '''

        :param ico:
        :param post_delay: in jifies (1/60s)
        '''
        self.ico = ico
        self.post_delay = post_delay

class Ani:
    def __init__(self, contents: bytes):
        self.riff = Riff.from_bytes(contents)
        file_type = self.riff.identifier
        assert file_type == b'ACON'

    @property
    def frames(self) -> typing.List[AniFrame]:
        frames = []
        seq = None
        rate = None
        default_rate = DEFAULT_DELAY
        for chunk in self.riff.subChunks:
            if chunk.ckID == b'anih':
                _, frame_count, step_count, _, _, _, _, default_rate, flags = struct.unpack("<IIIIIIIII", chunk.ckData)
            elif chunk.ckID == b'LIST' and chunk.identifier == b'fram':
                # process the frames
                for subChunk in chunk.subChunks:
                    frames.append(AniFrame(Ico.from_bytes(subChunk.ckData), default_rate))
            elif chunk.ckID == b'rate':
                rate = []
                for i in range(0, chunk.ckSize, 4):
                    rate.append(int.from_bytes(chunk.ckData[i:i+4], 'little'))
            elif chunk.ckID == b'seq ':
                seq = []
                for i in range(0, chunk.ckSize, 4):
                    seq.append(int.from_bytes(chunk.ckData[i:i+4], 'little'))
        # if a seq was specified, re-arange the frames as defined by it.
        if seq is not None:
            assert len(seq)
            raw_frames = frames
            frames = []
            for item in seq:
                frames.append(raw_frames[item])
        if rate is not None:
            for index, item in enumerate(rate):
                frames[index].post_delay = item
        return frames
