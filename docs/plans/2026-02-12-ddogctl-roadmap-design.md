# ddogctl Roadmap: From Dogshell Replacement to World-Class CLI

**Date:** 2026-02-12
**Status:** Approved

## Context

ddogctl currently has 8 command groups (~35 subcommands) covering monitors, metrics, events, hosts, APM, logs, DBM, and investigation workflows. This plan closes the gap with Dogshell, then pushes beyond it with CLI UX inspired by kubectl/awscli/gcloud and machine-readable output for agentic workflows.

### Gap Analysis Sources
- **Dogshell** (datadogpy): 19 modules — dashboard, SLO, downtime, service_check, tag, comment, search, security_monitoring, dashboard_list, screenboard, timeboard, plus monitor/metric/event/host
- **Datadog API surface**: 20+ API categories including synthetics, incidents, notebooks, RUM, CI visibility, users/RBAC, usage metering, audit
- **CLI UX benchmarks**: kubectl (profiles, apply, watch, completion), awscli (--query JMESPath, --profile, --output), gcloud (config configurations, formats, streaming)

## Phase 1: API Parity with Dogshell

**Goal:** Make ddogctl a complete Dogshell replacement.

### 1.1 Monitor CRUD Completion

Current: `monitor list|get|mute|unmute|validate`

**New subcommands:**
```
ddogctl monitor create --type "metric alert" --query "avg(last_5m):..." \
    --name "My Monitor" --message "@slack" --tags "env:prod" --priority 3
ddogctl monitor create -f monitor.json
ddogctl monitor update <monitor_id> --name "New Name" --query "..."
ddogctl monitor update <monitor_id> -f monitor.json
ddogctl monitor delete <monitor_id> [--confirm]
ddogctl monitor mute-all
ddogctl monitor unmute-all
```

**Design:**
- `create` and `update` support inline flags AND `-f <file>` for JSON input (kubectl pattern)
- `delete` requires `--confirm` flag or shows interactive confirmation prompt
- `mute-all`/`unmute-all` create/cancel a downtime over `*`
- `-f` accepts JSON matching the Datadog monitor API schema

**Client:** Add `monitors.create_monitor()`, `monitors.update_monitor()`, `monitors.delete_monitor()`

**Tests:** Mock create/update/delete API calls, test file input parsing, test confirmation prompt, test mute-all/unmute-all

### 1.2 Dashboard Management

**New command group:**
```
ddogctl dashboard list [--tags TAG] [--format json|table]
ddogctl dashboard get <dashboard_id> [--format json|table]
ddogctl dashboard create -f dashboard.json
ddogctl dashboard create --title "My Dashboard" --layout-type ordered --description "..."
ddogctl dashboard update <dashboard_id> -f dashboard.json
ddogctl dashboard delete <dashboard_id> [--confirm]
ddogctl dashboard export <dashboard_id> -o dashboard.json
ddogctl dashboard clone <dashboard_id> --title "Copy of ..."
```

**Design:**
- `list` shows: id, title, layout_type, author, created_at, url
- `create` from file is the primary workflow; inline flags set metadata only (widgets are always from file)
- `export` (new vs Dogshell) dumps dashboard to JSON for "export -> modify -> apply" GitOps loop
- `clone` (new vs Dogshell) duplicates a dashboard with a new title
- `--layout-type` choices: `ordered` (grid) or `free` (freeform)

**Client:** Add `dashboards` attribute wrapping `DashboardsApi` (v1 SDK)

**Tests:** Mock all CRUD ops, test export file writing, test clone (get + create with new title)

### 1.3 SLO Management

**New command group:**
```
ddogctl slo list [--query SEARCH] [--tags TAG] [--limit N] [--format json|table]
ddogctl slo get <slo_id> [--format json|table]
ddogctl slo create --type metric --name "API Availability" \
    --thresholds "30d:99.9,7d:99.95" \
    --numerator "sum:api.requests.success{*}" \
    --denominator "sum:api.requests.total{*}" --tags "team:platform"
ddogctl slo create --type monitor --name "DB Health" \
    --monitor-ids "123,456" --thresholds "30d:99.9"
ddogctl slo create -f slo.json
ddogctl slo update <slo_id> -f slo.json
ddogctl slo update <slo_id> --name "New Name" --thresholds "30d:99.95"
ddogctl slo delete <slo_id> [--confirm]
ddogctl slo history <slo_id> --from 30d [--format json|table]
ddogctl slo export <slo_id> -o slo.json
```

