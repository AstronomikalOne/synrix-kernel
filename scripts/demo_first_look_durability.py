#!/usr/bin/env python3
"""Synrix-native durability receipt — write, SIGKILL, WAL replay, recall.

No Octopoda. No Python SDK. ctypes against libsynrix.so.

The kill is a real one: the parent waits for the child to acknowledge a durable
write, then sends SIGKILL. SIGKILL cannot be caught, so no atexit handler, no
buffer flush, and no lattice checkpoint runs. The kill is post-ACK,
pre-clean-exit — not mid-write.

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

    We never exit on our own. No cleanup, no save, no checkpoint. The process
    dies after the durable write has returned and been acknowledged.
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
    # Structured marker: parent must not treat stderr noise as a successful open.
    print("opened=1", flush=True)
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
        f"truncated_tail={int(bool(truncated.value))}|"
        f"reinitialized={int(bool(reinitialized.value))}",
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
    return True, f"pid {proc.pid} SIGKILLed post-ACK, pre-clean-exit"


def _inject_torn_tail(lattice_path: Path) -> tuple[bool, str]:
    """Append an incomplete trailing fragment to the WAL after the writer is dead.

    This is an injected incomplete WAL tail, not a power-cut simulation. It
    does not exercise sudden power removal, write-ordering under power loss, or
    torn-sector behaviour.

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

    print("Synrix durability receipt (native lattice)", flush=True)
    print(f"mission: {MISSION}", flush=True)
    print(f"lib: {so.parent}", flush=True)
    print(flush=True)

    results = run_durability(so)
    return 0 if results and all(r["passed"] for r in results) else 1


