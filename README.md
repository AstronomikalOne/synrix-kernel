# Synrix — OEM memory kernel (first look)

**We're not your AI Act program — we're the part of the stack that can still tell the truth after the process dies.**

Deterministic, WAL-backed memory kernel for edge agents on Jetson-class hardware.  
Not a compliance platform. Not cloud memory. Not a chatbot SDK. Not a second SQLite.

One-pager: [`docs/gtm/SYNRIX_OEM_ONE_PAGER.md`](docs/gtm/SYNRIX_OEM_ONE_PAGER.md)

---

## Why not SQLite?

SQLite is excellent on-device storage — free, battle-tested, and enough when you only need durable rows. A capable team can also build durability contracts, failure injection, and evidence generation around it; teams do. The question is whether you want that on your roadmap.

Synrix ships those as one engineered component: retrieval semantics, deterministic behavior under insert-order and churn, durable persistence, and the evidence artifacts, tested together and versioned together. The sale is the NRE you don't do and the failure modes you don't discover in the field.

Device-key signing of those receipts is the next release, not this demo. Full paragraph: [`docs/gtm/SQLITE_OBJECTION.md`](docs/gtm/SQLITE_OBJECTION.md).

---

## First look

```bash
git clone https://github.com/AstronomikalOne/synrix-kernel
cd synrix-kernel
make first-look
```

Prints the one-pager and four receipts, then — on **aarch64** (Jetson-class) with a current `libsynrix.so` — runs the live durability test twice:

1. **Clean hard kill.** Child writes durably, acknowledges, parent sends `SIGKILL`. No snapshot exists on disk; the WAL is the only persistence. Fresh process replays and recalls.
2. **Torn tail.** Same kill, then a half-written record is appended to the WAL before restart. Recovery stops at the tear and keeps every complete record before it.

Every printed check derives from an observed condition — the kill is verified by exit status `-SIGKILL`, not assumed. `scripts/test_durability_harness.py` proves the demo can fail: delete or zero the WAL and it reports loss.

On **x86_64** (laptop / CI), live durability is a designed limit — receipts print, exit 0, no FAIL banner. Receipts-only: `make first-look-receipts`.

---

## Numbers (receipted)

| Metric | Value |
|--------|-------|
| Label-hit Recall@10 | ~98.9% |
| Median native retrieval (C/NEON, warm-process) | ~25.5 µs |
| Work vs full scan | ~13% bytes |
| Ordered top-k invariance under insertion-order shuffle | 2000/2000 — HNSW control on the same test: 863/2000 |
| Ordered top-k invariance, incremental vs batch build | 2000/2000 |

Read those last two precisely: **ordered top-k identical under one controlled shuffle seed (12345)**, not bitwise-identical execution across builds or platforms. The HNSW control arm is the point — it scores 43% on the test Synrix passes at 100%.

No speedup-ratio headline. Commodity ANN also hits high recall at tiny byte fractions — the surviving differentiator is order-invariance. Receipts live in `receipts/first_look/`; what they do and don't establish is in [`docs/RECEIPTS.md`](docs/RECEIPTS.md).

---

## License

Proprietary. Non-commercial evaluation use only.

**Contact:** Ryan Barkley · [xdeviantxmindx@gmail.com](mailto:xdeviantxmindx@gmail.com)

Native library source is not included. Pre-built binaries are provided for evaluation.
