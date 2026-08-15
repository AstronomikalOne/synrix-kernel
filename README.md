# Synrix — OEM memory kernel (first look)

**We're not your AI Act program — we're the part of the stack that can still tell the truth after the process dies.**

WAL-backed memory kernel for edge agents on Jetson-class hardware.
Not a compliance platform. Not cloud memory. Not a chatbot SDK. Not a second SQLite.

One-pager: [`docs/gtm/SYNRIX_OEM_ONE_PAGER.md`](docs/gtm/SYNRIX_OEM_ONE_PAGER.md)

---

## This repo ships no numbers

There are no pre-computed benchmark files here, and that is deliberate. A JSON
result you did not produce tells you nothing about your hardware, and hashing it
only proves the file is still itself.

Everything below is measured by `libsynrix.so` in this repo, on your machine,
at the moment you run it. If a check cannot be measured on your platform, you
get an honest refusal instead of a fallback number.

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

## The receipt

```bash
make receipt
```

Records what a second machine would need to compare against: binary SHA-256 and
GNU build ID, board model, SoC, kernel and L4T release, power mode, libc, page
size, SHA-256 of every harness source, the exact command, and every observed
value — including failures. It also carries an explicit `claims` block listing
what the run does *not* establish.

Receipts are gitignored. Yours should come from your hardware.

---

## What this does not claim

Scope matters more than adjectives, so plainly:

- **Ordered-sequence equality under reordering is not claimed.** Queries return
  nodes in insertion order, so sequences differ between builds by design. The
  claim is set completeness and exactness, which is narrower.
- **No retrieval, recall, or latency numbers.** This repo measures durability
  and set integrity. Nothing else.
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

Device-key signing of receipts is the next release, not this demo.

---

## License

Proprietary. Non-commercial evaluation use only.

**Contact:** Ryan Barkley · [xdeviantxmindx@gmail.com](mailto:xdeviantxmindx@gmail.com)

Native library source is not included. Pre-built binaries are provided for evaluation.
