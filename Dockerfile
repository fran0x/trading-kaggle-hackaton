# hackathon/Dockerfile
FROM python:3.12-slim as base

# Install build tools & Rust toolchain for mixed‑language teams
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc curl build-essential && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.cargo/bin:${PATH}"

# Python deps
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /workspace
CMD ["bash"]