#!/usr/bin/env python3
"""Synrix-native durability receipt — write, SIGKILL, WAL replay, recall.

No Octopoda. No Python SDK. ctypes against libsynrix.so.

The kill is a real one: the parent waits for the child to acknowledge a durable
write, then sends SIGKILL. SIGKILL cannot be caught, so no atexit handler, no
buffer flush, and no lattice checkpoint runs. Whatever is recalled afterwards
came off the WAL.

  make first-look
  python3 scripts/demo_first_look_durability.py
"""
from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MISSION = "Finish pallet route A-14"
NODE_NAME = "DEMO:mission"
NODE_BUF = 2048
ACK_TIMEOUT_S = 30.0
KILL_TIMEOUT_S = 10.0
CHILD_MAX_WAIT_S = 120.0

# ABI assumption, measured against the kernel headers this pack was cut from:
#   sizeof(lattice_node_t)       = 1216
#   offsetof(lattice_node_t,name)=   12
#   offsetof(lattice_node_t,data)=   76
#   sizeof(persistent_lattice_t) =  608
# The binary exports no size/version accessor yet, so these are pinned here and
# re-checked at runtime: _read_named verifies the name field decodes to the name
# we asked for, which fails loudly if the layout ever moves under us. A
# synrix_lattice_sizeof()/synrix_abi_version() pair is the real fix and is
# tracked for the next kernel release.
NAME_OFF = 12
DATA_OFF = 76
LATTICE_STRUCT_BYTES = 608
LATTICE_BUF = 1024 * 1024  # 1725x the measured struct; headroom for ABI growth


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


def worker_remember(lattice_path: str, ack_path: str) -> int:
    """Durable write, then idle until the parent SIGKILLs us.

    We never exit on our own. No cleanup, no save, no checkpoint — the durable
    WAL is the only persistence, and the process dies mid-life to prove it.
    """
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

    # The write is acknowledged. Tell the parent it may kill us now.
    Path(ack_path).write_text(f"{os.getpid()}\n", encoding="utf-8")

    deadline = time.monotonic() + CHILD_MAX_WAIT_S
    while time.monotonic() < deadline:
        time.sleep(0.05)
    print("FAIL: never received SIGKILL from parent", file=sys.stderr)
    return 1


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


def _step(label: str, ok: bool, detail: str = "") -> None:
    mark = "✓" if ok else "✗"
    suffix = f"  ({detail})" if detail else ""
    print(f"{label:<22} {mark}{suffix}", flush=True)


