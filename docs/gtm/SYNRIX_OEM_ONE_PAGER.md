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
| **Clean hard kill** | An acknowledged durable write survives `SIGKILL` (post-ACK, pre-clean-exit) and is recovered by WAL replay in a fresh process. No file exists at the expected snapshot path. Destroying the WAL causes loss. |
| **Injected incomplete WAL tail** | After the same kill, 28 bytes are appended and fsynced. Recovery stops at the fragment and keeps every complete record before it, without reinitializing. Not a power-cut simulation. |
| **Insertion-order set integrity** | The same 2000 nodes, inserted in natural then shuffled order, return a complete, exact set — nothing dropped, duplicated, or invented. Not retrieval. Not churn. |

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

Synrix packages that layer for **agent state**: durable persistence under
`SIGKILL` after an acknowledged write, recovery past an injected incomplete WAL
tail, set completeness when the same node set is inserted in two orders, and a
receipt generated on *this* binary and *this* hardware. Full paragraph:
[`SQLITE_OBJECTION.md`](SQLITE_OBJECTION.md).

The **ACK-can-lose vs durable-retains** contrast is roadmap — this pack measures
the durable profile only.

---

## The demo can fail

`make test` deletes the WAL, zeroes the WAL, and asserts no snapshot exists at
kill time. If any of those let the demo pass, the test fails. A durability
demo that cannot fail is decoration.

---

## Design-partner ask

One OEM/integrator on Jetson-class (or similar). We shape embed + license to **your** stack.

**Contact:** Ryan Barkley · [xdeviantxmindx@gmail.com](mailto:xdeviantxmindx@gmail.com)
