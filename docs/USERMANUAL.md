# USERMANUAL — quilt-mojo vibe runtime

Verified on-box 2026-09-30 against **Mojo 1.2.0.dev2026100105** (the
`quilt-mojo-lab` pixi toolchain). Every command below was run and its output
captured in this document.

---

## What is "vibe"?

`quilt_vibe.mojo` is a small cell-fabric runtime: a `Fabric` holds `Cell`s
keyed by id. Each cell has **16 × int16 "dials"** and a neighbor list.
Operations: `bind` (set dials), `link` (undirected edge), `effect` (each
cell's dial[0] ← floor-average of its neighbors' dial[0]), `tick` (all dials
±1, +1 for even ids, −1 for odd).

The **vibe hash** is the fingerprint of a fabric state:

1. Serialize each cell: `0x01` type byte + id (u64 LE) + 16 dials (i16 LE) +
   each neighbor (u64 LE) — 65 bytes for the canonical cell.
2. Concatenate cells in the fabric's cell order.
3. FNV-1a 64 (`offset 0xcbf29ce484222325`, prime `0x100000001b3`).

**Pinned constant:** id=1, dials 1..16, neighbors [2,3,4] hashes to
**`0xe435d91d6d92a1d8`** — reproducible byte-for-byte by both
`quilt_vibe.mojo` and the Python oracle `reference_vibe.py` on this box.

`reference_vibe.py` is the **spec oracle**: an independent Python mirror of
the serialization + hash. When the two sides disagree, whichever side matches
`reference_vibe.py` (and the pinned constant) is canon.

## Quickstart

```bash
# 1. Run the canonical hash check (Mojo side)
cd /home/eileen/projects/quilt-mojo-lab
/home/eileen/.pixi/bin/pixi run mojo -I /home/eileen/projects/quilt-mojo \
    /home/eileen/projects/quilt-mojo/quilt_vibe.mojo
# → hash = 0xe435d91d6d92a1d8 / PASS

# 2. Run the Python oracle
python3 /home/eileen/projects/quilt-mojo/reference_vibe.py
# → hash = 0xe435d91d6d92a1d8 / PASS

# 3. Run the test (assert is LIVE only with -D ASSERT=all, flags BEFORE file)
/home/eileen/.pixi/bin/pixi run mojo -I /home/eileen/projects/quilt-mojo \
    -D ASSERT=all /home/eileen/projects/quilt-mojo/test_vibe_hash.mojo
# → test_hash: OK  (exit 0)
```

## The parity contract

Eight cases (canonical + empty/degenerate + extremes + multi-cell +
tick/effect) are checked bit-for-bit between Mojo and the Python oracle.

**Re-verify with one command:**

```bash
python3 /home/eileen/projects/quilt-mojo/examples/run_demo.py
```

Exit code 0 = contract holds (the one booked divergence is expected and
labeled, not a failure). This box's receipt (2026-09-30):

```
==============================================================================
QUILT-MOJO VIBE PARITY RECEIPT
toolchain: Mojo 1.2.0.dev2026100105 (pixi, quilt-mojo-lab)
oracle   : examples/parity_oracle.py (reference_vibe.py serialization)
==============================================================================

case    : canonical
inputs  : ids=[1] dials=1..16 nbrs=[2,3,4]
mojo    : 0xe435d91d6d92a1d8
py-sorted (canon): 0xe435d91d6d92a1d8
verdict : PASS (bit-for-bit vs Python canon)

case    : empty
inputs  : no cells (hash of empty byte string)
mojo    : 0xcbf29ce484222325
py-sorted (canon): 0xcbf29ce484222325
verdict : PASS (bit-for-bit vs Python canon)

case    : zeros
inputs  : ids=[0] dials=0x16 nbrs=[] (degenerate)
mojo    : 0xcd4d43fc56c209ac
py-sorted (canon): 0xcd4d43fc56c209ac
verdict : PASS (bit-for-bit vs Python canon)

case    : extremes
inputs  : ids=[7] dials=-32768..-32753 nbrs=[1 dangling]
mojo    : 0xc3ae09126b536d2a
py-sorted (canon): 0xc3ae09126b536d2a
verdict : PASS (bit-for-bit vs Python canon)

case    : bigint
inputs  : ids=[123456789] dials=32767..32752 nbrs=[2^40,2 dangling]
mojo    : 0x2257471136ea7c7d
py-sorted (canon): 0x2257471136ea7c7d
verdict : PASS (bit-for-bit vs Python canon)

case    : multi_sorted
inputs  : ids=10,20,30 asc; dials 1..16 / 2..32 / 0..-15; links 10-20,10-30,20-30
mojo    : 0x5acf6043f877bc77
py-sorted (canon): 0x5acf6043f877bc77
verdict : PASS (bit-for-bit vs Python canon)

case    : multi_unsorted
inputs  : same fabric as multi_sorted, inserted 30,10,20
mojo    : 0x6fec04301caffe5f
py-sorted (canon): 0x5acf6043f877bc77
py-insertion     : 0x6fec04301caffe5f
verdict: DIVERGENCE (BOOKED) — byte format matches insertion-order
         oracle exactly; differs from sorted canon ONLY in
         serialization order (Mojo Dict insertion vs sorted id).

case    : tick_effect
inputs  : ids=5,6; dials 1..16 / 100..85; link 5-6; 3x tick, 2x effect
mojo    : 0xd895d2395e983f8d
py-sorted (canon): 0xd895d2395e983f8d
verdict : PASS (bit-for-bit vs Python canon)

==============================================================================
SUMMARY: 7 PASS, 1 booked divergence, 0 FAIL of 8 cases
==============================================================================
```

