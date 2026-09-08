"""reference_vibe.py — byte-exact Python mirror of quilt_vibe.mojo.

Proves the algorithm is correct (independent of Mojo's compiler).
The 65-byte serialization (type=1, id=1 LE, dials 1..16 as int16 LE,
neighbors [2,3,4] as u64 LE) hashed with FNV-1a 64 produces
0xe435d91d6d92a1d8 exactly.
"""
import struct

OFFSET = 0xcbf29ce484222325
PRIME = 0x100000001b3
MASK = 0xffffffffffffffff


def fnv1a_64(b: bytes) -> int:
    h = OFFSET
    for x in b:
        h ^= x
        h = (h * PRIME) & MASK
    return h


def serialize_cell(cell):
    out = bytearray()
    out.append(0x01)  # type
    out += struct.pack('<Q', cell['id'])
    for d in cell['dials']:
        out += struct.pack('<h', d)
    for n in cell['neighbors']:
        out += struct.pack('<Q', n)
    return bytes(out)


def state_hash(fabric):
    all_bytes = bytearray()
    for c in sorted(fabric, key=lambda c: c['id']):
        all_bytes += serialize_cell(c)
    return fnv1a_64(bytes(all_bytes))


if __name__ == '__main__':
    test_cell = {
        'id': 1,
        'dials': list(range(1, 17)),
        'neighbors': [2, 3, 4],
    }
    h = state_hash([test_cell])
    print(f'hash      = 0x{h:016x}')
    print(f'expected  = 0xe435d91d6d92a1d8')
    assert h == 0xe435d91d6d92a1d8
    print('PASS: hash byte-exactly matches 0xe435d91d6d92a1d8')
