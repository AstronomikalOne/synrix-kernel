# Positioning — receipt-backed agent state

**Other memory systems try to improve what an agent remembers. Synrix makes committed agent state survive predictably — and makes that behavior independently observable.**

That sentence is the product. Everything else is how hard it is to falsify.

---

## The wedge

Semantic-memory products (Mem0, Letta, Zep, and cousins) compete over **what gets remembered and what gets retrieved**: extraction, hybrid search, personalization, temporal graphs, context assembly.

Synrix sits **under** that question.

| They answer | Synrix answers |
|-------------|----------------|
| What should the agent remember? | What did the agent actually commit, what survived failure, and what evidence demonstrates that? |

Do not fight them on extraction algorithms. Own the floor:

```text
LLM / Agent
     │
Semantic memory layer   Mem0 / custom / graph / RAG
     │
Agent state model
     │
SYNRIX                  durability + recovery + receipts
     │
Filesystem / flash / device
```

---

## Receipt-backed durability (not “proof”)

An audit log generally records **what the application says happened**.

A Synrix receipt records **what the persistence subsystem demonstrated after failure**, against **this exact binary** on **this device**, under **this harness**.

Not: `write() returned success`.

But: on this device, against this binary, this acknowledged operation survived this failure scenario, under this harness, and here is the evidence.

Call it **receipt-backed durability**. Do not call it a proof. Device-key signing is the next release; until then the receipt is a reproducible evidence file, not authenticated chain-of-custody.

---

## Failure semantics as a contract

Having a WAL is not differentiation. RocksDB and a generation of engines already expose flush/sync tradeoffs.

The offer is that the **failure contract, the implementation, and the falsification tests ship together**.

Intended contract (ACK vs DURABLE contrast is **roadmap**; this pack measures DURABLE + RECEIPT):

```text
ACK
  Process-local acknowledgement.
  May be lost under declared failure classes.
  (Not yet a public demo scenario.)

DURABLE
  Acknowledgement after declared persistence boundary.
  Demonstrated: SIGKILL after ACK, fresh-process WAL replay,
  injected incomplete WAL tail, WAL-destroy negatives.

RECEIPT
  Machine-verifiable observation of the above against
  binary X on device Y. No observation → no receipt.
```

---

## Agent state, not “AI memory”

“AI memory” evokes embeddings, RAG, personalization, conversation history. That is their aisle.

**Agent state** is operational: task progression, local world state, tool state, policies, accumulated observations, checkpoints, machine-derived knowledge.

> Persistent state for autonomous systems that cannot shrug after reboot.

---

## Principle: no observation → no claim

If the shipped binary or platform cannot measure the claim, Synrix **refuses to issue a receipt**. It does not substitute a canned result.

That refusal is part of the product identity, not a missing feature.

---

## What is not differentiation

| Phrase | Why not |
|--------|---------|
| “We use WAL.” | Storage engines already do. |
| “Persistent AI memory.” | Crowded; wrong layer. |
| “Runs offline.” | Useful, not unique. |
| “Auditable.” | Vague. The distinction is **failure evidence**, not a log. |
| “Deterministic.” | Public evidence is set completeness under one insertion-order experiment. Do not resurrect the larger adjective. |

The defensible combination is:

**edge-native + agent-state-oriented + explicit persistence contracts + hostile failure testing + device-generated receipts + (roadmap) authenticated chain-of-custody.**

Build toward making the opening sentence harder to falsify. Do not invent a new graph-memory algorithm to feel busy.
