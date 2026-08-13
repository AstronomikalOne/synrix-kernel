# Synrix — OEM memory kernel (first look)

**We're not your AI Act program — we're the part of the stack that can still tell the truth after the process dies.**

Deterministic, WAL-backed memory kernel for edge agents on Jetson-class hardware.  
Not a compliance platform. Not cloud memory. Not a chatbot SDK. Not a second SQLite.

One-pager: [`docs/gtm/SYNRIX_OEM_ONE_PAGER.md`](docs/gtm/SYNRIX_OEM_ONE_PAGER.md)

---

## Why not SQLite?

SQLite is excellent on-device storage — free, battle-tested, and enough when you only need durable rows. Synrix is for **agent-state workloads under audit pressure**: receipted durability (ACK vs OEM-durable), bit-identical behavior under controlled insert-order and churn tests, and hash-stamped, re-runnable evidence of what the agent still knew after hard kill. An auditor will not ask “did you have a database?” — they will ask “can you show synchronized survival semantics and a trusted record after failure?” SQLite does not productize that; Synrix does.

Device-key signing of those receipts is the next release, not this demo. Full paragraph: [`docs/gtm/SQLITE_OBJECTION.md`](docs/gtm/SQLITE_OBJECTION.md).

---

## First look

```bash
git clone https://github.com/AstronomikalOne/synrix-kernel
cd synrix-kernel
make first-look
```

Prints the one-pager and four hash-stamped receipts. On **aarch64** (Jetson-class) with a current `libsynrix.so`, it then runs live write → hard-kill → WAL replay → recall (`WAL replayed: N>0`). On **x86_64** (laptop / CI), live durability is a designed limit — same receipt hashes, exit 0, no FAIL banner. Receipts-only: `make first-look-receipts`.

---

## Numbers (receipted)

| Metric | Value |
|--------|-------|
| Label-hit Recall@10 | ~98.9% |
| Median native retrieval (C/NEON, warm-process) | ~25.5 µs |
| Work vs full scan | ~13% bytes |
| Insertion-order determinism | 2000/2000 ordered top-k identical |
| Streaming churn-parity | 2000/2000 ordered top-k identical |

No speedup-ratio headline. Commodity ANN also hits high recall at tiny byte fractions — the surviving differentiators are determinism and churn-parity. Hashes print from `make first-look`; receipts live in `receipts/first_look/`.

---

## License

Proprietary. Non-commercial evaluation use only. Contact for OEM licensing and integration.

Native library source is not included. Pre-built binaries are provided for evaluation.
