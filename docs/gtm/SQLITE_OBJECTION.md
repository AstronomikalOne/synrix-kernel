# Why not SQLite? (kernel-sale gate)

**Use this first.** If an OEM rejects this paragraph, Synrix is not the right store.

---

## The paragraph (say this)

SQLite is excellent on-device storage — free, battle-tested, and enough when you only need durable rows. And you *could* build the rest on it: a named ACK-vs-durable contract, order-invariant retrieval over agent state, kill-and-replay test harnesses, evidence artifacts you keep across board revisions. Teams do. It's real engineering, and it's yours to own forever.

Synrix is that layer, already built and versioned as one component: retrieval semantics, order-invariant behavior under insert and churn, durable persistence with a receipted contract, and the failure-injection harness that proves it. The offer is the NRE you skip and the failure modes you meet in our test suite instead of in the field. If you'd rather build it, that's a legitimate answer — the question is only whether it's on your roadmap or ours.

---

## If they push (30 seconds)

| They say | You say |
|----------|---------|
| “We already fsync.” | “Then you're most of the way there. What we'd add is the named contract and the harness — ACK-then-kill vs durable-then-kill through the same API, with the negative tests that prove it reports loss.” |
| “We'll write our own WAL flags.” | “Plenty of teams do, and it works. The cost shows up in maintaining it across board revisions and proving it still holds. That's the line item we're offering to absorb.” |
| “We don't need AI Act yet.” | “Then SQLite is a reasonable call today. Worth knowing what this costs to retrofit if ‘show what the agent knew after the outage’ becomes a procurement line.” |

---

## What we do **not** say

- Synrix beats SQLite at generic persistence
- SQLite *can't* do this — a good team can; we're selling that they don't have to
- Regulators require Synrix
- ANN / Mem0 replacement
- Anything about what an auditor “will” ask — we don't know their auditor
