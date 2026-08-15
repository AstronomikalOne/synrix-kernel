# Receipts

## Nothing here is shipped

This repo contains no pre-computed result files. Earlier versions did, and they
were removed, because a receipt you did not generate is not evidence — it is a
JSON file that hashes to itself.

Receipts are produced by `make receipt`, on your machine, by the
`libsynrix.so` in this repo, and written to `receipts/generated/` (gitignored).

## What a receipt contains

| Block | Contents |
|-------|----------|
| `environment` | UTC time, board model, CPU/SoC, machine, core count, page size, kernel release and version, L4T/JetPack release, power mode, libc, Python version |
| `binary` | Path, SHA-256, size, GNU build ID, full ELF description, whether the WAL recovery symbol is exported |
| `harness` | SHA-256 of every script the result depends on |
| `command` | The exact invocation |
| `results` | Every observed value from every check, including failures |
| `claims` | Explicit `establishes` / `does_not_establish` lists |

The `binary` and `harness` hashes are the ones that matter for comparison. Two
receipts from different machines should agree on those and differ everywhere in
`environment`. If the binary hashes differ, you are not comparing the same thing.

## What the checks establish

**ACK vs DURABLE.** ACK means **no durability guarantee** (writes may be lost;
incidental persistence after a flush is allowed). This pack also runs an
**unflushed witness**: batch=50000, one operation, SIGKILL immediately after
ACK — the write is absent. That demonstrates permitted loss. It does not define
ACK as “the mode where writes must disappear.”

DURABLE (per-entry fsync) **survives** the same kill. The kernel is the product;
the receipt records which contract was observed.

**DURABLE mechanics.** Under `SYNRIX_SYNC_PROFILE=durable` (`fsync`, batch size
0) the parent sends `SIGKILL` after the write is acknowledged. The harness
records whether a file exists at the expected snapshot path. Absence there,
plus WAL-destroy negative controls, shows the WAL is load-bearing. It does not
prove the binary wrote nowhere else on the filesystem. A fresh process opens
the lattice (emits `opened=1` only after `lattice_init` succeeds).

**Torn / incomplete WAL tail.** The same scenario, with 28 bytes of incomplete
record appended and fsynced after the writer is dead. Shorter than an entry
header. Recovery stops at the fragment and retains every complete record before
it. This establishes tolerance to an **injected incomplete WAL tail**. It does
not simulate power loss, filesystem write ordering under sudden power removal,
storage-cache behaviour, or torn sectors.

One note on a field that is easy to misread: the kernel's `truncated_tail` flag
reports whether the WAL file was physically rewritten. Recovery does not rewrite
it, so the flag reads `0` even in the torn-tail scenario. It is recorded in the
receipt as observed, not interpreted.

**Insertion-order set integrity.** 2000 nodes are inserted in natural order,
then in an order shuffled under seed 12345, and the full node set is read back
via `lattice_find_nodes_by_type` both times. The receipt records the returned
counts, duplicate counts, set equality, and payload integrity.

## What the checks do not establish

- **Ordered-sequence equality.** `lattice_find_nodes_by_type` returns nodes in
  insertion order, so the sequences differ between the two builds. The receipt
  records `ordered_identical: false` rather than hiding it. The claim is set
  completeness and exactness, which is a narrower and true statement.
- **Retrieval quality, recall, or latency.** Not measured here, not claimed here.
- **Power-loss behaviour.** The incomplete tail is injected after kill, then
  fsynced. Not a power cut.
- **That the binary wrote no other files anywhere.** Expected snapshot path
  plus WAL-destroy negatives only.
- **That ACK writes must disappear.** ACK means no durability guarantee. The
  unflushed lane is a witness of permitted loss.
- **Sustained thermal or multi-hour behaviour.** These runs take seconds.
- **Anything about other builds.** Only the binary whose hash appears in the
  receipt is described.

## Proving the checks can fail

`make receipt` copies the durable WAL, then deletes it and zeroes a second
copy. Both leaves the mission absent. `make test` repeats those negatives as
unittests. A durability check that passes unconditionally would be worse than
no check, because it would look like evidence.

## Roadmap

1. aarch64 durability in CI on real hardware, with the generated receipt saved
   as an artifact bound to the binary SHA (behavioral conformance suite).
2. `synrix_abi_version()` / `synrix_lattice_sizeof()` exports, so the harness
   stops depending on a pinned struct layout.
3. Device-key signing, so a receipt is chain-of-custody rather than a checksum.
4. Grow the failure corpus (ENOSPC, concurrent writers, crash cycles, ABI
   mismatch) — each with declared behavior, experiment, observation, receipt.
