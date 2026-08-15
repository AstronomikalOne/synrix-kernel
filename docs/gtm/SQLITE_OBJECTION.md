# Why not SQLite? (kernel-sale gate)

**Use this first.** If an OEM rejects this paragraph, Synrix is not the right store.

Use the same nouns as `make receipt`. Do not upgrade them in conversation.

---

## The paragraph (say this)

SQLite is excellent on-device storage — free, battle-tested, and enough when you only need durable rows. RocksDB and friends already give you a WAL and sync knobs. A capable team can build a named failure contract, kill/replay harness, WAL-destroy negatives, and device-generated receipts on top of either. Teams do. It's real engineering, and it's yours to own forever.

Synrix is that layer, already built and versioned as one component for **agent state** (not “AI memory”): ACK may lose after SIGKILL, DURABLE retains, recovery stops at an injected incomplete WAL tail, set-complete node identity when the same 2,000 nodes are inserted in two orders, and a receipt generated against *this* binary on *this* hardware. The offer is the NRE you skip and the failure modes you meet in our test suite instead of in the field. If you'd rather build it, that's a legitimate answer — the question is only whether it's on your roadmap or ours.

This pack does **not** claim order-invariant retrieval, churn, or that having a WAL is unique. Those words are not in the receipt. We do not replace Mem0/Letta/Zep — we sit under them.

---

## If they push (30 seconds)

| They say | You say |
|----------|---------|
| “We already fsync.” | “Then you're most of the way there. What we'd add is the harness you can re-run: durable write, ACK, SIGKILL, WAL replay, plus the negative tests that prove destroying the WAL is reported as loss.” |
| “We'll write our own WAL flags.” | “Plenty of teams do, and it works. Having a WAL is not the product. The product is the failure contract, the harness, and the receipt, kept across board revisions.” |
| “We don't need AI Act yet.” | “Then SQLite is a reasonable call today. Worth knowing what this costs to retrofit if ‘show what the agent knew after the outage’ becomes a procurement line.” |

---

## What we do **not** say

- Synrix beats SQLite at generic persistence
- SQLite *can't* do this — a good team can; we're selling that they don't have to
- Order-invariant retrieval or churn as a verified public claim
- Regulators require Synrix
- ANN / Mem0 replacement — we sit under semantic memory, we don't fight it
- Anything about what an auditor “will” ask — we don't know their auditor
