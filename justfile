##################
# DEFAULT VALUES #
##################

DATA        := "data"

# Default time range

# dataset00
# START_TS    := "1746057600000"   # 2025‑05‑01
# END_TS      := "1746144000000"   # 2025‑05‑02

# dataset01
# START_TS    := "1738368000000"   # 2025‑02‑01
# END_TS      := "1743465600000"   # 2025‑04‑01

# dataset02
# START_TS    := "1612137600000"   # 2021‑02‑01
# END_TS      := "1617235200000"   # 2021‑04‑01

# dataset03
START_TS    := "1740614400000"   # 2023‑02‑01
END_TS      := "1745712000000"   # 2023‑04‑01

TIMEFRAME   := "1m"

# Default trading fees
FEE := "3"  # In basis points (3 = 0.03%)

# Default assets and balances
# TOKEN_1 := "ETH"
# TOKEN_2 := "BTC" 
# FIAT    := "USDT"

TOKEN_1 := "ETH"
TOKEN_2 := "BTC" 
FIAT    := "USDT"

TOKEN_1_BALANCE := "100"
TOKEN_2_BALANCE := "10"
FIAT_BALANCE    := "500000"

# Default team
TEAM        := "alpha"

# Default ratios for solution file
PUBLIC_RATIO  := "1."
PRIVATE_RATIO := "0."
IGNORED_RATIO  := "0."

###########
# RECIPES #
###########

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

# download market data for several pairs
download token1=TOKEN_1 token2=TOKEN_2 fiat=FIAT:
    #!/usr/bin/env bash
    # Convert to lowercase for filenames
    TOKEN1_LC=$(echo "{{token1}}" | tr '[:upper:]' '[:lower:]')
    TOKEN2_LC=$(echo "{{token2}}" | tr '[:upper:]' '[:lower:]')
    FIAT_LC=$(echo "{{fiat}}" | tr '[:upper:]' '[:lower:]')
    
    echo "Downloading data for {{token1}}/{{fiat}}, {{token2}}/{{fiat}}, and {{token1}}/{{token2}}..."
    
    # Create the data directory if it doesn't exist
    mkdir -p {{DATA}}
    
    # Download token1/fiat data
    python scripts/download.py "{{token1}}/{{fiat}}" --start {{START_TS}} --end {{END_TS}} \
        --output {{DATA}}/${TOKEN1_LC}${FIAT_LC}_{{TIMEFRAME}}.csv
    
    # Download token2/fiat data
    python scripts/download.py "{{token2}}/{{fiat}}" --start {{START_TS}} --end {{END_TS}} \
        --output {{DATA}}/${TOKEN2_LC}${FIAT_LC}_{{TIMEFRAME}}.csv
    
    # Download token1/token2 data
    python scripts/download.py "{{token1}}/{{token2}}" --start {{START_TS}} --end {{END_TS}} \
        --output {{DATA}}/${TOKEN1_LC}${TOKEN2_LC}_{{TIMEFRAME}}.csv

    echo "Download complete for {{token1}}, {{token2}}, and {{fiat}}."

    echo "Merging data files..."
    python scripts/merge.py \
        {{DATA}}/${TOKEN1_LC}${FIAT_LC}_{{TIMEFRAME}}.csv \
        {{DATA}}/${TOKEN2_LC}${FIAT_LC}_{{TIMEFRAME}}.csv \
        {{DATA}}/${TOKEN1_LC}${TOKEN2_LC}_{{TIMEFRAME}}.csv \
        --output {{DATA}}/test.csv \
        --token1 {{token1}} \
        --token2 {{token2}} \
        --fiat {{fiat}}
    echo "Data files merged into {{DATA}}/test.csv"

    echo "Generating a solution file..."
    python scripts/solution.py {{DATA}}/test.csv {{DATA}}/solution.csv \
        --public-ratio {{PUBLIC_RATIO}} \
        --private-ratio {{PRIVATE_RATIO}} \
        --ignored-ratio {{IGNORED_RATIO}}
    echo "Solution file generated at {{DATA}}/solution.csv"

# archive the trading strategy
tar team=TEAM:
    @echo "Creating strategy archive for team {{team}}..."
    tar -czf {{team}}_submission.tgz strategy/

