# Synrix — OEM memory kernel (first look)

**We're not your AI Act program — we're the part of the stack that can still tell the truth after the process dies.**

WAL-backed memory kernel for edge agents on Jetson-class hardware.
Not a compliance platform. Not cloud memory. Not a chatbot SDK. Not “a second SQLite.”

**Buyer:** OEM / air-gap integrator who already has counsel. We make the persistence layer of *their* compliance story true. We are not a GRC aisle product.

---

## What you can verify in five minutes

This repo ships **no pre-computed numbers**. Everything is measured by the
binary in the repo, on your hardware, when you run it:

```bash
git clone https://github.com/AstronomikalOne/synrix-kernel
cd synrix-kernel && make first-look
```

| Check | What is asserted |
|-------|------------------|
| **Clean hard kill** | An acknowledged durable write survives `SIGKILL` and is recovered by WAL replay in a fresh process. No snapshot exists at kill time, so the WAL is the only persistence. |
| **Torn WAL tail** | With a half-written record appended before restart, recovery stops at the tear and keeps every complete record before it, without reinitializing. |
| **Insertion-order set integrity** | 2000 nodes built in natural then shuffled order return a complete, exact set — nothing dropped, duplicated, or invented. |

`make receipt` writes the result with binary SHA-256 and build ID, board, SoC,
kernel, L4T, power mode, harness hashes, and every observed value.

---

## Stated scope

We would rather you trust a small claim than discover a large one was loose:

- **Ordered-sequence equality under reordering is not claimed.** Queries return
  insertion order, so sequences differ by design. The claim is set completeness.
- **No retrieval, recall, or latency numbers** are made in this pack.
- Short runs only — nothing about sustained thermal behaviour.

Retrieval work exists but is not part of this kernel pack and is not claimed here.

---

## Why not SQLite?

SQLite is excellent on-device storage — free, battle-tested, and enough when you only need durable rows. And a capable team can build durability contracts, failure injection, and evidence generation on top of it. Some do.

Synrix is for **agent-state workloads under audit pressure**, and the offer is that you don't build that layer: durable persistence with a receipted ACK-vs-durable contract, set-exact behaviour under churn, and the failure-injection harness that proves it — engineered, tested, and versioned as one component. What you're buying is the NRE you skip and the failure modes you don't meet in the field.

Device-key **signing** of receipts (chain-of-custody an auditor files) is the next release, not this demo.

---

## The demo can fail

`make test` deletes the WAL, zeroes the WAL, and asserts no snapshot exists at
kill time. If any of those let the demo pass, the test fails. A durability
demo that cannot fail is decoration.

Still roadmap: the **ACK-can-lose vs durable-retains** contrast runs internally
but is not yet in the public demo.

---

## Design-partner ask

One OEM/integrator on Jetson-class (or similar). We shape embed + license to **your** stack.

**Contact:** Ryan Barkley · [xdeviantxmindx@gmail.com](mailto:xdeviantxmindx@gmail.com)
