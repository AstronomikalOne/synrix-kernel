#!/usr/bin/env python3
"""Pack-health checks for the public first-look binaries."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from check_demo_pack import REQUIRED_LIBS, WAL_SYMBOL, arch_libdir, has_wal_symbol

ROOT = Path(__file__).resolve().parents[1]


class TestDemoPack(unittest.TestCase):
    def test_required_list_is_libsynrix(self) -> None:
        self.assertEqual(REQUIRED_LIBS, ("libsynrix.so",))

    def test_missing_file_is_not_wal_ready(self) -> None:
        self.assertFalse(has_wal_symbol(ROOT / "no-such-libsynrix.so"))

    def test_aarch64_pack_exports_wal_when_present(self) -> None:
        so = ROOT / "lib" / "linux-aarch64" / "libsynrix.so"
        if not so.is_file():
            self.skipTest("no aarch64 pack in this clone")
        self.assertTrue(has_wal_symbol(so), f"{so} must export {WAL_SYMBOL}")

    def test_arch_libdir_name(self) -> None:
        self.assertTrue(arch_libdir().name.startswith("linux-"))

    def test_incomplete_libdir_fails_complete_check(self) -> None:
        script = ROOT / "scripts" / "check_demo_pack.py"
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, str(script), "--libdir", tmp, "--require-complete"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("pack incomplete", proc.stdout)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
