# quilt_vibe.mojo — Quilt cell-fabric runtime in Mojo, vibe-coded from
# QUILT_VIBE_PROTOCOL.md by a fresh Claude session on 7 Sep 2026.
# Test hash 0xe435d91d6d92a1d8 verified byte-exact.
#
# 2026-09-30: mechanical drift fixes for Mojo 1.2.0.dev2026100105
# (fn->def, let->var, inout->out/mut self, iterator deref removal,
# raises on Dict getitem, shift-width casts, prelude import quirk,
# String.format/hex() replacement for u64 display — hex() sign-extends
# UInt64 on this nightly). Originals: *.orig-20260930.

from std import sys


def u64_hex(v: UInt64) -> String:
    # Display helper: this nightly's hex() sign-extends UInt64, so hashes
    # >= 2^63 print negative. Manual LSB-first formatter instead.
    var digits = String("0123456789abcdef")
    var out = String()
    var x = v
    if x == 0:
        return String("0")
    while x != 0:
        out = digits[byte=Int(x & 15)] + out
        x = x >> 4
    return out^


struct Cell(Copyable):
    var id: UInt64
    var dials: SIMD[DType.int16, 16]
    var neighbors: List[UInt64]

    def __init__(out self, id: UInt64, dials: SIMD[DType.int16, 16], neighbors: List[UInt64]):
        self.id = id
        self.dials = dials
        self.neighbors = neighbors.copy()

    # BIND: sets the dials, idempotent
    def bind(mut self, dials: SIMD[DType.int16, 16]):
        self.dials = dials

    # VIEW: returns dials
    def view(self) -> SIMD[DType.int16, 16]:
        return self.dials


struct Fabric:
    var cells: Dict[Int64, Cell]

    def __init__(out self):
        self.cells = Dict[Int64, Cell]()

    # LINK: adds an undirected edge
    def link(mut self, a_id: Int64, b_id: Int64) raises:
        if a_id in self.cells:
            var a = self.cells[a_id].copy()
            a.neighbors.append(UInt64(b_id))
            self.cells[a_id] = a^
        if b_id in self.cells:
            var b = self.cells[b_id].copy()
            b.neighbors.append(UInt64(a_id))
            self.cells[b_id] = b^

    # EFFECT: propagates dial[0] to neighbors
    def effect(mut self) raises:
        for cid in self.cells.keys():
            var c = self.cells[cid].copy()
            var sum: Int64 = 0
            for n in c.neighbors:
                if Int64(n) in self.cells:
                    sum += Int64(self.cells[Int64(n)].dials[0])
            if len(c.neighbors) > 0:
                c.dials[0] = Int16(sum // Int64(len(c.neighbors)))
            self.cells[cid] = c^

    # TICK: advances all dials by 1 in alternating direction
    def tick(mut self) raises:
        for cid in self.cells.keys():
            var c = self.cells[cid].copy()
            var dir = 1 if (cid + Int64(len(c.dials))) % 2 == 0 else -1
            for i in range(16):
                c.dials[i] = c.dials[i] + Int16(dir)
            self.cells[cid] = c^


# FNV-1a 64-bit hash
def fnv1a_64(data: List[UInt8]) -> UInt64:
    var h: UInt64 = 0xcbf29ce484222325
    for b in data:
        h = h ^ UInt64(b)
        h = (h * 0x100000001b3) & 0xffffffffffffffff
    return h


# Canonical serialization: type(1) + id(8) + dials(32) + neighbors(8*N)
def serialize_cell(c: Cell) -> List[UInt8]:
    var out = List[UInt8]()
    out.append(0x01)  # type = cell
    # id as 8 bytes LE
    for i in range(8):
        out.append(UInt8((c.id >> UInt64(i * 8)) & 0xff))
    # dials as 16 × int16 LE
    for i in range(16):
        var d = Int64(c.dials[i])
        for j in range(2):
            out.append(UInt8((d >> Int64(j * 8)) & 0xff))
    # neighbors as 8 bytes each
    for n in c.neighbors:
        for i in range(8):
            out.append(UInt8((n >> UInt64(i * 8)) & 0xff))
    return out^


def state_hash(fabric: Fabric) raises -> UInt64:
    var all_bytes = List[UInt8]()
    for cid in fabric.cells.keys():
        var cell = fabric.cells[cid].copy()
        var bytes = serialize_cell(cell)
        for b in bytes:
            all_bytes.append(b)
    return fnv1a_64(all_bytes)


def main() raises:
    # Build the test cell
    var dials = SIMD[DType.int16, 16]()
    for i in range(16):
        dials[i] = Int16(i + 1)

    var neighbors = List[UInt64]()
    neighbors.append(2)
    neighbors.append(3)
    neighbors.append(4)

    var test_cell = Cell(1, dials, neighbors)
    var fabric = Fabric()
    fabric.cells[1] = test_cell^

    var h = state_hash(fabric)
    print("hash      = 0x" + u64_hex(h))
    print("expected  = 0xe435d91d6d92a1d8")
    if h == 0xe435d91d6d92a1d8:
        print("PASS: hash byte-exactly matches 0xe435d91d6d92a1d8")
    else:
        print("FAIL: hash mismatch")
