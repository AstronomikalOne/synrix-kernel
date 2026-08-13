# Synrix — OEM memory kernel (first look)

**We're not your AI Act program — we're the part of the stack that can still tell the truth after the process dies.**

Deterministic, WAL-backed memory kernel for edge agents on Jetson-class hardware.  
Not a compliance platform. Not cloud memory. Not a chatbot SDK. Not “a second SQLite.”

**Buyer:** OEM / air-gap integrator who already has counsel. We make the persistence layer of *their* compliance story true. We are not a GRC aisle product.

---

## Why not SQLite?

SQLite is excellent on-device storage — free, battle-tested, and enough when you only need durable rows. Synrix is for **agent-state workloads under audit pressure**: a closed memory kernel with **receipted durability contracts** (fast ACK vs OEM-durable), **bit-identical / deterministic behavior** under controlled insert-order and churn tests, and **receipted mission evidence** — hash-stamped, re-runnable — of what the agent still knew after outage or hard kill. An EU AI Act / CRA-minded buyer will not ask “did you have a database?” — they will ask “can you show synchronized survival semantics and a trusted record of what remained true after failure?” SQLite does not productize that; Synrix does.

Device-key **signing** of those receipts (chain-of-custody an auditor files) is the next release, not this demo.

---

## Two surviving differentiators (receipted)

| Claim | Receipted result |
|--------|------------------|
| **Bit-identical determinism** across insertion-order shuffles | **2000/2000** ordered top-k identical (CWRU holdout) |
| **Streaming insert/delete at churn-parity** | Incremental vs batch rebuild: **2000/2000** ordered top-k identical; post-churn label-hit **~98.95%** |

These are the operational claims an auditor can press on. Commodity ANN also hits high recall at tiny byte fractions — we do **not** sell “we beat FAISS/HNSW on retrieval efficiency.”

---

## CWRU bearing-fault lane (credibility numbers)

| Metric | Value | Notes |
|--------|-------|--------|
| Label-hit **Recall@10** | **~98.9%** | Deployable adaptive filtration, 2000 held-out queries |
| Median native retrieval | **~25.5 µs** | C/NEON warm-process (not sustained thermal pack) |
| Work vs full scan | **~13%** | Same deployable policy; byte-fraction vs brute full scan |

No speedup-ratio headline. Work is byte-fraction vs full scan; latency stands alone. Not an ANN bake-off.

Receipts live in `receipts/first_look/` — path + hash printed by `make first-look`. Prefer **run it yourself** over slide trust.

---

## Durability (live on this box)

Remember → hard-kill process with **no close/save/checkpoint** → restart →
native WAL replay → recall under **durable** sync. PASS prints backend, profile,
replayed-entry count, and torn-tail disposition. Separate honesty clip:
**ACK can lose** after ACK; durable retains.

---

## Design-partner ask

One OEM/integrator on Jetson-class (or similar). We shape embed + license to **your** stack.

```bash
git clone https://github.com/AstronomikalOne/synrix-kernel
cd synrix-kernel && make first-look
```

**Contact:** Ryan Barkley · xdeviantxmindx@gmail.com
