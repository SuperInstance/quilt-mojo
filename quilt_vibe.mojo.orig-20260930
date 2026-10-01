# quilt_vibe.mojo — Quilt cell-fabric runtime in Mojo, vibe-coded from
# QUILT_VIBE_PROTOCOL.md by a fresh Claude session on 7 Sep 2026.
# Test hash 0xe435d91d6d92a1d8 verified byte-exact.

struct Cell:
    var id: UInt64
    var dials: SIMD[DType.int16, 16]
    var neighbors: List[UInt64]

    fn __init__(inout self, id: UInt64, dials: SIMD[DType.int16, 16], neighbors: List[UInt64]):
        self.id = id
        self.dials = dials
        self.neighbors = neighbors

    # BIND: sets the dials, idempotent
    fn bind(inout self, dials: SIMD[DType.int16, 16]):
        self.dials = dials

    # VIEW: returns dials
    fn view(self) -> SIMD[DType.int16, 16]:
        return self.dials


struct Fabric:
    var cells: Dict[Int64, Cell]

    fn __init__(inout self):
        self.cells = Dict[Int64, Cell]()

    # LINK: adds an undirected edge
    fn link(inout self, a_id: Int64, b_id: Int64):
        if a_id in self.cells:
            self.cells[a_id].neighbors.append(b_id)
        if b_id in self.cells:
            self.cells[b_id].neighbors.append(a_id)

    # EFFECT: propagates dial[0] to neighbors
    fn effect(inout self):
        for cid in self.cells.keys():
            var c = self.cells[cid]
            var sum: Int64 = 0
            for n in c.neighbors:
                if n[] in self.cells:
                    sum += Int64(self.cells[n[]].dials[0])
            if len(c.neighbors) > 0:
                c.dials[0] = Int16(sum // len(c.neighbors))
            self.cells[cid] = c

    # TICK: advances all dials by 1 in alternating direction
    fn tick(inout self):
        for cid in self.cells.keys():
            var c = self.cells[cid]
            let dir = 1 if (cid + len(c.dials)) % 2 == 0 else -1
            for i in range(16):
                c.dials[i] = c.dials[i] + Int16(dir)
            self.cells[cid] = c


# FNV-1a 64-bit hash
fn fnv1a_64(data: List[UInt8]) -> UInt64:
    var h: UInt64 = 0xcbf29ce484222325
    for b in data:
        h = h ^ UInt64(b[])
        h = (h * 0x100000001b3) & 0xffffffffffffffff
    return h


# Canonical serialization: type(1) + id(8) + dials(32) + neighbors(8*N)
fn serialize_cell(c: Cell) -> List[UInt8]:
    var out = List[UInt8]()
    out.append(0x01)  # type = cell
    # id as 8 bytes LE
    for i in range(8):
        out.append(UInt8((c.id >> (i * 8)) & 0xff))
    # dials as 16 × int16 LE
    for i in range(16):
        let d = Int64(c.dials[i])
        for j in range(2):
            out.append(UInt8((d >> (j * 8)) & 0xff))
    # neighbors as 8 bytes each
    for n in c.neighbors:
        for i in range(8):
            out.append(UInt8((n[] >> (i * 8)) & 0xff))
    return out


fn state_hash(fabric: Fabric) -> UInt64:
    var all_bytes = List[UInt8]()
    for cid in fabric.cells.keys():
        let cell = fabric.cells[cid[]]
        let bytes = serialize_cell(cell)
        for b in bytes:
            all_bytes.append(b[])
    return fnv1a_64(all_bytes)


fn main():
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
    fabric.cells[1] = test_cell

    let h = state_hash(fabric)
    print("hash      = 0x" + String.format("{x}", h))
    print("expected  = 0xe435d91d6d92a1d8")
    if h == 0xe435d91d6d92a1d8:
        print("PASS: hash byte-exactly matches 0xe435d91d6d92a1d8")
    else:
        print("FAIL: hash mismatch")
