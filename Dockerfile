# syntax=docker/dockerfile:1
FROM python:3.12-slim

LABEL description="Synrix OEM memory kernel — first look"

WORKDIR /app

COPY scripts/demo_first_look.py            scripts/demo_first_look.py
COPY scripts/demo_first_look_durability.py scripts/demo_first_look_durability.py
COPY scripts/demo_order_invariance.py      scripts/demo_order_invariance.py
COPY scripts/synrix_receipt.py             scripts/synrix_receipt.py
COPY scripts/check_demo_pack.py            scripts/check_demo_pack.py
COPY docs/gtm/                             docs/gtm/
COPY lib/                                  lib/

RUN mkdir -p build && \
    ARCH=$(uname -m) && \
    if   [ "$ARCH" = "aarch64" ]; then LIBDIR=linux-aarch64; \
    elif [ "$ARCH" = "x86_64"  ]; then LIBDIR=linux-x86_64; \
    else echo "Unsupported arch: $ARCH" && exit 1; fi && \
    if [ -f "lib/${LIBDIR}/libsynrix.so" ]; then \
        cp "lib/${LIBDIR}/"*.so build/; \
    else \
        echo "Pre-built libsynrix.so not available for ${ARCH} (${LIBDIR})."; \
        exit 1; \
    fi && \
    test -f build/libsynrix.so

ENV PYTHONPATH=/app
ENV SYNRIX_LIB_PATH=/app/build

CMD ["python3", "scripts/demo_first_look.py"]