**Design:**
- Two SLO types: `metric` (numerator/denominator queries) and `monitor` (monitor IDs)
- `--thresholds` compact format: `timeframe:target[,warning]` (e.g., `"30d:99.9,7d:99.95"`)
- `history` shows error budget, burn rate, status over time
- `export` for GitOps workflows

**Client:** Add `slos` attribute wrapping `ServiceLevelObjectivesApi` (v1 SDK)

**Tests:** Mock both SLO types, test threshold parsing, test history display, test export

### 1.4 Downtime Management

**New command group:**
```
ddogctl downtime list [--current-only] [--format json|table]
ddogctl downtime get <downtime_id> [--format json|table]
ddogctl downtime create --scope "env:prod" --start "now" --end "2h" \
    --message "Deploying v2.5" [--monitor-id 123]
ddogctl downtime create -f downtime.json
ddogctl downtime update <downtime_id> --end "4h" --message "Extended maintenance"
ddogctl downtime delete <downtime_id> [--confirm]
ddogctl downtime cancel-by-scope "env:prod"
```

**Design:**
- `--start` and `--end` accept relative times (`now`, `2h`, `30m`) or ISO datetimes via `parse_time_range()`
- Much friendlier than Dogshell's POSIX timestamps
- `cancel-by-scope` cancels all downtimes matching a scope (bulk operation)
- `--monitor-id` scopes downtime to a specific monitor

**Client:** Add `downtimes` attribute wrapping `DowntimesApi` (v2 SDK)

**Tests:** Mock all CRUD ops, test relative time parsing for start/end, test cancel-by-scope

### 1.5 Tag Management

**New command group:**
```
ddogctl tag list <host> [--source SOURCE] [--format json|table]
ddogctl tag add <host> <tags...> [--source SOURCE]
ddogctl tag replace <host> <tags...> [--source SOURCE]
ddogctl tag detach <host> [--source SOURCE]
```

**Design:**
- Host-centric: `add` appends, `replace` overwrites, `detach` removes all tags
- `--source` filters by tag source (chef, puppet, users, etc.)
- `TagsApi` already exists in the client — just needs command-level exposure

**Client:** Already has `tags` attribute, just expose in commands

**Tests:** Mock tag API calls, test add/replace/detach behaviors, test source filtering

### 1.6 Service Checks

**New command group:**
```
ddogctl service-check post <check_name> <host> <status> \
    [--message "Reason"] [--tags "env:prod,service:web"]
```

**Design:**
- Status accepts both numeric (0-3) and named values (ok/warning/critical/unknown)
- Fire-and-forget — service checks are one-way
- Output confirms the check was posted with check name, host, and status

**Client:** Add `service_checks` attribute wrapping `ServiceChecksApi` (v1 SDK)

**Tests:** Mock service check post, test numeric and named status values, test tag parsing

## Phase 2: CLI UX Improvements

**Goal:** Make ddogctl a joy to use interactively, on par with kubectl/awscli/gcloud.

### 2.1 Profiles + Config Management

```
ddogctl config init                           # interactive setup
ddogctl config set-profile prod --api-key xxx --app-key yyy --site us
ddogctl config set-profile staging --api-key xxx --app-key yyy --site eu
ddogctl config use-profile prod               # set default
ddogctl config list-profiles
ddogctl config get site                       # show current value
ddogctl --profile staging monitor list        # per-command override
```

**Design:**
- Config stored in `~/.ddogctl/config.toml` (TOML format)
- Env vars override profile values (backward compatible)
- `config init` runs interactive wizard: API key, app key, site selection
- Profile precedence: CLI flag > env var > active profile > defaults

### 2.2 Apply from File + Dry-Run

```
ddogctl apply -f monitor.json                 # create or update
ddogctl apply -f dashboards/ --recursive      # apply all files in directory
ddogctl apply -f slo.json --dry-run           # preview without applying
ddogctl diff -f monitor.json                  # compare file vs live state
```

**Design:**
- `apply` auto-detects resource type from JSON structure
- Resources with `id` field → update; without → create
- `--dry-run` shows what would happen without API calls
- `diff` fetches live state and shows side-by-side comparison
- Enables GitOps: store configs in git, apply via CI

