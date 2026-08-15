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

**Durability under `SIGKILL`.** A child writes under durable sync
(`SYNRIX_SYNC_PROFILE=durable`, `fsync`, batch size 0) and signals that the
write was acknowledged. The parent then sends `SIGKILL`, which cannot be caught
— no handler runs, nothing flushes, no checkpoint is taken. The harness records
whether a snapshot file exists at that moment; if one did, the WAL would not be
load-bearing and the result would be meaningless. A fresh process opens the
lattice, and the receipt records how many WAL records were replayed and whether
the WAL was reinitialized.

**Torn WAL tail.** The same scenario, with 28 bytes of partial record appended
to the WAL before restart — shorter than an entry header, which is what a power
cut mid-write leaves behind. Recovery stops at the tear and retains every
complete record before it.

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
- **Sustained thermal or multi-hour behaviour.** These runs take seconds.
- **Anything about other builds.** Only the binary whose hash appears in the
  receipt is described.

## Proving the checks can fail

`make test` runs `scripts/test_durability_harness.py`, which deletes the WAL,
zeroes the WAL, and asserts that no snapshot exists at kill time. Each of those
must cause the demo to report loss. A durability check that passes unconditionally
would be worse than no check, because it would look like evidence.

## Roadmap

1. aarch64 durability in CI on real hardware, with the generated receipt saved
   as an artifact bound to the binary SHA.
2. `synrix_abi_version()` / `synrix_lattice_sizeof()` exports, so the harness
   stops depending on a pinned struct layout.
3. The ACK-can-lose vs durable-retains contrast as a public scenario.
4. Device-key signing, so a receipt is chain-of-custody rather than a checksum.
