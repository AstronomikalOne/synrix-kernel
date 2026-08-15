#!/usr/bin/env python3
"""Synrix first-look — one-pager, then a receipt generated on your machine.

There is nothing here to take on trust. Every number this prints was measured
by the run that printed it, against the `libsynrix.so` in this repo.

  make first-look
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from check_demo_pack import has_wal_symbol

ROOT = Path(__file__).resolve().parents[1]
ONE_PAGER = ROOT / "docs/gtm/SYNRIX_OEM_ONE_PAGER.md"
SQLITE = ROOT / "docs/gtm/SQLITE_OBJECTION.md"


def _banner(title: str) -> None:
    print(flush=True)
    print("=" * 64, flush=True)
    print(title, flush=True)
    print("=" * 64, flush=True)


def show_one_pager() -> None:
    _banner("1 · ONE-PAGER")
    print(f"  file: {ONE_PAGER}")
    print(f"  sqlite gate: {SQLITE}")
    print()
    lines = ONE_PAGER.read_text(encoding="utf-8").strip().splitlines()
    for i, line in enumerate(lines):
        print(line)
        if i + 1 >= 32:
            print("  … (full page in docs/gtm/SYNRIX_OEM_ONE_PAGER.md)")
            break


def _libsynrix() -> Path:
    raw = os.environ.get("SYNRIX_LIB_PATH", "")
    if raw:
        p = Path(raw)
        if p.is_file():
            return p.resolve()
        return (p / "libsynrix.so").resolve()
    return (ROOT / "build" / "libsynrix.so").resolve()


def run_live() -> int:
    _banner("2 · LIVE — measured now, against this binary")
    print("  Synrix lattice only. No host runtime required.")
    print("  Writes receipts/generated/synrix_kernel_receipt.json.")
    print()
    return subprocess.call(
        [sys.executable, str(ROOT / "scripts/synrix_receipt.py")],
        cwd=str(ROOT),
    )


def show_designed_limit(so: Path) -> None:
    _banner("2 · LIVE — designed limit (not a FAIL)")
    print(f"  The binary for this architecture does not export WAL recovery stats:")
    print(f"    {so}")
    print("  Durability cannot be measured here, so no receipt is written. A")
    print("  receipt claiming otherwise would be worth nothing.")
    print()
    print("  This repo ships no pre-computed numbers to fall back on, by design.")
    print("  Run `make first-look` on aarch64 (Jetson-class) to see the evidence.")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description="Synrix first-look demo")
    ap.add_argument("--skip-live", action="store_true")
    args = ap.parse_args()

    print("SYNRIX · first look", flush=True)
    print("What it does · measured on your hardware · nothing else.", flush=True)

    show_one_pager()
    so = _libsynrix()
    live_rc = 0
    if args.skip_live:
        _banner("2 · LIVE (skipped)")
        print("  Re-run without --skip-live to generate a receipt.", flush=True)
    elif not has_wal_symbol(so):
        show_designed_limit(so)
    else:
        live_rc = run_live()

    _banner("CLOSE")
    print(
        '  "I\'m looking for one design partner to wire this into a real workload. '
        "If this looks useful, I'd want to scope a small pilot. "
        "If it looks like nonsense, tell me why — that's worth just as much to me.\"",
        flush=True,
    )
    print(flush=True)
    if live_rc == 0:
        print("  Run it yourself · not a source tour.", flush=True)
        return 0
    print("  Live durability failed — receipt records the failure.", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
