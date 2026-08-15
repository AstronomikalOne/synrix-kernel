.PHONY: first-look receipt test setup setup-first-look

# Partner first look: one-pager, then a receipt generated here from this
# binary. On an arch whose pack cannot measure durability, prints a designed
# limit and writes nothing (exit 0) — there are no shipped numbers to fall
# back on, which is the point.
first-look: setup-first-look
	PYTHONUNBUFFERED=1 SYNRIX_LIB_PATH="$(CURDIR)/build" \
		python3 scripts/demo_first_look.py

# The receipt on its own: runs the checks, records binary hash, build ID,
# board/SoC/kernel identity, harness hashes, and every observed value.
receipt: setup
	PYTHONUNBUFFERED=1 SYNRIX_LIB_PATH="$(CURDIR)/build" \
		python3 scripts/synrix_receipt.py

test: setup-first-look
	python3 scripts/test_check_demo_pack.py
	SYNRIX_LIB_PATH="$(CURDIR)/build" python3 scripts/test_durability_harness.py

setup-first-look:
	python3 scripts/check_demo_pack.py --copy --require-libsynrix

# Kernel pack: libsynrix.so + current WAL symbol. Stale binary → FAIL.
setup:
	python3 scripts/check_demo_pack.py --copy --require-libsynrix --require-wal
