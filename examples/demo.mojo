# examples/demo.mojo — end-to-end parity demo for quilt_vibe.mojo.
# Builds the case matrix (canonical + degenerate + multi-cell + tick/effect),
# prints one "MOJO <case> <hash-hex>" line per case. The Python oracle
# (examples/parity_oracle.py) computes the same cases; examples/run_demo.py
# runs both and prints the PASS/FAIL receipt.
#
# Run (flags BEFORE the source file — flag order matters on this nightly):
#   cd /home/eileen/projects/quilt-mojo-lab
#   pixi run mojo -I /home/eileen/projects/quilt-mojo examples/demo.mojo

from std import sys
from quilt_vibe import Cell, Fabric, state_hash, u64_hex


def dials_range(start: Int, step: Int) -> SIMD[DType.int16, 16]:
    var d = SIMD[DType.int16, 16]()
    for i in range(16):
        d[i] = Int16(start + step * i)
    return d


def case_canonical() raises -> Fabric:
    # id=1, dials 1..16, neighbors [2,3,4] — the pinned 0xe435d91d6d92a1d8
    var f = Fabric()
    var nbrs = List[UInt64]()
    nbrs.append(2)
    nbrs.append(3)
    nbrs.append(4)
    f.cells[1] = Cell(1, dials_range(1, 1), nbrs)
    return f^


def case_empty() raises -> Fabric:
    # no cells at all — hash of the empty byte string
    return Fabric()


def case_zeros() raises -> Fabric:
    # id=0, all-zero dials, no neighbors (degenerate)
    var f = Fabric()
    f.cells[0] = Cell(0, dials_range(0, 0), List[UInt64]())
    return f^


def case_extremes() raises -> Fabric:
    # id=7, int16-negative-extreme dials, one neighbor that does not exist
    var f = Fabric()
    var nbrs = List[UInt64]()
    nbrs.append(1)
    f.cells[7] = Cell(7, dials_range(-32768, 1), nbrs)
    return f^


def case_bigint() raises -> Fabric:
    # id=123456789, positive-extreme dials, big neighbor id + dangling neighbor
    var f = Fabric()
    var nbrs = List[UInt64]()
    nbrs.append(1099511627776)
    nbrs.append(2)
    f.cells[123456789] = Cell(123456789, dials_range(32767, -1), nbrs)
    return f^


def case_multi_sorted() raises -> Fabric:
    # three linked cells inserted in ASCENDING id order
    var f = Fabric()
    f.cells[10] = Cell(10, dials_range(1, 1), List[UInt64]())
    f.cells[20] = Cell(20, dials_range(2, 2), List[UInt64]())
    f.cells[30] = Cell(30, dials_range(0, -1), List[UInt64]())
    f.link(10, 20)
    f.link(10, 30)
    f.link(20, 30)
    return f^


def case_multi_unsorted() raises -> Fabric:
    # IDENTICAL cells and links to multi_sorted, inserted 30, 10, 20.
    # Probes the serialization-order policy: Mojo serializes in dict
    # insertion order; the Python reference canonicalizes by sorting ids.
    var f = Fabric()
    f.cells[30] = Cell(30, dials_range(0, -1), List[UInt64]())
    f.cells[10] = Cell(10, dials_range(1, 1), List[UInt64]())
    f.cells[20] = Cell(20, dials_range(2, 2), List[UInt64]())
    f.link(10, 20)
    f.link(10, 30)
    f.link(20, 30)
    return f^


def case_tick_effect() raises -> Fabric:
    # two linked cells, run 3 ticks + 2 effects, hash the result
    var f = Fabric()
    f.cells[5] = Cell(5, dials_range(1, 1), List[UInt64]())
    f.cells[6] = Cell(6, dials_range(100, -1), List[UInt64]())
    f.link(5, 6)
    for _i in range(3):
        f.tick()
    for _i in range(2):
        f.effect()
    return f^


def main() raises:
    var h: UInt64

    h = state_hash(case_canonical())
    print("MOJO canonical " + u64_hex(h))

    h = state_hash(case_empty())
    print("MOJO empty " + u64_hex(h))

    h = state_hash(case_zeros())
    print("MOJO zeros " + u64_hex(h))

    h = state_hash(case_extremes())
    print("MOJO extremes " + u64_hex(h))

    h = state_hash(case_bigint())
    print("MOJO bigint " + u64_hex(h))

    h = state_hash(case_multi_sorted())
    print("MOJO multi_sorted " + u64_hex(h))

    h = state_hash(case_multi_unsorted())
    print("MOJO multi_unsorted " + u64_hex(h))

    h = state_hash(case_tick_effect())
    print("MOJO tick_effect " + u64_hex(h))
