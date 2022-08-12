import base64
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
    def __init__(self, contents: bytes, verbose=False):
        self.riff = Riff.from_bytes(contents)
        file_type = self.riff.identifier
        assert file_type == b'ACON'
        self.verbose = verbose
        if self.verbose:
            for chunk in self.riff.subChunks:
                if chunk.ckID == b'LIST' and chunk.identifier == b"INFO":
                    for subchunk in chunk.subChunks:
                        assert subchunk.ckData[-1] == 0
                        print(f"{subchunk.ckID.decode('latin-1')}: {subchunk.ckData.decode('latin-1')[:-1]}")
                elif chunk.ckID == b'anih':
                    print(f"{chunk.ckID.decode()}: {self._parse_anih(chunk.ckData)}")
                elif chunk.ckID in (b"rate", b"seq "):
                    pass
                elif chunk.ckID != b'LIST':
                    print(f"Unexpected: {chunk.ckID.decode()}: {base64.b16encode(chunk.ckData)}")
                elif chunk.identifier != b"fram":
                    print(f"Unexpected: {chunk.ckID.decode()}: {chunk.identifier} :: {chunk.subChunks}")

    @staticmethod
    def _parse_anih(data):
        assert len(data) == 36
        size, frame_count, step_count, width, height, bits_per_pixel, color_planes, default_rate, flags = struct.unpack("<IIIIIIIII", data)
        format = 'RAW' if flags & 1 == 0 else "CUR"
        seq_present = flags & 2 != 0
        remaining_flags = flags & 0xfffffffc
        assert size == len(data)
        return {'frame_count': frame_count, 'step_count': step_count, 'width': width, 'height': height,
                'bits_per_pixel': bits_per_pixel, 'color_planes': color_planes, 'default_rate': default_rate,
                'format': format, 'seq_present': seq_present, 'remaining_flags': remaining_flags}

    @property
    def ani_header(self):
        for chunk in self.riff.subChunks:
            if chunk.ckID == b'anih':
                return self._parse_anih(chunk.ckData)
        return {}

    @property
    def frames(self) -> typing.List[AniFrame]:
        frames = []
        seq = None
        rate = None
        default_rate = DEFAULT_DELAY
        expecting_seq = False
        for chunk in self.riff.subChunks:
            if chunk.ckID == b'anih':
                anih = self._parse_anih(chunk.ckData)
                default_rate = anih['default_rate']
                expecting_seq = anih['seq_present']
            elif chunk.ckID == b'LIST' and chunk.identifier == b'fram':
                # process the frames
                for subChunk in chunk.subChunks:
                    frames.append(AniFrame(Ico.from_bytes(subChunk.ckData, verbose=self.verbose), default_rate))
            elif chunk.ckID == b'rate':
                rate = []
                for i in range(0, chunk.ckSize, 4):
                    rate.append(int.from_bytes(chunk.ckData[i:i+4], 'little'))
            elif chunk.ckID == b'seq ':
                assert expecting_seq
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
        else:
            assert not expecting_seq
        if rate is not None:
            for index, item in enumerate(rate):
                frames[index].post_delay = item
        return frames
