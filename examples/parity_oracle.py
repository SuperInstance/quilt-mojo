#!/usr/bin/env python3
"""examples/parity_oracle.py — Python oracle for the quilt-vibe case matrix.

Serialization/hashing mirrors reference_vibe.py byte-for-byte (struct.pack,
FNV-1a 64). Two serialization ORDER modes are provided:

  sorted     — reference canon: cells sorted by id (what reference_vibe.py does)
  insertion  — mirrors Mojo Dict.keys() iteration (insertion order), pinning
               the booked order-policy divergence for multi_unsorted

effect()/tick() mirror the Mojo semantics exactly: copy-mutate-writeback per
cell, in dict insertion order; neighbor reads see prior write-backs.

Output lines:  "PY <case> <sorted-hex> <insertion-hex>"  (equal values when
the two modes coincide).
"""
import struct
import sys

OFFSET = 0xcbf29ce484222325
PRIME = 0x100000001b3
MASK = 0xFFFFFFFFFFFFFFFF


def fnv1a_64(b: bytes) -> int:
    h = OFFSET
    for x in b:
        h ^= x
        h = (h * PRIME) & MASK
    return h


def serialize_cell(cell) -> bytes:
    out = bytearray()
    out.append(0x01)  # type
    out += struct.pack("<Q", cell["id"])
    for d in cell["dials"]:
        out += struct.pack("<h", d)
    for n in cell["neighbors"]:
        out += struct.pack("<Q", n)
    return bytes(out)


def state_hash(cells: dict, mode: str = "sorted") -> int:
    all_bytes = bytearray()
    ids = sorted(cells) if mode == "sorted" else list(cells)  # dict = insertion order
    for cid in ids:
        all_bytes += serialize_cell(cells[cid])
    return fnv1a_64(bytes(all_bytes))


def make_dials(start: int, step: int) -> list:
    return [start + step * i for i in range(16)]


def cell(cid: int, dials: list, neighbors: list) -> dict:
    return {"id": cid, "dials": dials, "neighbors": list(neighbors)}


def effect(cells: dict) -> None:
    for cid in list(cells.keys()):
        c = cells[cid]
        total = 0
        for n in c["neighbors"]:
            if n in cells:
                total += cells[n]["dials"][0]
        if len(c["neighbors"]) > 0:
            c["dials"][0] = total // len(c["neighbors"])  # Python // floors; Mojo // floors too (verified)


def tick(cells: dict) -> None:
    for cid in list(cells.keys()):
        c = cells[cid]
        direction = 1 if (cid + len(c["dials"])) % 2 == 0 else -1
        c["dials"] = [d + direction for d in c["dials"]]


def case_canonical():
    return {1: cell(1, make_dials(1, 1), [2, 3, 4])}


def case_empty():
    return {}


def case_zeros():
    return {0: cell(0, make_dials(0, 0), [])}


def case_extremes():
    return {7: cell(7, make_dials(-32768, 1), [1])}


def case_bigint():
    return {123456789: cell(123456789, make_dials(32767, -1), [1099511627776, 2])}


def _multi_cells():
    return {
        10: cell(10, make_dials(1, 1), []),
        20: cell(20, make_dials(2, 2), []),
        30: cell(30, make_dials(0, -1), []),
    }


def _link(cells: dict, a: int, b: int) -> None:
    if a in cells:
        cells[a]["neighbors"].append(b)
    if b in cells:
        cells[b]["neighbors"].append(a)


def case_multi_sorted():
    cells = _multi_cells()
    _link(cells, 10, 20)
    _link(cells, 10, 30)
    _link(cells, 20, 30)
    return cells


def case_multi_unsorted():
    # identical cells/links to multi_sorted, inserted 30, 10, 20
    cells = {
        30: cell(30, make_dials(0, -1), []),
        10: cell(10, make_dials(1, 1), []),
        20: cell(20, make_dials(2, 2), []),
    }
    _link(cells, 10, 20)
    _link(cells, 10, 30)
    _link(cells, 20, 30)
    return cells


def case_tick_effect():
    cells = {
        5: cell(5, make_dials(1, 1), []),
        6: cell(6, make_dials(100, -1), []),
    }
    _link(cells, 5, 6)
    for _ in range(3):
        tick(cells)
    for _ in range(2):
        effect(cells)
    return cells


CASES = [
    ("canonical", case_canonical, "ids=[1] dials=1..16 nbrs=[2,3,4]"),
    ("empty", case_empty, "no cells (hash of empty byte string)"),
    ("zeros", case_zeros, "ids=[0] dials=0x16 nbrs=[] (degenerate)"),
    ("extremes", case_extremes, "ids=[7] dials=-32768..-32753 nbrs=[1 dangling]"),
    ("bigint", case_bigint, "ids=[123456789] dials=32767..32752 nbrs=[2^40,2 dangling]"),
    ("multi_sorted", case_multi_sorted, "ids=10,20,30 asc; dials 1..16 / 2..32 / 0..-15; links 10-20,10-30,20-30"),
    ("multi_unsorted", case_multi_unsorted, "same fabric as multi_sorted, inserted 30,10,20"),
    ("tick_effect", case_tick_effect, "ids=5,6; dials 1..16 / 100..85; link 5-6; 3x tick, 2x effect"),
]


def main() -> int:
    # self-check: the oracle must reproduce the pinned canonical constant
    h = state_hash(case_canonical())
    assert h == 0xE435D91D6D92A1D8, f"oracle self-check failed: {h:#x}"
    print(f"ORACLE self-check canonical 0x{h:016x} OK")
    for name, fn, spec in CASES:
        cells = fn()
        hs = state_hash(cells, "sorted")
        hi = state_hash(cells, "insertion")
        print(f"INPUT {name} {spec}")
        print(f"PY {name} {hs:016x} {hi:016x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
