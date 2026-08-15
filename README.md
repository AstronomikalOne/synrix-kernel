# Synrix — receipt-backed agent-state kernel (first look)

**Other memory systems try to improve what an agent remembers. Synrix makes committed agent state survive predictably — and makes that behavior independently observable.**

Not a compliance platform. Not cloud memory. Not a chatbot SDK. Not a second SQLite. Not an extraction/RAG memory product.

We sit **under** the semantic-memory layer. They decide what the agent should remember. We answer what was actually committed, what survived failure, and what evidence demonstrates that — against the exact binary and hardware running it.

One-pager: [`docs/gtm/SYNRIX_OEM_ONE_PAGER.md`](docs/gtm/SYNRIX_OEM_ONE_PAGER.md) · Positioning: [`docs/gtm/POSITIONING.md`](docs/gtm/POSITIONING.md)

---

## Principle: no observation → no claim

There are no pre-computed benchmark files here. A JSON result you did not produce
tells you nothing about your hardware.

Everything below is measured by `libsynrix.so` in this repo, on your machine, at
the moment you run it. If a check cannot be measured on your platform, you get
an honest refusal and **no receipt**. That refusal is the product behaving
correctly, not a missing feature.

---

## First look

```bash
git clone https://github.com/AstronomikalOne/synrix-kernel
cd synrix-kernel
make first-look
```

On **aarch64** (Jetson-class) this runs three checks and writes a receipt to
`receipts/generated/`:

1. **Clean hard kill.** A child process writes under durable sync and signals
   the write was acknowledged. The parent sends `SIGKILL` — uncatchable, so no
   handler, no flush, no checkpoint. The kill is post-ACK, pre-clean-exit. The
   demo verifies no file exists at the expected snapshot path; WAL replay is
   observed; destroying the WAL causes loss. A fresh process replays and
   recalls the value.
2. **Injected incomplete WAL tail.** Same kill, then 28 bytes are appended and
   fsynced before restart. Recovery stops at the fragment and keeps every
   complete record before it, without reinitializing. This is not a power-cut
   simulation.
3. **Insertion-order set integrity.** 2000 nodes inserted in natural order, then
   again under shuffle seed 12345. The returned set is complete and exact —
   nothing dropped, duplicated, or invented, payloads intact. Not retrieval;
   not churn.

Every printed check derives from an observed condition. The kill is confirmed by
exit status `-SIGKILL`, not assumed.

On **x86_64** the shipped binary cannot measure durability, so `make first-look`
says so and writes nothing. There is no receipts-only fallback path.

---

## The receipt is the product

```bash
make receipt
```

Not `write() returned success`. A receipt is: on this device, against this
binary, this acknowledged operation survived this failure scenario, under this
harness, and here is the evidence.

It records binary SHA-256 and GNU build ID, board model, SoC, kernel and L4T
release, power mode, libc, page size, SHA-256 of every harness source, the exact
command, every observed value including failures, and an explicit `claims` block
listing what the run does *not* establish.

Call this **receipt-backed durability**, not a proof. Device-key signing (chain
of custody an auditor files) is the next release. Receipts are gitignored.
Yours should come from your hardware.

---

## What this does not claim

- **Ordered-sequence equality under reordering is not claimed.** Queries return
  nodes in insertion order, so sequences differ between builds by design. The
  claim is set completeness and exactness, which is narrower.
- **No retrieval, recall, or latency numbers.** This repo measures durability
  and set integrity. Nothing else.
- **WAL is not the differentiator.** Storage engines already have one. The
  offer is the failure contract, the implementation, and the falsification
  tests, shipped together.
- **Not “AI memory.”** Extraction, RAG, and personalization live in the layer
  above. This is **agent state**: what was committed and what survived.
- **Short runs only.** Nothing here speaks to sustained thermal behaviour.
- **The binary you hashed is the only one described.** Nothing generalizes to
  other builds.

---

## Verify it can fail

A durability demo that cannot fail is decoration.

```bash
make test
```

`scripts/test_durability_harness.py` deletes the WAL, zeroes the WAL, and
asserts that no snapshot exists at kill time. If any of those let the demo pass,
the test fails.

---

## Why not SQLite?

SQLite is excellent on-device storage — free, battle-tested, and enough when you
only need durable rows. A capable team can also build durability contracts,
failure injection, and evidence generation around it. Teams do.

Synrix is that layer, already built and versioned as one component. The offer is
the NRE you skip and the failure modes you meet in a test suite instead of in the
field. Full paragraph: [`docs/gtm/SQLITE_OBJECTION.md`](docs/gtm/SQLITE_OBJECTION.md).

Device-key signing of receipts is the next release, not this demo. The public
ACK-can-lose vs durable-retains contrast is also roadmap.

---

## License

Proprietary. Non-commercial evaluation use only.

**Contact:** Ryan Barkley · [xdeviantxmindx@gmail.com](mailto:xdeviantxmindx@gmail.com)

Native library source is not included. Pre-built binaries are provided for evaluation.
