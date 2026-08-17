# Building native libraries

First-look needs `build/libsynrix.so` (copied from `lib/linux-<arch>/` by `make first-look`).

`make setup` requires that binary to export `lattice_wal_get_recovery_stats`.

Refresh a shipped `.so` from private Synrix source:

    cd Synrix/NebulOS-Scaffolding
    bash scripts/build_libsynrix.sh
    cp build/libsynrix.so /path/to/synrix-kernel/lib/linux-$(uname -m)/libsynrix.so

Then in `synrix-kernel` run `make first-look` on that same machine.
