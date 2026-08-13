# Why not SQLite? (kernel-sale gate)

**Use this first.** If an OEM rejects this paragraph, Synrix is not the right store.

---

## The paragraph (say this)

SQLite is excellent on-device storage — free, battle-tested, and enough when you only need durable rows. Synrix is for **agent-state workloads under audit pressure**: a closed memory kernel with **receipted durability contracts** (fast ACK vs OEM-durable), **bit-identical / deterministic behavior** under controlled insert-order and churn tests, and **receipted mission evidence** — hash-stamped, re-runnable — of what the agent still knew after outage or hard kill. An EU AI Act / CRA-minded buyer will not ask “did you have a database?” — they will ask “can you show synchronized survival semantics and a trusted record of what remained true after failure?” SQLite does not productize that; Synrix does.

---

## If they push (30 seconds)

| They say | You say |
|----------|---------|
| “We already fsync.” | “Good. Show me the named contract an auditor can re-run: ACK-then-kill vs durable-then-kill, same API, receipted.” |
| “We’ll write our own WAL flags.” | “Many teams plan to. Few ship a re-runnable OEM receipt and keep it across boards. That’s the NRE we’re saving.” |
| “We don’t need AI Act yet.” | “Then keep SQLite. Call us when ‘prove what the agent knew after the outage’ becomes a procurement line.” |

---

## What we do **not** say

- Synrix beats SQLite at generic persistence
- Regulators require Synrix
- ANN / Mem0 replacement