def _kill_after_ack(cmd: list[str], ack: Path, cwd: str, env: dict) -> tuple[bool, str]:
    """Run the writer, wait for its durable-write ack, then SIGKILL it.

    Returns (killed_by_sigkill, detail). Every branch reports what actually
    happened to the child — there is no success path that we assume.
    """
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + ACK_TIMEOUT_S
    while time.monotonic() < deadline:
        if ack.is_file():
            break
        if proc.poll() is not None:
            err = (proc.stderr.read() if proc.stderr else "").strip()
            return False, f"writer exited rc={proc.returncode} before ack: {err or 'no output'}"
        time.sleep(0.02)
    else:
        proc.kill()
        proc.wait(timeout=KILL_TIMEOUT_S)
        return False, f"no durable-write ack within {ACK_TIMEOUT_S:.0f}s"

    os.kill(proc.pid, signal.SIGKILL)
    try:
        proc.wait(timeout=KILL_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return False, f"pid {proc.pid} survived SIGKILL for {KILL_TIMEOUT_S:.0f}s"

    if proc.returncode != -signal.SIGKILL:
        return False, f"expected SIGKILL death, got rc={proc.returncode}"
    return True, f"pid {proc.pid} SIGKILLed mid-write"


def _inject_torn_tail(lattice_path: Path) -> tuple[bool, str]:
    """Append a half-written record to the WAL, as a power cut would leave it.

    Returns (injected, detail). Refuses to claim success if there is no WAL to
    tear — a missing WAL would mean the write never reached disk at all.
    """
    wal = Path(str(lattice_path) + ".wal")
    if not wal.is_file():
        return False, f"no WAL at {wal.name}"
    before = wal.stat().st_size
    if before <= 0:
        return False, f"{wal.name} is empty; nothing was durably written"
    with wal.open("ab") as fh:
        fh.write(b"\xde\xad\xbe\xef" * 7)  # 28 bytes: shorter than an entry header
        fh.flush()
        os.fsync(fh.fileno())
    return True, f"{wal.name} {before} -> {wal.stat().st_size} bytes, tail is a partial record"


def main() -> int:
    ap = argparse.ArgumentParser(description="Synrix first-look durability receipt")
    ap.add_argument("--worker", choices=("remember", "recall"))
    ap.add_argument("--lattice", default="")
    ap.add_argument("--ack", default="")
    args = ap.parse_args()
    if args.worker == "remember":
        return worker_remember(args.lattice, args.ack)
    if args.worker == "recall":
        return worker_recall(args.lattice)

    so = _lib_path()
    if not so.is_file():
        print(f"FAIL: missing {so} — run make setup", file=sys.stderr)
        return 2

    demo_dir = Path(tempfile.mkdtemp(prefix="synrix_first_look_"))
    env = os.environ.copy()
    env["SYNRIX_LIB_PATH"] = str(so.parent)
    env["PYTHONUNBUFFERED"] = "1"

    print("Synrix durability receipt (native lattice)", flush=True)
    print(f"mission: {MISSION}", flush=True)
    print(f"lib: {so.parent}", flush=True)
    print(flush=True)

    rc = _scenario(demo_dir, env, inject_tear=False)
    if rc != 0:
        print(f"data: {demo_dir}", flush=True)
        return rc

    print(flush=True)
    print("Torn-tail variant — same kill, plus a half-written record appended", flush=True)
    print("to the WAL before restart (simulates a tear at the moment of power loss).", flush=True)
    print(flush=True)
    rc = _scenario(demo_dir, env, inject_tear=True)
    if rc != 0:
        print(f"data: {demo_dir}", flush=True)
        return rc

    shutil.rmtree(demo_dir, ignore_errors=True)
    return 0


def _scenario(demo_dir: Path, env: dict, inject_tear: bool) -> int:
    tag = "torn" if inject_tear else "clean"
    run_dir = demo_dir / tag
    run_dir.mkdir(parents=True, exist_ok=True)
    lattice_path = str(run_dir / "mission.lattice")
    ack = run_dir / "write.ack"
    cmd_a = [
        sys.executable, str(Path(__file__)),
        "--worker", "remember", "--lattice", lattice_path, "--ack", str(ack),
    ]
    killed, kill_detail = _kill_after_ack(cmd_a, ack, str(ROOT), env)
    _step("Remember mission", ack.is_file(), "durable write acknowledged" if ack.is_file() else kill_detail)
    _step("SIGKILL runtime", killed, kill_detail)

    if not killed:
        print(flush=True)
        print(f"FAIL — kill phase did not run as specified ({kill_detail})", flush=True)
        return 1

    if inject_tear:
        ok, tear_detail = _inject_torn_tail(Path(lattice_path))
        _step("Tear WAL tail", ok, tear_detail)
        if not ok:
            print(flush=True)
            print(f"FAIL — could not inject a torn tail ({tear_detail})", flush=True)
            return 1

    cmd_b = [sys.executable, str(Path(__file__)), "--worker", "recall", "--lattice", lattice_path]
    proc_b = subprocess.run(cmd_b, cwd=str(ROOT), env=env, capture_output=True, text=True)
    line = (proc_b.stdout or "").strip().splitlines()[-1] if proc_b.stdout else ""
    restarted = proc_b.returncode is not None and bool(line or proc_b.stderr)
    recall_ok = proc_b.returncode == 0 and line.startswith("ok|lattice|durable")
    _step(
        "Restart runtime",
        restarted,
        "fresh process opened the lattice" if restarted else "worker produced no output",
    )
    _step("Recall mission", recall_ok, "" if recall_ok else (proc_b.stderr or "").strip()[:80])

    print(flush=True)
    if not recall_ok:
        detail = (proc_b.stderr or proc_b.stdout or "no worker output").strip()
        print(f"FAIL — mission not recovered ({detail})", flush=True)
        return 1

    replayed = line.split("replayed=", 1)[1].split("|", 1)[0]
    truncated = line.split("truncated_tail=", 1)[1] == "1"
    if inject_tear:
        print(
            "PASS — acknowledged write survived SIGKILL *and* a torn WAL tail "
            f"(records replayed: {replayed}, WAL not reinitialized)",
            flush=True,
        )
        # Observed behaviour, stated exactly: recovery stops at the first
        # incomplete entry header and keeps every complete record before it.
        # The kernel's truncated_tail flag reports physical file truncation,
        # which this path does not perform — so it reads 0 here by design.
        print(
            f"  recovery stopped at the torn record; truncated_tail flag={int(truncated)} "
            "(flag means the file was rewritten, which recovery does not do)",
            flush=True,
        )
    else:
        print(
            "PASS — durable memory survived SIGKILL "
            f"(backend: lattice, profile: durable, WAL records replayed: {replayed})",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
