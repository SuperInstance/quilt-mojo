# test_vibe_hash.mojo — Vibe-code test for quilt_vibe.mojo
# Verifies the byte-exact hash 0xe435d91d6d92a1d8
#
# 2026-09-30: mechanical drift fixes for Mojo 1.2.0.dev2026100105
# (prelude import quirk, implicit-copy removal). Run with:
#   pixi run mojo test_vibe_hash.mojo -D ASSERT=all
# (assert is a no-op without -D ASSERT=all on this toolchain).
# Original: test_vibe_hash.mojo.orig-20260930

from std import sys
from quilt_vibe import Cell, Fabric, state_hash

def main() raises:
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
    assert(h == 0xe435d91d6d92a1d8)
    print("test_hash: OK")
