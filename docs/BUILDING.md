# Building native libraries

First-look needs `build/libsynrix.so` (copied from `lib/linux-<arch>/` by `make first-look`).

`make setup` also requires that binary to export `lattice_wal_get_recovery_stats`. A May-era x86 binary is a FAIL, not an OK.

Refresh x86 `libsynrix.so` from private Synrix source when a current binary is available. Until then, `make first-look` on x86_64 verifies receipts and prints a designed-limit banner.
