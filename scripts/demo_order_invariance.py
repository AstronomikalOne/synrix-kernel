#!/usr/bin/env python3
"""Insertion-order behaviour of the shipped lattice, measured on your machine.

Builds the same node set twice — once in natural order, once shuffled under a
fixed seed — and compares what the kernel returns.

Read the result carefully, because it is deliberately not the strongest thing we
could claim. `lattice_find_nodes_by_type` returns nodes in insertion order, so
the *sequence* is expected to differ between the two builds. What is asserted
here is that the returned *set* is complete and exact under reordering: no node
dropped, none duplicated, none invented, and every payload intact.

That is a narrower claim than order-invariant retrieval, and it is stated
narrowly on purpose. It runs against the binary in this repo, on your hardware,
and it fails loudly if it does not hold.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import random
import sys
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME_OFF = 12
DATA_OFF = 76
NODE_TYPE = 1
LATTICE_BUF = 1024 * 1024
NODE_BUF = 2048
DEFAULT_N = 2000
DEFAULT_SEED = 12345


def _lib_path() -> Path:
    raw = os.environ.get("SYNRIX_LIB_PATH", "")
    if raw:
        p = Path(raw)
        if p.is_file():
            return p.resolve()
        return (p / "libsynrix.so").resolve()
    return (ROOT / "build" / "libsynrix.so").resolve()


def _load(so: Path) -> ctypes.CDLL:
    lib = ctypes.CDLL(str(so))
    lib.lattice_init.restype = ctypes.c_int
    lib.lattice_init.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint32,
    ]
    lib.lattice_add_node.restype = ctypes.c_uint64
    lib.lattice_add_node.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint64,
    ]
    lib.lattice_find_nodes_by_type.restype = ctypes.c_uint32
    lib.lattice_find_nodes_by_type.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_uint64), ctypes.c_uint32,
    ]
    lib.lattice_get_node_data.restype = ctypes.c_int
    lib.lattice_get_node_data.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_void_p]
    return lib


def _build_and_read(lib: ctypes.CDLL, order: list[int], names: list[str]) -> list[tuple[str, str]]:
    """Insert nodes in `order`, then read every node back as (name, payload)."""
    tmp = tempfile.mkdtemp(prefix="synrix_order_")
    try:
        buf = ctypes.create_string_buffer(LATTICE_BUF)
        rc = lib.lattice_init(buf, str(Path(tmp) / "order.lattice").encode(), len(names) * 2 + 64, 0)
        if rc != 0:
            raise SystemExit(f"FAIL: lattice_init rc={rc}")
        for i in order:
            if not lib.lattice_add_node(buf, NODE_TYPE, names[i].encode(), f"payload-{i}".encode(), 0):
                raise SystemExit(f"FAIL: add_node returned 0 for {names[i]}")

        cap = len(names) + 64
        ids = (ctypes.c_uint64 * cap)()
        found = lib.lattice_find_nodes_by_type(buf, NODE_TYPE, ids, cap)
        node = ctypes.create_string_buffer(NODE_BUF)
        out: list[tuple[str, str]] = []
        for j in range(found):
            if lib.lattice_get_node_data(buf, ids[j], node) != 0:
                raise SystemExit(f"FAIL: get_node_data failed for id {ids[j]}")
            raw = node.raw
            name = raw[NAME_OFF:NAME_OFF + 64].split(b"\x00", 1)[0].decode("utf-8", "replace")
            data = raw[DATA_OFF:DATA_OFF + 512].split(b"\x00", 1)[0].decode("utf-8", "replace")
            out.append((name, data))
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_order_invariance(so: Path, n: int = DEFAULT_N, seed: int = DEFAULT_SEED) -> dict:
    lib = _load(so)
    names = [f"DEMO:node{i:06d}" for i in range(n)]
    expected = {(names[i], f"payload-{i}") for i in range(n)}

    reference = _build_and_read(lib, list(range(n)), names)
    shuffled_order = list(range(n))
    random.Random(seed).shuffle(shuffled_order)
    shuffled = _build_and_read(lib, shuffled_order, names)

    ref_set, shuf_set = set(reference), set(shuffled)
    obs = {
        "check": "insertion_order_set_completeness",
        "n_nodes": n,
        "shuffle_seed": seed,
        "query": "lattice_find_nodes_by_type",
        "reference_returned": len(reference),
        "shuffled_returned": len(shuffled),
        "reference_duplicates": len(reference) - len(ref_set),
        "shuffled_duplicates": len(shuffled) - len(shuf_set),
        "set_identical": ref_set == shuf_set,
        "matches_expected_set": shuf_set == expected,
        "missing_after_shuffle": len(ref_set - shuf_set),
        "unexpected_after_shuffle": len(shuf_set - ref_set),
        # Stated, not hidden: ordering follows insertion, so the sequences differ.
        "ordered_identical": reference == shuffled,
        "ordering_semantics": "insertion order; sequence equality is NOT claimed",
    }
    obs["passed"] = bool(
        obs["set_identical"]
        and obs["matches_expected_set"]
        and obs["reference_returned"] == n
        and obs["shuffled_returned"] == n
        and obs["reference_duplicates"] == 0
        and obs["shuffled_duplicates"] == 0
    )
    return obs


def print_result(obs: dict) -> None:
    mark = "✓" if obs["passed"] else "✗"
    print(f"Nodes inserted         {obs['n_nodes']} (shuffle seed {obs['shuffle_seed']})", flush=True)
    print(f"Returned, natural order{obs['reference_returned']:>6}", flush=True)
    print(f"Returned, shuffled     {obs['shuffled_returned']:>6}", flush=True)
    print(f"Dropped / duplicated   {obs['missing_after_shuffle']} / "
          f"{obs['shuffled_duplicates']}", flush=True)
    print(flush=True)
    if obs["passed"]:
        print(f"{mark} PASS — set-complete and exact under reordering "
              f"({obs['n_nodes']}/{obs['n_nodes']} nodes, payloads intact)", flush=True)
        print("  Sequence order follows insertion and is expected to differ; "
              "this does not claim ordered equality.", flush=True)
    else:
        print(f"{mark} FAIL — reordering changed the returned set", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Lattice behaviour under insertion-order shuffle")
    ap.add_argument("--nodes", type=int, default=DEFAULT_N)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--json", action="store_true", help="emit observations as JSON")
    args = ap.parse_args()

    so = _lib_path()
    if not so.is_file():
        print(f"FAIL: missing {so} — run make setup", file=sys.stderr)
        return 2

    obs = run_order_invariance(so, n=args.nodes, seed=args.seed)
    if args.json:
        print(json.dumps(obs, indent=2))
    else:
        print_result(obs)
    return 0 if obs["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
