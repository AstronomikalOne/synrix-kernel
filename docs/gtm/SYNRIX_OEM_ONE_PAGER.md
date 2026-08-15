# Synrix — OEM memory kernel (first look)

**We're not your AI Act program — we're the part of the stack that can still tell the truth after the process dies.**

Deterministic, WAL-backed memory kernel for edge agents on Jetson-class hardware.  
Not a compliance platform. Not cloud memory. Not a chatbot SDK. Not “a second SQLite.”

**Buyer:** OEM / air-gap integrator who already has counsel. We make the persistence layer of *their* compliance story true. We are not a GRC aisle product.

---

## Why not SQLite?

SQLite is excellent on-device storage — free, battle-tested, and enough when you only need durable rows. And a capable team can build durability contracts, failure injection, and evidence generation on top of it. Some do.

Synrix is for **agent-state workloads under audit pressure**, and the offer is that you don't build that layer: retrieval semantics, order-invariant behavior under insert and churn, durable persistence with a receipted ACK-vs-durable contract, and the evidence artifacts — engineered, tested, and versioned as one component. What you're buying is the NRE you skip and the failure modes you don't meet in the field.

Device-key **signing** of those receipts (chain-of-custody an auditor files) is the next release, not this demo. Independent regeneration of the retrieval receipts is roadmap — see `docs/RECEIPTS.md` for what today's artifacts do and don't establish.

---

## Two surviving differentiators (receipted)

| Claim | Receipted result |
|--------|------------------|
| **Ordered top-k invariant** under insertion-order shuffle | **2000/2000** identical — HNSW control on the same test: **863/2000** (CWRU holdout, shuffle seed 12345) |
| **Streaming insert/delete at churn-parity** | Incremental vs batch rebuild: **2000/2000** ordered top-k identical; post-churn label-hit **~98.95%** |

Stated precisely: this is ordered top-k equivalence under one controlled shuffle seed, not bitwise-identical execution across builds, threads, or platforms. Multi-seed and cross-build coverage is roadmap. The control arm is what makes it a claim worth pressing on — the same test applied to HNSW returns a different ordering 57% of the time.

Commodity ANN also hits high recall at tiny byte fractions — we do **not** sell “we beat FAISS/HNSW on retrieval efficiency.”

---

## CWRU bearing-fault lane (credibility numbers)

| Metric | Value | Notes |
|--------|-------|--------|
| Label-hit **Recall@10** | **~98.9%** | Deployable adaptive filtration, 2000 held-out queries |
| Median native retrieval | **~25.5 µs** | C/NEON warm-process (not sustained thermal pack) |
| Work vs full scan | **~13%** | Same deployable policy; byte-fraction vs brute full scan |

No speedup-ratio headline. Work is byte-fraction vs full scan; latency stands alone. Not an ANN bake-off.

Receipts live in `receipts/first_look/` — path + hash printed by `make first-look`. These are artifacts from runs on the private research tree; the hashes pin the files, they do not re-derive the numbers. The durability test below is the part you run yourself.

---

## Durability (live on this box, aarch64)

Two scenarios, both executed on the evaluator's hardware:

1. **Clean hard kill.** Child process writes under **durable** sync, acknowledges, and the parent sends **`SIGKILL`** — uncatchable, so no handler, no flush, no checkpoint. No snapshot file exists on disk; the WAL is the only persistence. A fresh process replays and recalls.
2. **Torn tail.** Same kill, then a half-written record is appended to the WAL before restart. Recovery stops at the tear and keeps every complete record before it, without reinitializing.

Every printed check derives from an observed condition — the kill is confirmed by exit status `-SIGKILL`. `scripts/test_durability_harness.py` deletes and zeroes the WAL to prove the demo reports loss when loss occurs.

Still roadmap: the **ACK-can-lose vs durable-retains** contrast runs internally but is not yet in the public demo.

---

## Design-partner ask

One OEM/integrator on Jetson-class (or similar). We shape embed + license to **your** stack.

```bash
git clone https://github.com/AstronomikalOne/synrix-kernel
cd synrix-kernel && make first-look
```

**Contact:** Ryan Barkley · [xdeviantxmindx@gmail.com](mailto:xdeviantxmindx@gmail.com)
