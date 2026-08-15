#!/usr/bin/env python3
"""Synrix first-look — one-pager, hashed receipts, live WAL durability.

  make first-look
"""
from __future__ import annotations

import argparse
import hashlib
import json
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
RECEIPT_DIR = ROOT / "receipts/first_look"

RECEIPTS = [
    (
        "CWRU deployable Recall@10 ~98.9%",
        "aion_filtration_stage2_receipt.json",
        lambda d: (
            f"Recall@10={d['held_out']['filtration_adaptive_deployable']['recall_at10']}"
            f"  bytes_vs_full_scan_median="
            f"{d['held_out']['filtration_adaptive_deployable']['bytes_vs_full_scan_median']:.3f}"
        ),
    ),
    (
        "Native C/NEON median latency (warm-process)",
        "cwru_hnsw_gate1_receipt.json",
        lambda d: (
            f"p19 C/NEON p50={d['p19_reference']['native_c_neon_live']['p50_us']}µs"
            f"  (no speedup-ratio derived)"
        ),
    ),
    (
        "Ordered top-k invariance under insertion-order shuffle",
        "p19_determinism_receipt.json",
        lambda d: (
            f"synrix ordered_topk_identical="
            f"{d['p19']['shuffled_vs_reference']['ordered_topk_identical']}/"
            f"{d['p19']['shuffled_vs_reference']['n_queries']}  "
            f"vs HNSW control="
            f"{d['hnsw']['shuffled_order_vs_reference']['ordered_topk_identical']}/"
            f"{d['hnsw']['shuffled_order_vs_reference']['n_queries']}  "
            f"(single shuffle seed {d['identity']['shuffle_seed']})"
        ),
    ),
    (
        "Streaming insert/delete churn-parity",
        "p19_streaming_receipt.json",
        lambda d: (
            f"incremental_vs_batch ordered="
            f"{d['p19']['incremental_vs_batch_parity']['ordered_topk_identical']}/"
            f"{d['p19']['incremental_vs_batch_parity']['n_queries']}  "
            f"post_churn R@10={d['p19']['post_churn_recall_at10_incremental']}"
        ),
    ),
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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


def show_receipts() -> bool:
    _banner("2 · RECEIPTS (pre-computed — see docs/RECEIPTS.md for provenance)")
    print("  These are artifacts from runs on the private research tree, not")
    print("  regenerated here. The hashes pin the files; they do not re-derive")
    print("  the results. Independent regeneration is on the roadmap.")
    print("  Note: commodity HNSW/IVF also hit high recall at tiny byte fractions.")
    print("  Surviving differentiators below are determinism + churn-parity.")
    print("  Number rule: print receipt scalars only — never invent a × from division.")
    print()
    ok = True
    for label, fname, fmt in RECEIPTS:
        path = RECEIPT_DIR / fname
        if not path.is_file():
            print(f"  ✗ MISSING  {label}")
            print(f"             {path}")
            ok = False
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        digest = _sha256(path)[:16]
        print(f"  ✓ {label}")
        print(f"    {fmt(data)}")
        print(f"    receipt: {path.name}  sha256={digest}…")
        print()
    return ok


def _libsynrix() -> Path:
    raw = os.environ.get("SYNRIX_LIB_PATH", "")
    if raw:
        p = Path(raw)
        if p.is_file():
            return p.resolve()
        return (p / "libsynrix.so").resolve()
    return (ROOT / "build" / "libsynrix.so").resolve()


def run_live() -> int:
    _banner("3 · LIVE — write / hard-kill / restart / recall")
    print("  Synrix lattice only. No host runtime required.")
    print("  Partner: re-run `make first-look`.")
    print()
    return subprocess.call(
        [sys.executable, str(ROOT / "scripts/demo_first_look_durability.py")],
        cwd=str(ROOT),
    )


def show_designed_limit(so: Path) -> None:
    _banner("3 · LIVE — designed limit (not a FAIL)")
    print("  Live kill/recall requires a current libsynrix with WAL recovery stats.")
    print(f"  This pack's binary does not export that symbol: {so}")
    print("  Receipts above are the same hashes as the Jetson pack.")
    print("  Full write/kill/recall: run `make first-look` on aarch64 (Jetson-class).")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description="Synrix first-look demo")
    ap.add_argument("--skip-live", action="store_true")
    args = ap.parse_args()

    print("SYNRIX · first look", flush=True)
    print("What it does · how you know it's real · nothing else.", flush=True)

    show_one_pager()
    receipts_ok = show_receipts()
    so = _libsynrix()
    live_rc = 0
    if args.skip_live:
        _banner("3 · LIVE (skipped)")
        print("  Re-run without --skip-live for kill/recall.", flush=True)
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
    if receipts_ok and live_rc == 0:
        print("  Pack READY · run it yourself · not a source tour.", flush=True)
        return 0
    if not receipts_ok:
        print("  Receipt files missing — check receipts/first_look/.", flush=True)
    if live_rc != 0:
        print("  Live durability failed — see lib path / WAL symbol.", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
