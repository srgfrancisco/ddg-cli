# ddg-cli

**A modern CLI for the Datadog API. Like Dogshell, but better.**

## Features

- Rich terminal output with tables, colors, and progress bars
- APM trace search and service listing
- Log querying with trace correlation
- Database monitoring (DBM) for slow queries and execution plans
- Investigation workflows that correlate across monitors, traces, logs, and hosts
- Retry logic with exponential backoff
- Region shortcuts (`us`, `eu`, `us3`, `us5`, `ap1`, `gov`)

## ddg-cli vs Dogshell

| Feature | ddg-cli | Dogshell |
|---|---|---|
| Rich terminal output | Yes | No |
| APM traces | Yes | No |
| Log search + correlation | Yes | No |
| Database monitoring | Yes | No |
| Investigation workflows | Yes | No |
| Retry with backoff | Yes | No |
| Active maintenance | Yes | Deprecated |

## Installation

```bash
pip install ddg-cli
```

Or with pipx:

```bash
pipx install ddg-cli
```

Or with uv:

```bash
uv pip install ddg-cli
```

## Configuration

Set the required environment variables:

```bash
export DD_API_KEY="your-api-key"
export DD_APP_KEY="your-app-key"
export DD_SITE="us"  # optional, defaults to datadoghq.com
```

### Region Shortcuts

| Shortcut | Site |
|---|---|
| `us` | `datadoghq.com` |
| `eu` | `datadoghq.eu` |
| `us3` | `us3.datadoghq.com` |
| `us5` | `us5.datadoghq.com` |
| `ap1` | `ap1.datadoghq.com` |
| `gov` | `ddog-gov.com` |

## Quick Start

```bash
# Monitors
ddg monitor list --state Alert
ddg monitor get 12345

# Metrics
ddg metric query "avg:system.cpu.user{env:prod}" --from 1h
ddg metric search "cpu"

# Events
ddg event list --from 1d --priority normal
ddg event post "Deployment" "v2.1.0 deployed to prod"

# Hosts
ddg host list --filter "env:prod"
ddg host info web-prod-01

# APM
ddg apm services
ddg apm traces my-service --from 1h

# Logs
ddg logs search "status:error" --service my-api --from 30m
ddg logs tail "env:prod" --follow

# Database Monitoring
ddg dbm slow-queries --service postgres-prod --from 1h
ddg dbm explain "SELECT * FROM users WHERE id = 1"

# Investigation Workflows
ddg investigate service my-api --from 1h
ddg investigate host web-prod-01 --from 30m
```

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for setup instructions and development guidelines.

## License

[MIT](./LICENSE)
