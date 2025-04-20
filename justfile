DATA        := "data"
START_TS    := "1743292800000"   # 2025‑04‑30
END_TS      := "1743379200000"   # 2025‑04‑31
SYMBOL      := "BTC/USDT"
TEAM        := "alpha"
TIMEFRAME   := "1m"

# Convert symbol format for filename (BTC/USDT -> btcusdt)
SYMBOL_FILE := replace(lowercase(SYMBOL), "/", "")
STRATEGY    := TEAM + "_submission.tgz"
MARKET_DATA := DATA + "/" + SYMBOL_FILE + "_" + TIMEFRAME + ".parquet"

# print options
default:
    @just --list --unsorted

alias i := install
alias b := build
alias d := download
alias t := tar
alias s := score
alias c := clean
alias p := print

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
    python -m exchange.engine {{STRATEGY}} --data {{MARKET_DATA}}

# print current configuration
print:
    @echo "Symbol: {{SYMBOL}}"
    @echo "Timeframe: {{TIMEFRAME}}"
    @echo "Input File: {{MARKET_DATA}}"
    @echo "Team: {{TEAM}}"
    @echo "Strategy: {{STRATEGY}}"

# remove downloaded data and generated archives
clean:
    rm -f data/*.parquet && \
    rm -f *_submission.tgz