def _scenario(demo_dir: Path, env: dict, inject_tear: bool) -> dict:
    """Run one kill/recover scenario and return what was actually observed.

    Returns a plain dict so the same run can be printed for a human and written
    into a machine-checkable receipt. Nothing in here is inferred: every field
    is read back from the filesystem or from the child process's exit status.
    """
    tag = "torn_tail" if inject_tear else "clean_sigkill"
    run_dir = demo_dir / tag
    run_dir.mkdir(parents=True, exist_ok=True)
    lattice_path = Path(run_dir / "mission.lattice")
    wal_path = Path(str(lattice_path) + ".wal")
    ack = run_dir / "write.ack"

    obs: dict = {
        "scenario": tag,
        "sync_profile": "durable",
        "wal_sync_mode": "fsync",
        "wal_batch_size": 0,
        "written_value": MISSION,
        "node_name": NODE_NAME,
        "passed": False,
        "failure": None,
    }

    cmd_a = [
        sys.executable, str(Path(__file__)),
        "--worker", "remember", "--lattice", str(lattice_path), "--ack", str(ack),
    ]
    killed, kill_detail = _kill_after_ack(cmd_a, ack, str(ROOT), env)
    obs["durable_write_acked"] = ack.is_file()
    obs["killed_by_sigkill"] = killed
    obs["kill_detail"] = kill_detail
    # Expected lattice snapshot path. Absence here, plus WAL-destroy negative
    # controls, shows the WAL is load-bearing. It does not prove the binary
    # wrote nowhere else on the filesystem.
    obs["snapshot_file_present_at_kill"] = lattice_path.is_file()
    obs["wal_bytes_at_kill"] = wal_path.stat().st_size if wal_path.is_file() else None

    _step("Remember mission", obs["durable_write_acked"],
          "durable write acknowledged" if obs["durable_write_acked"] else kill_detail)
    _step("SIGKILL runtime", killed, kill_detail)
    if not killed:
        obs["failure"] = f"kill phase did not run as specified: {kill_detail}"
        print(flush=True)
        print(f"FAIL — {obs['failure']}", flush=True)
        return obs

    _step(
        "Expected snapshot absent",
        not obs["snapshot_file_present_at_kill"],
        f"no file at {lattice_path.name}; WAL is {obs['wal_bytes_at_kill']} bytes"
        if not obs["snapshot_file_present_at_kill"]
        else "snapshot present at expected path — WAL not shown load-bearing",
    )
    if obs["snapshot_file_present_at_kill"]:
        obs["failure"] = "a snapshot existed at the expected lattice path; WAL was not shown load-bearing"
        print(flush=True)
        print(f"FAIL — {obs['failure']}", flush=True)
        return obs

    if inject_tear:
        injected, tear_detail = _inject_torn_tail(lattice_path)
        obs["tear_injected"] = injected
        obs["tear_detail"] = tear_detail
        obs["wal_bytes_after_tear"] = wal_path.stat().st_size if wal_path.is_file() else None
        _step("Tear WAL tail", injected, tear_detail)
        if not injected:
            obs["failure"] = f"could not inject a torn tail: {tear_detail}"
            print(flush=True)
            print(f"FAIL — {obs['failure']}", flush=True)
            return obs

    cmd_b = [sys.executable, str(Path(__file__)), "--worker", "recall", "--lattice", str(lattice_path)]
    proc_b = subprocess.run(cmd_b, cwd=str(ROOT), env=env, capture_output=True, text=True)
    stdout_lines = [ln.strip() for ln in (proc_b.stdout or "").splitlines() if ln.strip()]
    opened = any(ln == "opened=1" for ln in stdout_lines)
    line = next((ln for ln in reversed(stdout_lines) if ln.startswith("ok|lattice|durable")), "")
    obs["lattice_opened"] = opened
    obs["restarted"] = opened
    obs["recall_matched_written_value"] = proc_b.returncode == 0 and bool(line)
    _step(
        "Restart runtime",
        opened,
        "fresh process opened the lattice" if opened else "no opened=1 marker after lattice_init",
    )
    _step("Recall mission", obs["recall_matched_written_value"],
          "" if obs["recall_matched_written_value"] else (proc_b.stderr or "").strip()[:80])

    print(flush=True)
    if not obs["recall_matched_written_value"]:
        obs["failure"] = (proc_b.stderr or proc_b.stdout or "no worker output").strip()
        print(f"FAIL — mission not recovered ({obs['failure']})", flush=True)
        return obs

    obs["wal_records_replayed"] = int(line.split("replayed=", 1)[1].split("|", 1)[0])
    obs["truncated_tail_flag"] = int(line.split("truncated_tail=", 1)[1].split("|", 1)[0])
    if "reinitialized=" in line:
        obs["wal_reinitialized"] = int(line.split("reinitialized=", 1)[1].split("|", 1)[0]) == 1
        obs["wal_reinitialized_source"] = "worker ok-line"
    else:
        obs["wal_reinitialized"] = None
        obs["wal_reinitialized_source"] = "absent from worker output"
    obs["passed"] = True

    if inject_tear:
        print(
            "PASS — acknowledged write survived SIGKILL *and* an injected incomplete WAL tail "
            f"(records replayed: {obs['wal_records_replayed']}, "
            f"reinitialized={int(bool(obs['wal_reinitialized']))})",
            flush=True,
        )
        # Observed behaviour, stated exactly: recovery stops at the first
        # incomplete entry header and keeps every complete record before it.
        # The kernel's truncated_tail flag reports physical file truncation,
        # which this path does not perform — so it reads 0 here by design.
        print(
            f"  recovery stopped at the incomplete fragment; truncated_tail flag="
            f"{obs['truncated_tail_flag']} (flag means the file was rewritten, "
            "which recovery does not do)",
            flush=True,
        )
    else:
        print(
            "PASS — durable memory survived SIGKILL "
            f"(backend: lattice, profile: durable, WAL records replayed: "
            f"{obs['wal_records_replayed']})",
            flush=True,
        )
    return obs


def run_durability(so: Path, env: dict | None = None) -> list[dict]:
    """Both scenarios, returning observations. Used by the demo and the receipt."""
    demo_dir = Path(tempfile.mkdtemp(prefix="synrix_first_look_"))
    run_env = dict(env or os.environ)
    run_env["SYNRIX_LIB_PATH"] = str(so.parent)
    run_env["PYTHONUNBUFFERED"] = "1"

    results = [_scenario(demo_dir, run_env, inject_tear=False)]
    if results[0]["passed"]:
        print(flush=True)
        print("Injected incomplete WAL tail — same kill, then 28 bytes appended", flush=True)
        print("and fsynced before restart. Not a power-cut simulation.", flush=True)
        print(flush=True)
        results.append(_scenario(demo_dir, run_env, inject_tear=True))

    if all(r["passed"] for r in results):
        shutil.rmtree(demo_dir, ignore_errors=True)
    else:
        print(f"data: {demo_dir}", flush=True)
    return results


if __name__ == "__main__":
    raise SystemExit(main())
