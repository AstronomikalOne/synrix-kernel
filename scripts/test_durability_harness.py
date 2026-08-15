#!/usr/bin/env python3
"""Failure-path checks for the hard-kill durability harness.

The point of these tests is not to watch the demo pass. It is to prove the demo
can fail: if we destroy the WAL, recall must report loss rather than quietly
printing a checkmark. A durability demo that cannot fail is decoration.

Skipped on platforms whose pack has no WAL recovery symbol (x86_64 today).
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_demo_pack import arch_libdir, has_wal_symbol  # noqa: E402
from demo_first_look_durability import (  # noqa: E402
    DATA_OFF,
    NAME_OFF,
    _inject_torn_tail,
)

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "scripts" / "demo_first_look_durability.py"
LIBDIR = arch_libdir()
LIVE = has_wal_symbol(LIBDIR / "libsynrix.so")


def _env() -> dict:
    env = os.environ.copy()
    env["SYNRIX_LIB_PATH"] = str(LIBDIR)
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _write_then_sigkill(tmp: Path) -> Path:
    """Durably write, wait for the ack, SIGKILL the writer. Returns the WAL."""
    lattice = tmp / "mission.lattice"
    ack = tmp / "write.ack"
    proc = subprocess.Popen(
        [sys.executable, str(DRIVER), "--worker", "remember",
         "--lattice", str(lattice), "--ack", str(ack)],
        cwd=str(ROOT), env=_env(), stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline and not ack.is_file():
        if proc.poll() is not None:
            raise AssertionError(f"writer exited early rc={proc.returncode}")
        time.sleep(0.02)
    os.kill(proc.pid, signal.SIGKILL)
    proc.wait(timeout=10.0)
    assert proc.returncode == -signal.SIGKILL, f"expected SIGKILL, got {proc.returncode}"
    return Path(str(lattice) + ".wal")


def _recall(lattice: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(DRIVER), "--worker", "recall", "--lattice", str(lattice)],
        cwd=str(ROOT), env=_env(), capture_output=True, text=True,
    )


@unittest.skipUnless(LIVE, "pack for this arch has no WAL recovery symbol")
class TestDurabilityFailurePaths(unittest.TestCase):
    def test_acknowledged_write_survives_sigkill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wal = _write_then_sigkill(Path(tmp))
            self.assertTrue(wal.is_file(), "durable write left no WAL")
            proc = _recall(wal.with_suffix(""))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("replayed=1", proc.stdout)

    def test_no_snapshot_is_written_before_kill(self) -> None:
        """The WAL must be the only persistence — otherwise the test is hollow."""
        with tempfile.TemporaryDirectory() as tmp:
            wal = _write_then_sigkill(Path(tmp))
            snapshot = Path(str(wal)[: -len(".wal")])
            self.assertFalse(snapshot.is_file(), "a snapshot existed; WAL was not load-bearing")

    def test_deleted_wal_is_reported_as_loss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wal = _write_then_sigkill(Path(tmp))
            wal.unlink()
            proc = _recall(wal.with_suffix(""))
            self.assertNotEqual(proc.returncode, 0, "deleted WAL must not pass")
            self.assertIn("replayed=0", proc.stderr)

    def test_zeroed_wal_is_reported_as_loss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wal = _write_then_sigkill(Path(tmp))
            wal.write_bytes(b"\x00" * wal.stat().st_size)
            proc = _recall(wal.with_suffix(""))
            self.assertNotEqual(proc.returncode, 0, "zeroed WAL must not pass")

    def test_torn_tail_still_recovers_acknowledged_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wal = _write_then_sigkill(Path(tmp))
            injected, detail = _inject_torn_tail(wal.with_suffix(""))
            self.assertTrue(injected, detail)
            proc = _recall(wal.with_suffix(""))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("replayed=1", proc.stdout)

    def test_full_harness_runs_both_scenarios(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(DRIVER)],
            cwd=str(ROOT), env=_env(), capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.count("SIGKILLed mid-write"), 2)
        self.assertIn("torn WAL tail", proc.stdout)


class TestHarnessInvariants(unittest.TestCase):
    """Checks that hold on every platform, live pack or not."""

    def test_tear_refuses_when_no_wal_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            injected, detail = _inject_torn_tail(Path(tmp) / "absent.lattice")
            self.assertFalse(injected)
            self.assertIn("no WAL", detail)

    def test_abi_offsets_match_measured_layout(self) -> None:
        """Pinned against the kernel headers this pack was cut from.

        If a future kernel moves these fields, this test fails here rather than
        the demo misreading node memory in front of a partner.
        """
        self.assertEqual(NAME_OFF, 12)
        self.assertEqual(DATA_OFF, 76)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
