# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ddg-cli is a modern CLI for the Datadog API. Like Dogshell, but better. Rich terminal output, APM/logs/DBM support, retry logic, investigation workflows. Requires Python 3.10+.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
pytest tests/commands/test_apm.py -v          # single module
pytest tests/commands/test_apm.py::test_name   # single test
pytest tests/ --cov=ddg --cov-report=html      # coverage

# Code quality
black ddg/ tests/                              # format (line-length: 100)
ruff check ddg/ tests/                         # lint (line-length: 100)
mypy ddg/                                      # type check

# Run CLI
export DD_API_KEY=... DD_APP_KEY=...
ddg monitor list --state Alert
ddg apm services
ddg logs search "status:error" --service my-api
ddg dbm queries --sort-by avg_latency
ddg investigate latency my-service --threshold 500
```

## Architecture

**Entry point**: `ddg.cli:main` — a Click group that registers command subgroups.

**Command structure** (`ddg/commands/`): Each file defines a Click group with subcommands. Commands call `get_datadog_client()` to get an API client, then use Rich for output formatting.

```
ddg monitor {list, get, mute, unmute, validate}
ddg metric  {query, search, metadata}
ddg event   {list, get, post}
ddg host    {list, get, totals}
ddg apm     {services, traces, analytics}
ddg logs    {search, tail, query, trace}
ddg dbm     {hosts, queries, explain, samples}
ddg investigate {latency, errors, throughput, compare}
```

**Key modules**:
- `ddg/client.py` — `DatadogClient` wraps `datadog_api_client` SDK, exposing V1 APIs (monitors, metrics, events, hosts, tags) and V2 APIs (logs, spans). Use `get_datadog_client()` to instantiate.
- `ddg/config.py` — `DatadogConfig` (Pydantic BaseSettings) loads from env vars (`DD_API_KEY`, `DD_APP_KEY`, `DD_SITE`). Supports region shortcuts (us, eu, us3, us5, ap1, gov).
- `ddg/utils/error.py` — `@handle_api_error` decorator with retry logic (exponential backoff on 429/5xx, immediate exit on 401/403).
- `ddg/utils/time.py` — `parse_time_range()` handles relative (1h, 24h, 7d) and ISO datetime formats, returns Unix timestamps.
- `ddg/utils/tags.py` — Tag parsing and display formatting.

## Testing Patterns

Tests use `unittest.mock` with Click's `CliRunner`. Key fixtures from `tests/conftest.py`:
- `mock_client` — Mock with `.monitors`, `.hosts`, `.metrics`, `.events`, `.spans`, `.logs`, `.dbm` attributes
- `runner` — `CliRunner()` instance
- Factory functions: `create_mock_monitor()`, `create_mock_host()`, `create_mock_span()`, `create_mock_log()`, `create_mock_dbm_host()`, `create_mock_dbm_query()`, `create_mock_dbm_sample()`

Standard test pattern: patch `get_datadog_client` to return `mock_client`, invoke command via `runner`, assert on output and exit code.

## Development Methodology

Strict TDD (RED-GREEN-REFACTOR). Coverage target >90%. Reference implementation: `ddg/commands/apm.py`.
