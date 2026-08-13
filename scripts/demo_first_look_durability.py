#!/usr/bin/env python3
"""Synrix-native durability receipt — write, hard-kill, WAL replay, recall.

No Octopoda. No Python SDK. ctypes against libsynrix.so.

  make first-look
  python3 scripts/demo_first_look_durability.py
"""
from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MISSION = "Finish pallet route A-14"
NODE_NAME = "DEMO:mission"
LATTICE_BUF = 1024 * 1024
NODE_BUF = 2048
# lattice_node_t: id(8) + type(4) + name(64) + data(512) on aarch64/x86_64
NAME_OFF = 12
DATA_OFF = 76


def _lib_path() -> Path:
    raw = os.environ.get("SYNRIX_LIB_PATH", "")
    if raw:
        p = Path(raw)
        if p.is_file():
            return p.resolve()
        if p.is_dir():
            return (p / "libsynrix.so").resolve()
        return (ROOT / raw / "libsynrix.so").resolve()
    return (ROOT / "build" / "libsynrix.so").resolve()


def _load() -> ctypes.CDLL:
    so = _lib_path()
    if not so.is_file():
        print(f"FAIL: missing {so} — run make setup", file=sys.stderr)
        raise SystemExit(2)
    lib = ctypes.CDLL(str(so))
    if not hasattr(lib, "lattice_wal_get_recovery_stats"):
        print(
            f"FAIL: {so} has no lattice_wal_get_recovery_stats "
            "(need a current libsynrix, not the May 2026 demo binary)",
            file=sys.stderr,
        )
        raise SystemExit(2)
    lib.lattice_init.restype = ctypes.c_int
    lib.lattice_init.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
    ]
    lib.lattice_add_node.restype = ctypes.c_uint64
    lib.lattice_add_node.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_uint64,
    ]
    lib.lattice_find_nodes_by_name.restype = ctypes.c_uint32
    lib.lattice_find_nodes_by_name.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.c_uint32,
    ]
    lib.lattice_get_node_data.restype = ctypes.c_int
    lib.lattice_get_node_data.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint64,
        ctypes.c_void_p,
    ]
    lib.lattice_wal_get_recovery_stats.restype = ctypes.c_int
    lib.lattice_wal_get_recovery_stats.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_bool),
        ctypes.POINTER(ctypes.c_bool),
    ]
    return lib


def _apply_durable_env() -> None:
    os.environ["SYNRIX_SYNC_PROFILE"] = "durable"
    os.environ["SYNRIX_WAL_BATCH_SIZE"] = "0"
    os.environ["SYNRIX_WAL_ADAPTIVE"] = "0"
    os.environ["SYNRIX_WAL_ADAPTIVE_MIN_BATCH"] = "1"
    os.environ["SYNRIX_WAL_ADAPTIVE_MAX_BATCH"] = "1"
    os.environ["SYNRIX_WAL_SYNC_MODE"] = "fsync"


def _open(lib: ctypes.CDLL, path: str) -> ctypes.Array:
    buf = ctypes.create_string_buffer(LATTICE_BUF)
    rc = lib.lattice_init(buf, path.encode(), 1024, 0)
    if rc != 0:
        print(f"FAIL: lattice_init rc={rc}", file=sys.stderr)
        raise SystemExit(1)
    return buf


def _read_named(lib: ctypes.CDLL, lattice, name: str) -> str | None:
    ids = (ctypes.c_uint64 * 4)()
    n = lib.lattice_find_nodes_by_name(lattice, name.encode(), ids, 4)
    if n < 1 or ids[0] == 0:
        return None
    out = ctypes.create_string_buffer(NODE_BUF)
    if lib.lattice_get_node_data(lattice, ids[0], out) != 0:
        return None
    raw = out.raw
    stored = raw[NAME_OFF : NAME_OFF + 64].split(b"\x00", 1)[0].decode("utf-8", "replace")
    if stored != name:
        print(f"FAIL: storage name {stored!r} != {name!r}", file=sys.stderr)
        raise SystemExit(1)
    return raw[DATA_OFF : DATA_OFF + 512].split(b"\x00", 1)[0].decode("utf-8", "replace")


