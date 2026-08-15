# Why not SQLite? (kernel-sale gate)

**Use this first.** If an OEM rejects this paragraph, Synrix is not the right store.

Use the same nouns as `make receipt`. Do not upgrade them in conversation.

---

## The paragraph (say this)

SQLite is excellent on-device storage — free, battle-tested, and enough when you only need durable rows. And you *could* build the rest on it: a durable-write kill/replay harness, negative controls that prove WAL destruction is reported as loss, set completeness under insertion-order shuffle, evidence artifacts you keep across board revisions. Teams do. It's real engineering, and it's yours to own forever.

Synrix is that layer, already built and versioned as one component: durable persistence under `SIGKILL` after an acknowledged write, recovery that stops at an injected incomplete WAL tail, set-complete node identity when the same 2,000 nodes are inserted in two orders, and the failure-injection harness that proves the demo reports loss. The offer is the NRE you skip and the failure modes you meet in our test suite instead of in the field. If you'd rather build it, that's a legitimate answer — the question is only whether it's on your roadmap or ours.

This pack does **not** claim order-invariant retrieval, churn, or a public ACK-vs-durable contrast. Those words are not in the receipt.

---

## If they push (30 seconds)

| They say | You say |
|----------|---------|
| “We already fsync.” | “Then you're most of the way there. What we'd add is the harness you can re-run: durable write, ACK, SIGKILL, WAL replay, plus the negative tests that prove destroying the WAL is reported as loss.” |
| “We'll write our own WAL flags.” | “Plenty of teams do, and it works. The cost shows up in maintaining it across board revisions and proving it still holds. That's the line item we're offering to absorb.” |
| “We don't need AI Act yet.” | “Then SQLite is a reasonable call today. Worth knowing what this costs to retrofit if ‘show what the agent knew after the outage’ becomes a procurement line.” |

---

## What we do **not** say

- Synrix beats SQLite at generic persistence
- SQLite *can't* do this — a good team can; we're selling that they don't have to
- Order-invariant retrieval, churn, or ACK-vs-durable as a verified public claim
- Regulators require Synrix
- ANN / Mem0 replacement
- Anything about what an auditor “will” ask — we don't know their auditor
