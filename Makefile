.PHONY: first-look first-look-receipts setup setup-first-look

# Partner first look: one-pager + hashed receipts + live WAL kill/recall
# when the arch pack exports lattice_wal_get_recovery_stats. Otherwise
# designed-limit banner + receipts (exit 0).
first-look: setup-first-look
	PYTHONUNBUFFERED=1 SYNRIX_LIB_PATH="$(CURDIR)/build" \
		python3 scripts/demo_first_look.py

first-look-receipts: setup-first-look
	PYTHONUNBUFFERED=1 SYNRIX_LIB_PATH="$(CURDIR)/build" \
		python3 scripts/demo_first_look.py --skip-live

setup-first-look:
	python3 scripts/check_demo_pack.py --copy --require-libsynrix

# Kernel pack: libsynrix.so + current WAL symbol. Stale binary → FAIL.
setup:
	python3 scripts/check_demo_pack.py --copy --require-libsynrix --require-wal
