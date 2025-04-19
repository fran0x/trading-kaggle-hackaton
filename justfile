DATA_DIR  := "data"
START_TS  := "1743292800000"   # 2025‑04‑30
END_TS    := "1743379200000"   # 2025‑04‑31
SYMBOL    := "BTC/USDT"
TEAM      := "alpha"

# print options
default:
    @just --list --unsorted

alias i := install
alias b := build
alias d := download
alias t := tar
alias s := score
alias c := clean

# install Python requirements
install:
    pip install --upgrade pip && \
    pip install -r requirements.txt

# build the Docker environment
build:
    docker build -t junz .

# download 1‑minute OHLCV
download:
    python scripts/download.py {{SYMBOL}} --start {{START_TS}} --end {{END_TS}}

# archive the strategy
tar:
    tar -czf {{TEAM}}_submission.tgz strategy/

# score with Python the strategy
score:
    FILE="{{TEAM}}_submission.tgz" \
    DATA="{{DATA_DIR}}/$(echo '{{SYMBOL}}' | tr '[:upper:]' '[:lower:]' | tr -d '/')_1m.parquet" \
    python -m exchange.engine "$FILE" --data "$DATA"

# remove downloaded data and generated archives
clean:
    rm -f data/*.parquet && \
    rm -f *_submission.tgz