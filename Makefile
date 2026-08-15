.PHONY: first-look receipt conformance test setup setup-first-look

# Partner first look: one-pager, then a receipt generated here from this
# binary. On an arch whose pack cannot measure durability, prints a designed
# limit and writes nothing (exit 0) — there are no shipped numbers to fall
# back on, which is the point.
first-look: setup-first-look
	PYTHONUNBUFFERED=1 SYNRIX_LIB_PATH="$(CURDIR)/build" \
		python3 scripts/demo_first_look.py

# Generate a receipt on this machine. Written even when a lane fails.
receipt: setup
	PYTHONUNBUFFERED=1 SYNRIX_LIB_PATH="$(CURDIR)/build" \
		python3 scripts/synrix_receipt.py

# Target-hardware ship gate: receipt plus the conformance card.
# Exit 1 if conformance is FAIL or if no receipt was issued.
conformance: setup
	PYTHONUNBUFFERED=1 SYNRIX_LIB_PATH="$(CURDIR)/build" \
		python3 scripts/synrix_receipt.py; \
	rc=$$?; \
	python3 scripts/conformance_summary.py; \
	exit $$rc

test: setup-first-look
	python3 scripts/test_check_demo_pack.py
	python3 scripts/test_receipt_claims.py
	SYNRIX_LIB_PATH="$(CURDIR)/build" python3 scripts/test_durability_harness.py

setup-first-look:
	python3 scripts/check_demo_pack.py --copy --require-libsynrix

# Kernel pack: libsynrix.so + current WAL symbol. Stale binary → FAIL.
setup:
	python3 scripts/check_demo_pack.py --copy --require-libsynrix --require-wal