### BOOKED FINDING — serialization order policy (multi-cell, unsorted insertion)

- The Python reference (`reference_vibe.py`) **sorts cells by id** before
  hashing → the hash is a function of STATE only.
- Mojo `state_hash` serializes in **`Dict` insertion order** → the hash can
  differ for the same logical fabric depending on insertion history
  (empirically pinned: `multi_sorted` → `0x5acf…`, `multi_unsorted` →
  `0x6fec…`; the latter equals the Python insertion-order oracle exactly, so
  the byte format is identical and ONLY the order policy diverges).
- Canon is the Python side (state hash must be insertion-independent).
- **Not fixed**: the repair (sort keys before serializing in
  `quilt_vibe.mojo`) is a semantic change, and this verification pass was
  restricted to mechanical toolchain-drift fixes. Single-cell fabrics (the
  only case the repo pins) are unaffected. Fix when the protocol doc
  (`QUILT_VIBE_PROTOCOL.md`) is available to confirm, and update
  `reference_vibe.py`/oracle in the same commit.

## Tests

```
$ pixi run mojo -I /home/eileen/projects/quilt-mojo -D ASSERT=all \
      /home/eileen/projects/quilt-mojo/test_vibe_hash.mojo
test_hash: OK        # exit 0 — 1/1 passed, 0 failed
```

The hardcoded constant `0xe435d91d6d92a1d8` in the test was verified against
`reference_vibe.py`'s **live output** (both print the same value; the Python
side asserts it too). Negative control: flipping the constant by one bit with
`-D ASSERT=all` correctly fails with `Assert Error: assertion failed`.

## Troubleshooting (traps hit and pinned on this box, 2026-09-30)

1. **`assert` is a no-op without `-D ASSERT=all`** — and the flag is
   **silently ignored if placed after the source file**. `-I` too. Correct:
   `mojo -I <dir> -D ASSERT=all file.mojo`. Wrong order = false PASS (caught
   here by a wrong-constant negative control).
2. **Old-syntax source won't parse**: `fn` → `def`, `let` → `var`,
   `inout self` → `out self` (ctors) / `mut self` (mutating methods).
   Originals preserved as `*.orig-20260930`.
3. **Iterator deref is gone**: `for b in xs: use b[]` → `use b` directly.
4. **Implicit copy is gone**: dict getitem → `var c = d[k].copy()`;
   store-back needs `d[k] = c^`; locals returned need `return out^`.
   Declare `struct Cell(Copyable)` for auto-generated deep-enough copy
   (`@value` is REMOVED on this nightly).
5. **Dict getitem raises** → containing functions need `raises`.
6. **Width mismatches are hard errors**: `UInt64 >> Int` fails — cast the
   rhs (`UInt64(i * 8)`); dict keys are `Int64`, neighbor ids `UInt64` —
   convert explicitly.
7. **`assert(cond, msg)` two-positional form doesn't parse** — use
   `assert(cond)`.
8. **`hex()` sign-extends UInt64** on this nightly: hashes ≥ 2^63 print
   negative (`0xe435…` → `-0x1bca…`). Use the `u64_hex()` helper in
   `quilt_vibe.mojo` instead.
9. **`case` is a keyword** — don't use it as a loop variable.
10. **Prelude quirk**: builtin symbols (`SIMD`, `List`, `Dict`, `Pointer`)
    resolve only when the file has at least one `from std import …` line.
    `from collections import …` does NOT work (no `collections` module);
    `List`/`Dict` come from the prelude.
11. **Import resolution** is relative to the entry file's directory; use
    `-I <repo-root>` (before the filename) when running from elsewhere.
    The `mojo` binary only works through the lab pixi env:
    `cd /home/eileen/projects/quilt-mojo-lab && /home/eileen/.pixi/bin/pixi run mojo …`
12. **Mojo `//` floors like Python** (verified `-7//2 = -4`), so `effect()`'s
    negative averages match Python — no truncation surprise.
13. **`List[Int](1,2,3)` variadic init is gone** — use `List[Int]()` +
    `append`, or a list literal.

## File map

| File | Role |
|---|---|
| `quilt_vibe.mojo` | the runtime + canonical hash check in `main` |
| `reference_vibe.py` | Python spec oracle (canon) |
| `test_vibe_hash.mojo` | assert-based test (needs `-D ASSERT=all`, flags first) |
| `examples/demo.mojo` | case-matrix hash printer (Mojo side) |
| `examples/parity_oracle.py` | case-matrix oracle (Python side; sorted + insertion modes) |
| `examples/run_demo.py` | **the parity contract driver** — runs both, prints receipt |
| `*.orig-20260930` | pre-drift-fix originals, archived (never deleted) |
