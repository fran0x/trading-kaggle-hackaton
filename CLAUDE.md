# CLAUDE.md - Junz Trading Strategy Framework

## Build & Run Commands
- Install dependencies: `just i` or `just install`
- Download market data: `just d` or `just download`
- Create submission archive: `just t` or `just tar`
- Score strategy: `just s` or `just score`
- Clean data: `just c` or `just clean`
- Build Docker: `just b` or `just build`
- View configuration: `just p` or `just print`
- Change trading pair: Edit the `SYMBOL` variable in the justfile (e.g., `SYMBOL := "ETH/USDT"`)
- Run individual test: Create tar first with `just tar`, then run scoring with `just score`

## Code Style Guidelines
- **Imports**: Standard library first, then third-party, then local modules
- **Variables**: Use snake_case for variables and functions
- **Constants**: Use UPPERCASE for constant values
- **Type Hints**: Add typing where helpful (e.g., function args and returns)
- **Docstrings**: Use triple quotes for module and function documentation
- **Error Handling**: Use try/except blocks for API calls and data processing
- **Data Processing**: Prefer pandas/numpy vectorized operations over loops
- **Formatting**: 4-space indentation, 88-character line limit
- **Testing**: Document assumptions and edge cases in comments
- **Module Imports**: Always use fully qualified package names (e.g., `strategy.basic` not `basic`)
- **Package Structure**: All imports should be at the top of the file, not inside functions

## Project Structure
- `exchange/`: Trading engine and backtest framework
- `strategy/`: Trading strategy implementation
  - `main.py`: Entry point for strategy
  - `basic.py`: Implementation of mean-reversion strategy
- `data/`: Market data storage
- `scripts/`: Utility scripts for data download and processing