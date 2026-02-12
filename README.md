# DD CLI - Datadog Command Line Interface

A comprehensive CLI tool for querying Datadog APIs across monitors, metrics, events, logs, APM, and database monitoring.

## Quick Start

```bash
# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Configure
cp .envrc.example .envrc
# Edit .envrc with your Datadog API keys
source .envrc

# Test
pytest tests/ -v
# Expected: 176 passed

# Use
./scripts/dd_cli.sh apm services
./scripts/dd_cli.sh apm traces web-prod-blue --from 1h
```

## Features

### Implemented
- **monitor** - Monitor management
- **metric** - Metric queries
- **event** - Event management
- **host** - Host information
- **apm** - APM (services, traces, analytics)

### Coming Soon
- **logs** - Log querying
- **dbm** - Database monitoring
- **investigate** - Investigation workflows

## Documentation

- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - Feature roadmap
- [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) - Migration details

## Testing

```bash
pytest tests/ -v                              # Run all tests
pytest tests/commands/test_apm.py -v          # Run APM tests
pytest tests/ --cov=dd --cov-report=html      # Coverage report
```

## Development

Follow strict TDD (RED-GREEN-REFACTOR):
1. Write failing test
2. Make test pass
3. Refactor
4. Verify coverage (>90% target)

See `dd/commands/apm.py` as reference implementation.

## Stats

- **Total Tests**: 176
- **Coverage**: 96%
- **Commands**: 5 (monitor, metric, event, host, apm)
- **APM Tests**: 15 (94% coverage)
