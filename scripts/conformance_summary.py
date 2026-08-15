#!/usr/bin/env python3
"""CI-facing conformance card from a generated receipt.

Always prints identity. Exit 0 only when the receipt exists and passed.
Missing file → no observation → no claim → FAIL.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "receipts" / "generated" / "synrix_kernel_receipt.json"


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    print("=" * 64)
    print("SYNRIX target-hardware conformance")
    print("=" * 64)
    if not path.is_file():
        print("receipt:           (none issued)")
        print("conformance:       FAIL")
        print("reason:            no observation — no receipt")
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    env = data.get("environment") or {}
    binary = data.get("binary") or {}
    claims = data.get("claims") or {}
    passed = bool(data.get("passed"))
    print(f"receipt:           {path}")
    print(f"schema/contract:   {data.get('schema_version')}")
    print(f"binary SHA-256:    {binary.get('sha256')}")
    print(f"binary build-id:   {binary.get('build_id')}")
    print(f"hardware:          {env.get('board_model') or env.get('cpu_model')}")
    print(f"machine:           {env.get('machine')}  cpus={env.get('cpu_count')}")
    print(f"kernel:            {env.get('kernel_release')}")
    l4t = (env.get("jetpack_l4t") or "").splitlines()
    print(f"L4T/JetPack:       {l4t[0] if l4t else None}")
    print(f"power mode:        {env.get('power_mode')}")
    print(f"established:       {len(claims.get('established') or [])}")
    print(f"not_established:   {len(claims.get('not_established') or [])}")
    print(f"conformance:       {'PASS' if passed else 'FAIL'}")
    for line in claims.get("not_established") or []:
        print(f"  not established: {line}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
