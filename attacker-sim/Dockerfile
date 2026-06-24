FROM debian:bookworm-slim@sha256:60eac759739651111db372c07be67863818726f754804b8707c90979bda511df

RUN apt-get update && apt-get install -y \
    hydra \
    sshpass \
    openssh-client \
    curl \
    wget \
    bash \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN chmod +x /app/run_scenario.sh || true
RUN chmod +x /app/scenarios/*.sh || true

CMD ["tail", "-f", "/dev/null"]
