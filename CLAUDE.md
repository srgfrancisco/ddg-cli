# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DD CLI is a Python CLI tool for querying Datadog APIs, built for Kojo troubleshooting. It covers monitors, metrics, events, hosts, and APM. Requires Python 3.10+.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
pytest tests/commands/test_apm.py -v          # single module
pytest tests/commands/test_apm.py::test_name   # single test
pytest tests/ --cov=dd --cov-report=html       # coverage

# Code quality
black dd/ tests/                               # format (line-length: 100)
ruff check dd/ tests/                          # lint (line-length: 100)
mypy dd/                                       # type check

# Run CLI
source .envrc                                  # load DD_API_KEY, DD_APP_KEY
dd monitor list --state Alert
dd apm services
```

## Architecture

**Entry point**: `dd.cli:main` — a Click group that registers command subgroups.

**Command structure** (`dd/commands/`): Each file defines a Click group with subcommands. Commands call `get_datadog_client()` to get an API client, then use Rich for output formatting.

```
dd apm {services, traces, analytics}
dd monitor {list, get, mute, unmute, validate}
dd metric {query, search, metadata}
dd event {list, get, post}
dd host {list, get, totals}
```

**Key modules**:
- `dd/client.py` — `DatadogClient` wraps `datadog_api_client` SDK, exposing V1 APIs (monitors, metrics, events, hosts, tags) and V2 APIs (logs, spans). Use `get_datadog_client()` to instantiate.
- `dd/config.py` — `DatadogConfig` (Pydantic BaseSettings) loads from env vars (`DD_API_KEY`, `DD_APP_KEY`, `DD_SITE`). Supports region shortcuts (us, eu, us3, us5, ap1, gov).
- `dd/utils/error.py` — `@handle_api_error` decorator with retry logic (exponential backoff on 429/5xx, immediate exit on 401/403).
- `dd/utils/time.py` — `parse_time_range()` handles relative (1h, 24h, 7d) and ISO datetime formats, returns Unix timestamps.
- `dd/utils/tags.py` — Tag parsing and display formatting.

## Testing Patterns

Tests use `unittest.mock` with Click's `CliRunner`. Key fixtures from `tests/conftest.py`:
- `mock_client` — Mock with `.monitors`, `.hosts`, `.metrics`, `.events`, `.spans` attributes
- `runner` — `CliRunner()` instance
- Factory functions: `create_mock_monitor()`, `create_mock_host()`, `create_mock_span()`, etc.

Standard test pattern: patch `get_datadog_client` to return `mock_client`, invoke command via `runner`, assert on output and exit code.

## Development Methodology

Strict TDD (RED-GREEN-REFACTOR). Coverage target >90%. Reference implementation: `dd/commands/apm.py`.

## Planned Features

See `IMPLEMENTATION_PLAN.md`: logs, database monitoring, investigation workflows.
