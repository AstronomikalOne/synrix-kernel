# Receipts — what they establish, and what they don't

Read this before you weigh the numbers in the README. It is written to be
unflattering where the evidence is thin, because the alternative is you
discovering it yourself and trusting the rest of the repo less.

## The short version

The four JSON files in `receipts/first_look/` are **artifacts from runs on a
private research tree**. `make first-look` reads them, prints selected scalars,
and prints a SHA-256 of each file.

That hash establishes exactly one thing: **the file you are reading is the file
we shipped**. It does not re-derive the result, and it is not a signature — a
SHA-256 computed locally over a file we also shipped proves the file has not
been corrupted in transit, nothing more. Device-key signing is the next release.

**The durability test is different.** That one runs on your hardware, against
the binary in this repo, and it can fail — see `scripts/test_durability_harness.py`,
which deletes and zeroes the WAL to prove the demo reports loss. If you only
have time to evaluate one thing here, evaluate that.

## Provenance of the four retrieval receipts

| Receipt | What it measures | Dataset identity |
|---------|------------------|------------------|
| `cwru_hnsw_gate1_receipt.json` | Recall@10, native C/NEON median latency, byte-fraction vs full scan | corpus path only — **no dataset hash** |
| `p19_determinism_receipt.json` | Ordered top-k invariance under insertion-order shuffle, with an HNSW control arm | corpus path only — **no dataset hash** |
| `p19_streaming_receipt.json` | Incremental vs batch build parity, post-churn recall | corpus path only — **no dataset hash** |
| `aion_filtration_stage2_receipt.json` | Filtration-stage retrieval detail | `corpus_sha256`, `cache_sha256`, `query_ids_sha256` present |

All four record `git_commit` from a private repository, so that field is not
independently checkable by you. The corpus is CWRU bearing-fault data, pinned in
the stage-2 receipt as:

```
corpus_sha256 = a12cbe63ee0d258ee02f41aad484b53627c48490e7eb3156e3b7dac162c7618f
```

The other three were generated against the same corpus but do not carry the
hash inline. Treat that as a gap, not a guarantee.

## Reading the determinism claim precisely

The headline is **2000/2000 ordered top-k identical**. The exact scope:

- One corpus (CWRU holdout, 73,919 train / 2,000 queries)
- One shuffle seed (`12345`), one split seed (`0`), `k=10`
- Ordered top-k equivalence — *not* bitwise-identical output, and not tested
  across compilers, thread counts, or hardware

What makes it worth attention is the control arm in the same receipt: HNSW under
the same shuffle returns **863/2000** ordered-identical, and **1082/2000** under
multi-threaded build. So the test discriminates — it is not a test that
everything passes.

What would make it strong: many seeds, restarts, thread counts, compiler builds,
and byte-level output hashing. That is roadmap, and until it exists, the claim
should be read as scoped above.

## Environment identity for the latency number

`~25.5 µs` median native retrieval is warm-process, explicitly labelled in the
receipt as `warm_process_bench_not_sustained_thermal_pack`. The receipt does
**not** currently record board model, SoC, JetPack/kernel version, power mode,
clocks, compiler flags, or binary hash.

For an edge kernel that is a real omission, and it means the number should be
treated as indicative rather than as a spec you design against. Full environment
capture is roadmap.

## Roadmap for this document

In priority order:

1. A regeneration lane — pinned public fixture, shipped harness, manifest with
   hashes for binary/dataset/harness/config, and a `make receipt` that actually
   produces output on your machine.
2. aarch64 durability in CI on real hardware, with the generated receipt saved
   as an artifact bound to the binary SHA.
3. Full environment capture in the benchmark receipts.
4. Device-key signing, so a receipt is chain-of-custody rather than a checksum.
