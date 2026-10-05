# Build from the repository root with an explicit target and freeze both image IDs for a campaign:
#   docker build -f benchmark/Dockerfile --target agent -t keygen-ft2-benchmark:local .
#   docker build -f benchmark/Dockerfile --target visualizer -t keygen-ft2-visualizer:local .
ARG BASE_IMAGE=debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251
FROM ${BASE_IMAGE} AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git ca-certificates pkg-config libsdl2-dev libmicrohttpd-dev python3 \
    && rm -rf /var/lib/apt/lists/*
COPY scripts/build-ft2-linux.sh /tmp/build-ft2.sh
RUN bash /tmp/build-ft2.sh /tmp/ft2-src \
    && install -m 755 /tmp/ft2-src/release/other/ft2-clone /usr/local/bin/ft2-clone
COPY tools/ft2_smoke.py /opt/keygen/tools/ft2_smoke.py
RUN SDL_AUDIODRIVER=dummy python3 /opt/keygen/tools/ft2_smoke.py \
    --ft2 /usr/local/bin/ft2-clone --out /tmp/native-acceptance \
    && cp /tmp/native-acceptance/report.json /opt/keygen/native-acceptance.json \
    && sed '/^def wav_metrics(/,$d' /opt/keygen/tools/ft2_smoke.py > /opt/keygen/tools/ft2_transport.py \
    && python3 -m py_compile /opt/keygen/tools/ft2_transport.py

FROM ${BASE_IMAGE} AS agent
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash coreutils python3 python3-numpy libsdl2-2.0-0 libmicrohttpd12 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home agent \
    && mkdir -p /workspace && chown agent:agent /workspace
COPY --from=build /usr/local/bin/ft2-clone /usr/local/bin/ft2-clone
COPY --from=build /opt/keygen/tools/ft2_transport.py /opt/keygen/tools/ft2_transport.py
COPY --from=build /opt/keygen/native-acceptance.json /opt/keygen/native-acceptance.json
COPY benchmark/bridge.py /opt/keygen/bridge.py
RUN printf '#!/bin/sh\nexec python3 /opt/keygen/bridge.py "$@"\n' > /usr/local/bin/ft2 \
    && chmod 755 /usr/local/bin/ft2 \
    && dpkg-query -W > /opt/keygen/packages.txt \
    && sha256sum /usr/local/bin/ft2-clone > /opt/keygen/binary.sha256
ENV SDL_AUDIODRIVER=dummy HOME=/home/agent XDG_CONFIG_HOME=/home/agent/.config
USER 10001:10001
WORKDIR /workspace
ENTRYPOINT ["python3", "/opt/keygen/bridge.py", "serve", "/usr/local/bin/ft2-clone"]

# Trusted visualizer: records the FT2 GUI playing a collected module. Never given to the agent.
FROM agent AS visualizer
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb x11-utils xdotool ffmpeg libsdl2-2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && dpkg-query -W > /opt/keygen/packages.txt
COPY benchmark/visualize.sh /opt/keygen/visualize.sh
USER 10001:10001
ENTRYPOINT ["/bin/sleep", "infinity"]
