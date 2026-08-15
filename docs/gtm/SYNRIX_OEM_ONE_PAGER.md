# Synrix — receipt-backed agent-state kernel (first look)

**Other memory systems try to improve what an agent remembers. Synrix makes committed agent state survive predictably — and makes that behavior independently observable.**

Not a compliance platform. Not cloud memory. Not a chatbot SDK. Not a second SQLite. Not an extraction/RAG memory product.

**Buyer:** OEM / air-gap integrator who already has counsel. We sit **under** the semantic-memory layer (Mem0, Letta, Zep, or yours) and make the persistence layer of *their* story true after the process dies. We are not a GRC aisle product.

Positioning: [`docs/gtm/POSITIONING.md`](POSITIONING.md)

---

## What you can verify in five minutes

This repo ships **no pre-computed numbers**. Everything is measured by the
binary in the repo, on your hardware, when you run it. **No observation → no
receipt.**

```bash
git clone https://github.com/AstronomikalOne/synrix-kernel
cd synrix-kernel && make first-look
```

| Check | What is asserted |
|-------|------------------|
| **ACK (unflushed witness)** | ACK has no durability guarantee. This lane (batch=50000, one op, immediate SIGKILL) expects the write **absent** — a witness of permitted loss, not “ACK must vanish.” |
| **DURABLE** | Same kill. State **survives** WAL replay. No file at the expected snapshot path. |
| **WAL delete / zero** | After DURABLE kill, deleting or zeroing that WAL leaves the mission absent. Observed by `make receipt`. |
| **Injected incomplete WAL tail** | DURABLE kill, then 28 bytes appended and fsynced. Recovery stops at the fragment. Not a power-cut simulation. |
| **Insertion-order set integrity** | The same 2000 nodes, two insert orders, complete exact set. Not retrieval. Not churn. |

`make receipt` writes binary SHA-256 and build ID, board, SoC, kernel, L4T,
power mode, harness hashes, command, every observed value (including failures),
and explicit `establishes` / `does_not_establish` boundaries.

That is **receipt-backed durability**, not a cryptographic proof. Device-key
signing is the next release.

---

## Stated scope

We would rather you trust a small claim than discover a large one was loose:

- **Ordered-sequence equality under reordering is not claimed.** Queries return
  insertion order, so sequences differ by design. The claim is set completeness.
- **No retrieval, recall, or latency numbers** are made in this pack.
- Short runs only — nothing about sustained thermal behaviour.
- Having a WAL is not the product. The product is the failure contract, the
  implementation, and the falsification tests, shipped together.

---

## Why not SQLite / RocksDB?

They are excellent stores. A capable team can build durability contracts,
failure injection, and evidence generation on top of them. Some do.

Synrix packages that layer for **agent state**: ACK may lose after `SIGKILL`,
DURABLE retains, recovery past an injected incomplete WAL tail, set completeness
when the same node set is inserted in two orders, and a receipt generated on
*this* binary and *this* hardware. Full paragraph:
[`SQLITE_OBJECTION.md`](SQLITE_OBJECTION.md).

The **ACK-can-lose vs durable-retains** contrast is in `make first-look`. Device-key
**signing** of receipts is the next release, not this demo.

---

## The demo can fail

`make test` deletes the WAL, zeroes the WAL, and asserts no snapshot exists at
kill time. If any of those let the demo pass, the test fails. A durability
demo that cannot fail is decoration.

---

## Design-partner ask

One OEM/integrator on Jetson-class (or similar). We shape embed + license to **your** stack.

**Contact:** Ryan Barkley · [xdeviantxmindx@gmail.com](mailto:xdeviantxmindx@gmail.com)
