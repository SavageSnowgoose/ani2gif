class Bitstream:
    def __init__(self, buffer):
        self.buffer = buffer
        self.remainder = 8 if len(buffer) else 0
        self.remainder_end = 0

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

    def push_bits(self, number: int, bits: int):
        assert number < (1 << bits)
        # push the number as needed
        number = number << self.remainder_end
        total_bits = self.remainder_end + bits
        raw_bytes = number.to_bytes((total_bits + 7) // 8, "little")
        if self.remainder_end:
            self.buffer = self.buffer[:-1] + (self.buffer[-1] | raw_bytes[0]).to_bytes(1, 'little')
            raw_bytes = raw_bytes[1:]
        self.buffer += raw_bytes
        self.remainder_end = (total_bits) % 8

    def remaining_buffer(self):
        if self.remainder < 8:
            return self.buffer[1:]
        return self.buffer


if __name__ == "__main__":
    testbs = Bitstream(b'')
    testbs.push_bits(1,1)
    assert testbs.buffer == b'\x01'
    testbs.push_bits(1,1)
    assert testbs.buffer == b'\x03'
    testbs.push_bits(1,1)
    assert testbs.buffer == b'\x07'
    testbs.push_bits(1,1)
    assert testbs.buffer == b'\x0F'
    testbs.push_bits(2,2)
    assert testbs.buffer == b'\x2F'
    testbs.push_bits(2,2)
    assert testbs.buffer == b'\xAF'