def worker_remember(lattice_path: str) -> int:
    _apply_durable_env()
    lib = _load()
    lat = _open(lib, lattice_path)
    nid = lib.lattice_add_node(lat, 1, NODE_NAME.encode(), MISSION.encode(), 0)
    if not nid:
        print("FAIL: add_node returned 0", file=sys.stderr)
        return 1
    got = _read_named(lib, lat, NODE_NAME)
    if got != MISSION:
        print(f"FAIL: immediate recall {got!r}", file=sys.stderr)
        return 1
    # No cleanup / save / checkpoint — durable WAL is the only persistence.
    os._exit(0)


def worker_recall(lattice_path: str) -> int:
    _apply_durable_env()
    lib = _load()
    lat = _open(lib, lattice_path)
    replayed = ctypes.c_uint32(0)
    truncated = ctypes.c_bool(False)
    reinitialized = ctypes.c_bool(False)
    rc = lib.lattice_wal_get_recovery_stats(
        lat, ctypes.byref(replayed), ctypes.byref(truncated), ctypes.byref(reinitialized)
    )
    if rc != 0:
        print("FAIL: WAL recovery stats unavailable", file=sys.stderr)
        return 1
    if int(replayed.value) <= 0:
        print(f"FAIL: WAL replayed={replayed.value}; snapshot is not accepted", file=sys.stderr)
        return 1
    if bool(reinitialized.value):
        print("FAIL: WAL was reinitialized during recovery", file=sys.stderr)
        return 1
    got = _read_named(lib, lat, NODE_NAME)
    if got != MISSION:
        print(f"FAIL: recall {got!r}", file=sys.stderr)
        return 1
    print(
        f"ok|lattice|durable|replayed={int(replayed.value)}|"
        f"truncated_tail={int(bool(truncated.value))}",
        flush=True,
    )
    return 0


def _step(label: str, ok: bool) -> None:
    print(f"{label:<22} {'✓' if ok else '✗'}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Synrix first-look durability receipt")
    ap.add_argument("--worker", choices=("remember", "recall"))
    ap.add_argument("--lattice", default="")
    args = ap.parse_args()
    if args.worker == "remember":
        return worker_remember(args.lattice)
    if args.worker == "recall":
        return worker_recall(args.lattice)

    so = _lib_path()
    if not so.is_file():
        print(f"FAIL: missing {so} — run make setup", file=sys.stderr)
        return 2

    demo_dir = Path(tempfile.mkdtemp(prefix="synrix_first_look_"))
    lattice_path = str(demo_dir / "mission.lattice")
    env = os.environ.copy()
    env["SYNRIX_LIB_PATH"] = str(so.parent)
    env["PYTHONUNBUFFERED"] = "1"

    print("Synrix durability receipt (native lattice)", flush=True)
    print(f"mission: {MISSION}", flush=True)
    print(f"lib: {so.parent}", flush=True)
    print(flush=True)

    cmd_a = [sys.executable, str(Path(__file__)), "--worker", "remember", "--lattice", lattice_path]
    rc_a = subprocess.call(cmd_a, cwd=str(ROOT), env=env)
    _step("Remember mission", rc_a == 0)
    _step("Kill runtime", rc_a == 0)

    cmd_b = [sys.executable, str(Path(__file__)), "--worker", "recall", "--lattice", lattice_path]
    proc_b = subprocess.run(cmd_b, cwd=str(ROOT), env=env, capture_output=True, text=True)
    line = (proc_b.stdout or "").strip().splitlines()[-1] if proc_b.stdout else ""
    recall_ok = proc_b.returncode == 0 and line.startswith("ok|lattice|durable")
    _step("Restart runtime", True)
    _step("Recall mission", recall_ok)

    print(flush=True)
    if recall_ok:
        replayed = line.split("replayed=", 1)[1].split("|", 1)[0]
        truncated = line.split("truncated_tail=", 1)[1]
        print(
            "PASS — durable memory survived restart "
            f"(backend: lattice, profile: durable, WAL replayed: {replayed}, "
            f"torn tail truncated: {'yes' if truncated == '1' else 'no'})",
            flush=True,
        )
        shutil.rmtree(demo_dir, ignore_errors=True)
        return 0

    detail = (proc_b.stderr or proc_b.stdout or "no worker output").strip()
    print(f"FAIL — mission not recovered ({detail})", flush=True)
    print(f"data: {demo_dir}", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