### 2.3 Shell Completion + Aliases

```bash
eval "$(ddogctl completion bash)"
eval "$(ddogctl completion zsh)"
ddogctl completion fish | source

# Built-in aliases
ddogctl mon list          # monitor
ddogctl dash get abc-123  # dashboard
ddogctl dt list           # downtime
```

**Design:**
- Click has built-in shell completion support
- Aliases registered as Click group aliases
- Alias map: mon=monitor, dash=dashboard, dt=downtime, sc=service-check, inv=investigate

### 2.4 Watch Mode + Streaming

```
ddogctl monitor list --state Alert --watch
ddogctl monitor list --state Alert --watch --interval 10
ddogctl logs tail "status:error" --follow
```

**Design:**
- `--watch` re-runs command at intervals, updating terminal in-place (Rich Live)
- `--interval` sets refresh rate in seconds (default: 30)
- `--follow` on logs tail uses polling loop with cursor-based pagination
- Clean exit on Ctrl+C

## Phase 3: Agentic/Machine-Readable

**Goal:** Make ddogctl a first-class tool for AI agents and automation.

### 3.1 Structured Error Output

```json
{"error": true, "code": "AUTH_FAILED", "status": 401, "message": "Invalid API key", "hint": "Check DD_API_KEY or run ddogctl config init"}
```

**Design:**
- When `--format json`, errors output structured JSON to stderr
- When `--format table`, errors keep the current Rich display
- Dual-mode: agents get parseable errors, humans get pretty output

### 3.2 Semantic Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Authentication/authorization failure |
| 3 | Resource not found |
| 4 | Validation error |
| 5 | Rate limited (after retries exhausted) |
| 6 | Server error |

### 3.3 Composable Piping

```bash
ddogctl monitor list --state Alert --format json | ddogctl monitor mute --from-stdin
ddogctl dashboard export abc-123 | ddogctl dashboard create --from-stdin --title "Copy"
echo '{"type":"metric alert","query":"..."}' | ddogctl monitor create --from-stdin
```

**Design:**
- `--from-stdin` flag reads JSON input from stdin
- Auto-detect stdin when pipe is detected (`not sys.stdin.isatty()`)
- Combined with `--format json`, commands become composable blocks

## Phase 4: Beyond Dogshell (Future)

Stretch goals prioritized by user demand. Each is its own PR.

| Command Group | Description | API |
|---------------|-------------|-----|
| `ddogctl synthetics` | API/browser test management, trigger test runs | SyntheticsApi (v1) |
| `ddogctl incident` | Create/update/resolve incidents, list on-call | IncidentsApi (v2) |
| `ddogctl notebook` | List/create notebooks for investigations | NotebooksApi (v1) |
| `ddogctl user` | List users, manage roles | UsersApi (v2) |
| `ddogctl usage` | Usage metering, cost visibility | UsageMeteringApi (v1/v2) |
| `ddogctl rum` | RUM application data | RUMApi (v2) |
| `ddogctl ci` | CI Visibility pipeline/test data | CIVisibilityPipelinesApi (v2) |

## Implementation Order (Phase 1)

Each item is a separate worktree + PR, following strict TDD:

1. **Monitor CRUD** — extends existing command, smallest diff
2. **Tag management** — client already has TagsApi, minimal client changes
3. **Service checks** — simple fire-and-forget, quick win
4. **Dashboard management** — new group, largest scope, export/clone are novel
5. **SLO management** — new group, two SLO types to handle
6. **Downtime management** — new group, time parsing reuse

### Per-Feature Workflow

```
1. git gtr create <feature-name>
2. RED:    Write failing tests (command, client, edge cases)
3. GREEN:  Implement minimum code to pass
4. REFACTOR: Clean up, ensure patterns match apm.py reference
5. Verify: pytest, black, ruff, mypy
6. PR:     Open PR from worktree branch
7. Merge:  Squash merge to main
```

### Shared Infrastructure (before feature PRs)

- Add `--confirm` flag utility for destructive operations
- Add `-f` / `--file` input parsing utility (JSON file → dict)
- Add `export` output utility (dict → JSON file)
- These go in `ddogctl/utils/` as shared helpers

## Success Criteria

- All Dogshell commands have ddogctl equivalents (Phase 1)
- Test coverage stays >90% throughout
- All new commands follow apm.py reference patterns
- Each phase is independently shippable
