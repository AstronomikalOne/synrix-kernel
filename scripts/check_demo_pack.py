#!/usr/bin/env python3
"""Verify the arch-native demo pack. A PASS is only worth what it checks.

  python3 scripts/check_demo_pack.py --copy --require-libsynrix
  python3 scripts/check_demo_pack.py --copy --require-complete --require-wal
"""
from __future__ import annotations

import argparse
import ctypes
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_LIBS = ("libsynrix.so",)
WAL_SYMBOL = "lattice_wal_get_recovery_stats"


def arch_libdir(override: str | None = None) -> Path:
    if override:
        return Path(override).resolve()
    return ROOT / "lib" / f"linux-{platform.machine()}"


def has_wal_symbol(so: Path) -> bool:
    if not so.is_file():
        return False
    try:
        lib = ctypes.CDLL(str(so))
    except OSError:
        return False
    return hasattr(lib, WAL_SYMBOL)


def main() -> int:
    ap = argparse.ArgumentParser(description="Check synrix-demo native pack")
    ap.add_argument("--copy", action="store_true", help="Copy arch libs into build/")
    ap.add_argument("--libdir", default="", help="Override lib/linux-<arch> (tests)")
    ap.add_argument("--require-libsynrix", action="store_true")
    ap.add_argument("--require-complete", action="store_true")
    ap.add_argument("--require-wal", action="store_true")
    args = ap.parse_args()

    libdir = arch_libdir(args.libdir or None)
    if not libdir.is_dir():
        print(f"[FAIL] no pre-built libraries for {platform.machine()} (looked in {libdir})")
        return 1

    build = ROOT / "build"
    if args.copy:
        build.mkdir(parents=True, exist_ok=True)
        copied = 0
        for src in sorted(libdir.glob("*.so")):
            shutil.copy2(src, build / src.name)
            copied += 1
        print(f"[INFO] copied {copied} libraries from {libdir.relative_to(ROOT)} to build/")

    so = (build if args.copy else libdir) / "libsynrix.so"
    missing = []
    names = REQUIRED_LIBS if args.require_complete else (("libsynrix.so",) if args.require_libsynrix else ())
    base = build if args.copy else libdir
    for name in names:
        if not (base / name).is_file():
            missing.append(name)
    if missing:
        print(f"[FAIL] pack incomplete under {libdir}: missing {', '.join(missing)}")
        print(f"       expected in {libdir}: {', '.join(REQUIRED_LIBS)}")
        return 1

    wal = has_wal_symbol(so)
    print(f"[INFO] {so.name} {WAL_SYMBOL}={'yes' if wal else 'NO (stale May-era binary)'}")
    if args.require_wal and not wal:
        print(
            f"[FAIL] {so} is stale — rebuild libsynrix.so "
            f"(need {WAL_SYMBOL})"
        )
        return 1

    if args.require_complete or (args.require_libsynrix and args.require_wal):
        print("[OK] libsynrix.so present + current WAL symbol")
    elif args.require_libsynrix:
        print("[OK] libsynrix.so present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
