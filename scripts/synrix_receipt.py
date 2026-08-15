#!/usr/bin/env python3
"""Generate a Synrix kernel receipt by running the checks, here, now.

This is not a file we ship and hash. It is produced on your machine, by your
copy of `libsynrix.so`, and it records enough identity that a second run
elsewhere can be compared against it: binary hash and build ID, board and SoC,
kernel and toolchain, the exact harness sources, and every observed value.

  make receipt

Everything in the `results` block is produced by this run. Nothing is copied
from a prior artifact. If a check fails, the receipt still writes and records
the failure. Each observation names its source (filesystem, child exit status,
or worker stdout marker).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from check_demo_pack import WAL_SYMBOL, has_wal_symbol  # noqa: E402
from demo_first_look_durability import run_durability  # noqa: E402
from demo_order_invariance import print_result, run_order_invariance  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "receipts" / "generated"
SCHEMA_VERSION = 1

# Every source file whose behaviour the results depend on. Hashed into the
# receipt so a reader can tell whether two receipts came from the same harness.
HARNESS_FILES = (
    "scripts/synrix_receipt.py",
    "scripts/demo_first_look_durability.py",
    "scripts/demo_order_invariance.py",
    "scripts/check_demo_pack.py",
)


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _first_line(path: str) -> str | None:
    try:
        return Path(path).read_text(errors="replace").strip().strip("\x00") or None
    except OSError:
        return None


def _cpu_model() -> str | None:
    try:
        text = Path("/proc/cpuinfo").read_text(errors="replace")
    except OSError:
        return None
    for key in ("model name", "Model", "Hardware", "CPU implementer"):
        m = re.search(rf"^{key}\s*:\s*(.+)$", text, re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


def _build_id(so: Path) -> str | None:
    """ELF GNU build-id, if the toolchain emitted one."""
    for cmd in (["readelf", "-n", str(so)], ["file", str(so)]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        m = re.search(r"Build ID: ([0-9a-f]+)", out) or re.search(r"BuildID\[sha1\]=([0-9a-f]+)", out)
        if m:
            return m.group(1)
    return None


def _elf_arch(so: Path) -> str | None:
    try:
        out = subprocess.run(["file", "-b", str(so)], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return out.strip() or None


def _jetson_power_mode() -> str | None:
    """nvpmodel profile, if this is a Jetson and the tool is present."""
    try:
        out = subprocess.run(["nvpmodel", "-q"], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"NV Power Mode:\s*(.+)", out)
    return m.group(1).strip() if m else None


def environment() -> dict:
    uname = platform.uname()
    return {
        "utc_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "board_model": _first_line("/proc/device-tree/model"),
        "cpu_model": _cpu_model(),
        "machine": uname.machine,
        "cpu_count": os.cpu_count(),
        "page_size": os.sysconf("SC_PAGESIZE") if hasattr(os, "sysconf") else None,
        "system": uname.system,
        "kernel_release": uname.release,
        "kernel_version": uname.version,
        "jetpack_l4t": _first_line("/etc/nv_tegra_release"),
        "power_mode": _jetson_power_mode(),
        "libc": " ".join(platform.libc_ver()).strip() or None,
        "python_version": platform.python_version(),
    }


def binary_identity(so: Path) -> dict:
    return {
        "path": str(so.relative_to(ROOT)) if so.is_relative_to(ROOT) else str(so),
        "sha256": sha256_file(so),
        "size_bytes": so.stat().st_size if so.is_file() else None,
        "build_id": _build_id(so),
        "elf": _elf_arch(so),
        "exports_wal_recovery_symbol": has_wal_symbol(so),
        "wal_symbol": WAL_SYMBOL,
    }


def harness_identity() -> dict:
    return {rel: sha256_file(ROOT / rel) for rel in HARNESS_FILES}


def _lane(durability: list, tag: str) -> dict:
    for row in durability or []:
        if row.get("scenario") == tag:
            return row
    return {}


def _obs(row: dict) -> str:
    parts = [
        f"acknowledged={row.get('write_acked')}",
        f"sigkill={row.get('killed_by_sigkill')}",
        f"recovered={row.get('state_recovered')}",
        f"timeout={bool(row.get('recovery_timeout'))}",
        f"passed={row.get('passed')}",
    ]
    if row.get("failure"):
        parts.append(f"failure={row['failure']}")
    return " ".join(parts)


def _claims(results: dict) -> dict:
    """Populate established only from successful observations. No observation → no claim."""
    durability = results.get("durability") or []
    order = results.get("order_invariance") or {}
    ack = _lane(durability, "ack_unflushed_loss_witness")
    durable = _lane(durability, "durable_sigkill")
    tail = _lane(durability, "durable_torn_tail")
    wal_del = _lane(durability, "wal_delete")
    wal_zero = _lane(durability, "wal_zero")

    established: list[str] = []
    not_established: list[str] = []

    if (
        ack.get("passed")
        and ack.get("write_acked")
        and ack.get("killed_by_sigkill")
        and ack.get("state_recovered") is False
        and not ack.get("recovery_timeout")
    ):
        established.append(
            "ACK has no durability guarantee. Unflushed witness (batch=50000, "
            "one op, SIGKILL immediately after ACK): acknowledged write absent."
        )
    elif ack:
        not_established.append(
            "ACK unflushed-loss witness: NOT ESTABLISHED. " + _obs(ack)
        )
    else:
        not_established.append("ACK unflushed-loss witness: NOT ESTABLISHED (lane missing).")

    if (
        durable.get("passed")
        and durable.get("write_acked")
        and durable.get("killed_by_sigkill")
        and durable.get("state_recovered")
        and not durable.get("recovery_timeout")
    ):
        established.append(
            "DURABLE: acknowledged write survived SIGKILL and was recovered "
            "by WAL replay in a fresh process."
        )
    elif durable:
        not_established.append("DURABLE SIGKILL survival: NOT ESTABLISHED. " + _obs(durable))
    else:
        not_established.append("DURABLE SIGKILL survival: NOT ESTABLISHED (lane missing).")

    if (
        tail.get("passed")
        and tail.get("state_recovered")
        and tail.get("tear_injected")
        and not tail.get("recovery_timeout")
    ):
        established.append(
            "DURABLE survival holds when an incomplete trailing WAL fragment "
            "is injected before restart."
        )
    elif tail:
        not_established.append("Incomplete-tail recovery: NOT ESTABLISHED. " + _obs(tail))
    else:
        not_established.append("Incomplete-tail recovery: NOT ESTABLISHED (lane missing).")

    wal_ok = (
        wal_del.get("passed")
        and wal_del.get("state_recovered") is False
        and not wal_del.get("recovery_timeout")
        and wal_zero.get("passed")
        and wal_zero.get("state_recovered") is False
        and not wal_zero.get("recovery_timeout")
    )
    if wal_ok:
        established.append(
            "No snapshot at the expected lattice path after DURABLE kill. "
            "Deleting that WAL, or zeroing it, leaves the mission absent."
        )
    else:
        bits = []
        if wal_del:
            bits.append("delete: " + _obs(wal_del))
        else:
            bits.append("delete: lane missing")
        if wal_zero:
            bits.append("zero: " + _obs(wal_zero))
        else:
            bits.append("zero: lane missing")
        not_established.append("WAL destroy causes loss: NOT ESTABLISHED. " + "; ".join(bits))

    if (
        order.get("passed")
        and order.get("set_identical")
        and order.get("matches_expected_set")
        and order.get("reference_duplicates") == 0
        and order.get("shuffled_duplicates") == 0
    ):
        established.append(
            "Node sets are complete and exact under insertion-order shuffle: "
            "nothing dropped, duplicated, or invented. Not retrieval; not churn."
        )
    elif order:
        not_established.append(
            "Insertion-order set integrity: NOT ESTABLISHED. "
            f"passed={order.get('passed')} set_identical={order.get('set_identical')} "
            f"matches_expected={order.get('matches_expected_set')}"
        )
    else:
        not_established.append("Insertion-order set integrity: NOT ESTABLISHED (lane missing).")

    return {
        "established": established,
        "not_established": not_established,
        "boundaries": [
            "Ordered-sequence equality under reordering. Queries return nodes in "
            "insertion order, so sequences differ by design.",
            "Retrieval quality, recall, or latency of any kind.",
            "Power-loss, write-ordering under sudden power removal, or torn-sector "
            "behaviour. The incomplete tail is injected after kill.",
            "That the binary wrote no other files anywhere on the filesystem.",
            "That ACK writes must disappear. ACK means no durability guarantee.",
            "Sustained thermal or multi-hour behaviour.",
            "Anything about builds other than the binary hashed above.",
        ],
        "reproduce": "make receipt",
    }


def build_receipt(so: Path) -> dict:
    print("Durability — ACK may lose, DURABLE retains, injected incomplete tail", flush=True)
    print(flush=True)
    durability = run_durability(so)

    print(flush=True)
    print("Insertion-order set integrity", flush=True)
    print(flush=True)
    order = run_order_invariance(so)
    print_result(order)

    results = {"durability": durability, "order_invariance": order}
    passed = all(r["passed"] for r in durability) and order["passed"]
    return {
        "schema_version": SCHEMA_VERSION,
        "receipt_type": "synrix_kernel_live",
        "generated_by": "scripts/synrix_receipt.py",
        "command": f"{Path(sys.executable).name} {' '.join(sys.argv)}",
        "environment": environment(),
        "binary": binary_identity(so),
        "harness": harness_identity(),
        "results": results,
        "claims": _claims(results),
        "passed": passed,
    }


def _libsynrix() -> Path:
    raw = os.environ.get("SYNRIX_LIB_PATH", "")
    if raw:
        p = Path(raw)
        if p.is_file():
            return p.resolve()
        return (p / "libsynrix.so").resolve()
    return (ROOT / "build" / "libsynrix.so").resolve()


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a live Synrix kernel receipt")
    ap.add_argument("--out", default=str(OUT_DIR / "synrix_kernel_receipt.json"))
    args = ap.parse_args()

    so = _libsynrix()
    if not so.is_file():
        print(f"FAIL: missing {so} — run make setup", file=sys.stderr)
        return 2
    if not has_wal_symbol(so):
        print(
            f"FAIL: {so} does not export {WAL_SYMBOL}, so durability cannot be\n"
            "      measured on this platform. A receipt asserting otherwise would\n"
            "      be worthless, so none is written. Run this on aarch64.",
            file=sys.stderr,
        )
        return 2

    receipt = build_receipt(so)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(flush=True)
    print("=" * 64, flush=True)
    print(f"receipt      {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}", flush=True)
    print(f"sha256       {sha256_file(out)}", flush=True)
    print(f"binary       {receipt['binary']['sha256']}", flush=True)
    print(f"build id     {receipt['binary']['build_id'] or '(none emitted)'}", flush=True)
    print(f"board        {receipt['environment']['board_model'] or receipt['environment']['cpu_model']}", flush=True)
    print(f"result       {'PASS' if receipt['passed'] else 'FAIL'}", flush=True)
    print("=" * 64, flush=True)
    print("Generated here, from this binary. Compare against another machine's", flush=True)
    print("receipt: the binary hash should match, the environment block should not.", flush=True)
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