# generate transactions with a trading strategy
trade team=TEAM token1=TOKEN_1 token2=TOKEN_2 fiat=FIAT token1_balance=TOKEN_1_BALANCE token2_balance=TOKEN_2_BALANCE fiat_balance=FIAT_BALANCE fee=FEE:
    #!/usr/bin/env bash
    # Calculate strategy file name
    STRATEGY_FILE="{{team}}_submission.tgz"

    # Convert to lowercase for filenames
    TOKEN1_LC=$(echo "{{token1}}" | tr '[:upper:]' '[:lower:]')
    TOKEN2_LC=$(echo "{{token2}}" | tr '[:upper:]' '[:lower:]')
    FIAT_LC=$(echo "{{fiat}}" | tr '[:upper:]' '[:lower:]')

    echo "Trading strategy with {{token1}}/{{fiat}}, {{token2}}/{{fiat}}, and {{token1}}/{{token2}} for team {{team}}..."
    echo "Initial balances: {{token1}}={{token1_balance}}, {{token2}}={{token2_balance}}, {{fiat}}={{fiat_balance}}"
    FEE_DECIMAL=$(echo "scale=4; {{fee}}/10000" | bc)
    FEE_PERCENT=$(echo "scale=2; {{fee}}/100" | bc)
    echo "Trading fee: {{fee}} basis points ($FEE_DECIMAL or ${FEE_PERCENT}%)"

    python -m exchange.trade ${STRATEGY_FILE} \
        --data {{DATA}}/test.csv \
        --output {{DATA}}/submission.csv \
        --token1_balance {{token1_balance}} \
        --token2_balance {{token2_balance}} \
        --fiat_balance {{fiat_balance}} \
        --fee {{fee}}

# score the generated transactions
score team=TEAM token1=TOKEN_1 token2=TOKEN_2 fiat=FIAT token1_balance=TOKEN_1_BALANCE token2_balance=TOKEN_2_BALANCE fiat_balance=FIAT_BALANCE fee=FEE:
    #!/usr/bin/env bash
    # Calculate strategy file name
    STRATEGY_FILE="{{team}}_submission.tgz"

    # Convert to lowercase for filenames
    TOKEN1_LC=$(echo "{{token1}}" | tr '[:upper:]' '[:lower:]')
    TOKEN2_LC=$(echo "{{token2}}" | tr '[:upper:]' '[:lower:]')
    FIAT_LC=$(echo "{{fiat}}" | tr '[:upper:]' '[:lower:]')

    echo "Scoring strategy with {{token1}}/{{fiat}}, {{token2}}/{{fiat}}, and {{token1}}/{{token2}} for team {{team}}..."
    echo "Initial balances: {{token1}}={{token1_balance}}, {{token2}}={{token2_balance}}, {{fiat}}={{fiat_balance}}"
    FEE_DECIMAL=$(echo "scale=4; {{fee}}/10000" | bc)
    FEE_PERCENT=$(echo "scale=2; {{fee}}/100" | bc)
    echo "Trading fee: {{fee}} basis points ($FEE_DECIMAL or ${FEE_PERCENT}%)"

    python -m exchange.score {{DATA}}/submission.csv \
        --data {{DATA}}/test.csv \
        --token1_balance {{token1_balance}} \
        --token2_balance {{token2_balance}} \
        --fiat_balance {{fiat_balance}} \
        --fee {{fee}}

# print current configuration
print:
    #!/usr/bin/env bash
    echo "Trading Configuration:"
    # Convert unix timestamps to human-readable dates
    START_DATE=$(date -r $(( {{START_TS}} / 1000 )) "+%Y-%m-%d %H:%M:%S")
    END_DATE=$(date -r $(( {{END_TS}} / 1000 )) "+%Y-%m-%d %H:%M:%S")
    echo "  Start: $START_DATE ({{START_TS}})"
    echo "  End: $END_DATE ({{END_TS}})"
    echo "  Timeframe: {{TIMEFRAME}}"
    # Calculate decimal and percentage representations of the fee
    FEE_DECIMAL=$(echo "scale=4; {{FEE}}/10000" | bc)
    FEE_PERCENT=$(echo "scale=2; {{FEE}}/100" | bc)
    echo "  Fee: {{FEE}} basis points ($FEE_DECIMAL or ${FEE_PERCENT}%)"
    echo ""
    echo "Default Portfolio:"
    echo "  {{TOKEN_1}}: {{TOKEN_1_BALANCE}}"
    echo "  {{TOKEN_2}}: {{TOKEN_2_BALANCE}}" 
    echo "  {{FIAT}}: {{FIAT_BALANCE}}"
    echo ""
    echo "Default Team: {{TEAM}}"
    echo ""
    echo "Commands:"
    echo "  Download market data: just download [token1] [token2] [fiat]"
    echo "  Archive strategy: just tar [team]"
    echo "  Score strategy: just score [team] [token1] [token2] [fiat] [token1_balance] [token2_balance] [fiat_balance] [fee]"
    echo ""
    echo "Examples:"
    echo "  just download                       # Uses default tokens: {{TOKEN_1}}, {{TOKEN_2}}, {{FIAT}}"
    echo "  just download SOL AVAX USDC         # Downloads SOL/USDC, AVAX/USDC, SOL/AVAX data"
    echo "  just tar                            # Uses default team: {{TEAM}}"
    echo "  just tar beta                       # Creates beta_submission.tgz"
    echo "  just score                          # Uses default team and tokens with default balances"
    echo "  just score beta SOL AVAX USDC       # Scores beta team with SOL/AVAX/USDC data"
    echo "  just score beta SOL AVAX USDC 50 5 1000000  # Custom initial balances"
    echo "  just score beta SOL AVAX USDC 50 5 1000000 5  # Custom fee (5 bps = 0.05%)"

# remove downloaded data and generated archives
clean:
    rm -f data/*.parquet && \
    rm -f *_submission.tgz