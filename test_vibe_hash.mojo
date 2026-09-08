# test_vibe_hash.mojo — Vibe-code test for quilt_vibe.mojo
# Verifies the byte-exact hash 0xe435d91d6d92a1d8

from quilt_vibe import Cell, Fabric, state_hash, SIMD, List, Int16, Int64, UInt64

fn main():
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
    assert(h == 0xe435d91d6d92a1d8, "hash mismatch")
    print("test_hash: OK")
