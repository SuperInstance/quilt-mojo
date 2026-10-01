#!/usr/bin/env python3
"""examples/run_demo.py — end-to-end parity driver / receipt printer.

Runs examples/demo.mojo (Mojo side) and examples/parity_oracle.py (Python
side) on the identical case matrix and prints a receipt: inputs, hashes,
and PASS/FAIL per case vs the Python canon (sorted serialization order).

The known multi_unsorted divergence is a BOOKED finding: Mojo serializes
cells in Dict insertion order; the Python reference canonicalizes by id.
The receipt shows it as DIVERGENCE (booked) and additionally verifies that
the Mojo bytes match the insertion-order oracle exactly — isolating the
divergence to serialization ORDER, not byte format.

Usage:
  python3 examples/run_demo.py
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB = "/home/eileen/projects/quilt-mojo-lab"
PIXI = "/home/eileen/.pixi/bin/pixi"

BOOKED_DIVERGENCE = {"multi_unsorted"}


def run(cmd: list, cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def main() -> int:
    # --- Mojo side (flags BEFORE the source file: flag order matters) ---
    mojo = run(
        [PIXI, "run", "mojo", "-I", REPO, "-D", "ASSERT=all",
         os.path.join(REPO, "examples", "demo.mojo")],
        LAB,
    )
    if mojo.returncode != 0:
        print("MOJO RUN FAILED (rc=%d)" % mojo.returncode)
        print(mojo.stdout)
        print(mojo.stderr)
        return 1

    # --- Python side ---
    oracle = run([sys.executable, os.path.join("examples", "parity_oracle.py")], REPO)
    if oracle.returncode != 0:
        print("ORACLE FAILED (rc=%d)" % oracle.returncode)
        print(oracle.stdout)
        print(oracle.stderr)
        return 1

    mojo_hashes = {}
    for line in mojo.stdout.splitlines():
        if line.startswith("MOJO "):
            _, name, hx = line.split()
            mojo_hashes[name] = hx

    py_hashes, inputs = {}, {}
    for line in oracle.stdout.splitlines():
        parts = line.split()
        if parts[0] == "PY":
            py_hashes[parts[1]] = (parts[2], parts[3])  # (sorted, insertion)
        elif parts[0] == "INPUT":
            inputs[parts[1]] = " ".join(parts[2:])

    print("=" * 78)
    print("QUILT-MOJO VIBE PARITY RECEIPT")
    print("toolchain: Mojo 1.2.0.dev2026100105 (pixi, quilt-mojo-lab)")
    print("oracle   : examples/parity_oracle.py (reference_vibe.py serialization)")
    print("=" * 78)

    n_pass = n_booked = n_fail = 0
    for name in inputs:
        mj = mojo_hashes.get(name, "MISSING")
        hs, hi = py_hashes[name]
        print(f"\ncase    : {name}")
        print(f"inputs  : {inputs[name]}")
        print(f"mojo    : 0x{mj}")
        print(f"py-sorted (canon): 0x{hs}")
        if name in BOOKED_DIVERGENCE:
            print(f"py-insertion     : 0x{hi}")
            if mj == hi and mj != hs:
                print("verdict: DIVERGENCE (BOOKED) — byte format matches insertion-order")
                print("         oracle exactly; differs from sorted canon ONLY in")
                print("         serialization order (Mojo Dict insertion vs sorted id).")
                n_booked += 1
            elif mj == hs:
                print("verdict: PASS (canon) — insertion order happened to equal sorted order")
                n_pass += 1
            else:
                print("verdict: FAIL — mismatch vs BOTH oracle modes (byte-format bug)")
                n_fail += 1
        else:
            verdict = "PASS" if mj == hs else "FAIL"
            print(f"verdict : {verdict} (bit-for-bit vs Python canon)")
            n_pass += verdict == "PASS"
            n_fail += verdict == "FAIL"

    print("\n" + "=" * 78)
    print(f"SUMMARY: {n_pass} PASS, {n_booked} booked divergence, {n_fail} FAIL "
          f"of {len(inputs)} cases")
    print("parity contract: re-verify with  python3 examples/run_demo.py")
    print("=" * 78)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
