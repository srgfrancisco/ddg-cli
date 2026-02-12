# Migration Guide: Moving DD CLI to Standalone Repository

This guide helps you move the `dd` CLI tool from the troubleshooter workspace to a standalone Git-tracked repository.

---

## Quick Start

```bash
# 1. Create new repository location
mkdir -p ~/code/dd-cli
cd ~/code/dd-cli

# 2. Copy files
cp -r /Users/sergio.francisco/code/kojo/infrastructure/troubleshooter/dd ./
cp -r /Users/sergio.francisco/code/kojo/infrastructure/troubleshooter/tests ./
cp /Users/sergio.francisco/code/kojo/infrastructure/troubleshooter/pyproject.toml ./
cp /Users/sergio.francisco/code/kojo/infrastructure/troubleshooter/IMPLEMENTATION_PLAN.md ./

# 3. Copy and rename environment template
cp /Users/sergio.francisco/code/kojo/infrastructure/troubleshooter/.envrc ./.envrc.example
# Edit .envrc.example to remove sensitive values, keep structure

# 4. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 5. Initialize git
git init
git add .
git commit -m "chore: initial commit - dd cli with APM commands

- 176 tests, 94% coverage
- Commands: monitor, metric, event, host, apm
- Strict TDD implementation
- Ready for logs and dbm implementation"

# 6. Run tests to verify
pytest tests/ -v
# Should show: 176 passed
```

---

## Detailed Migration Steps

### Step 1: Prepare Destination

```bash
# Create directory structure
mkdir -p ~/code/dd-cli/{dd,tests,reports,scripts}
cd ~/code/dd-cli
```

### Step 2: Copy Source Code

```bash
# Set source path
SOURCE="/Users/sergio.francisco/code/kojo/infrastructure/troubleshooter"

# Copy main code
cp -r "$SOURCE/dd" ./

# Copy tests
cp -r "$SOURCE/tests" ./

# Copy configuration
cp "$SOURCE/pyproject.toml" ./

# Copy documentation
cp "$SOURCE/IMPLEMENTATION_PLAN.md" ./
cp "$SOURCE/MIGRATION_GUIDE.md" ./

# Copy CLI script
cp "$SOURCE/dd_cli.sh" ./scripts/

# Copy report template if exists
if [ -d "$SOURCE/reports" ]; then
    cp -r "$SOURCE/reports/_template.html" ./reports/ 2>/dev/null || true
fi
```

### Step 3: Create Environment Template

```bash
# Copy .envrc but sanitize
cat "$SOURCE/.envrc" | sed 's/export DD_API_KEY=.*/export DD_API_KEY="your-api-key-here"/' \
                     | sed 's/export DD_APP_KEY=.*/export DD_APP_KEY="your-app-key-here"/' \
                     > .envrc.example

# Create actual .envrc (git-ignored)
cp "$SOURCE/.envrc" ./.envrc
```

### Step 4: Create .gitignore

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/
env/

# Testing
.pytest_cache/
.coverage
htmlcov/
*.cover
.hypothesis/

# Environment
.envrc
.env
*.local

# Reports
reports/*.html
reports/*.md
!reports/_template.html

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
EOF
```

### Step 5: Create README

```bash
cat > README.md << 'EOF'
# DD CLI - Datadog Command Line Interface

A comprehensive CLI tool for querying Datadog APIs across monitors, metrics, events, logs, APM, and database monitoring.

## Features

### Implemented Commands

- **monitor** - Monitor management (list, get, mute, unmute, validate)
- **metric** - Metric queries (query, search, metadata)
- **event** - Event management (list, get, post)
- **host** - Host information (list, get, totals)
- **apm** - Application Performance Monitoring
  - `services` - List all APM services
  - `traces` - Search traces for a service
  - `analytics` - Aggregate metrics by dimensions

### Coming Soon

- **logs** - Log querying and streaming
- **dbm** - Database monitoring (queries, explain plans, samples)
- **investigate** - Automated investigation workflows

## Installation

```bash
# Clone repository
git clone <repo-url>
cd dd-cli

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .

# Configure environment
cp .envrc.example .envrc
# Edit .envrc with your Datadog API keys
source .envrc
```

## Configuration

Set these environment variables (or use `.envrc` with direnv):

```bash
export DD_API_KEY="your-datadog-api-key"
export DD_APP_KEY="your-datadog-app-key"
export DD_SITE="datadoghq.com"  # Optional, defaults to datadoghq.com
```

## Usage

### APM Commands

```bash
# List all APM services
./scripts/dd_cli.sh apm services
./scripts/dd_cli.sh apm services --format json

# Search traces
./scripts/dd_cli.sh apm traces web-prod-blue --from 1h
./scripts/dd_cli.sh apm traces web-prod-blue --filter "@http.status_code:>=500"
./scripts/dd_cli.sh apm traces marketplace-prod --from 24h --limit 100

# Analytics
./scripts/dd_cli.sh apm analytics web-prod-blue --metric count --group-by resource_name
./scripts/dd_cli.sh apm analytics web-prod-blue --metric p99 --group-by resource_name
./scripts/dd_cli.sh apm analytics marketplace-prod --metric avg --from 24h
```

### Monitor Commands

```bash
# List monitors
./scripts/dd_cli.sh monitor list --state Alert
./scripts/dd_cli.sh monitor list --state Warn --format json

# Get monitor details
./scripts/dd_cli.sh monitor get <monitor_id>

# Mute/unmute monitors
./scripts/dd_cli.sh monitor mute <monitor_id>
./scripts/dd_cli.sh monitor unmute <monitor_id>
```

### Metric Commands

```bash
# Query metrics
./scripts/dd_cli.sh metric query "avg:system.cpu.user{service:web-prod}" --from 1h

# Search metrics
./scripts/dd_cli.sh metric search "database"

# Get metadata
./scripts/dd_cli.sh metric metadata "system.cpu.user"
```

### Event Commands

```bash
# List events
./scripts/dd_cli.sh event list --sources alert --priority normal --since 24h

# Post event
./scripts/dd_cli.sh event post "Investigation Started" --text "Details" --tags "team:infra"
```

### Host Commands

```bash
# List hosts
./scripts/dd_cli.sh host list --filter "service:web"

# Get host totals
./scripts/dd_cli.sh host totals
```

## Development

### Running Tests

```bash
# Activate environment
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific module tests
pytest tests/commands/test_apm.py -v

# Check coverage
pytest tests/ --cov=dd --cov-report=html
open htmlcov/index.html
```

### Adding New Commands

Follow the strict TDD approach documented in `IMPLEMENTATION_PLAN.md`:

1. **RED**: Write failing test
2. **GREEN**: Write minimal implementation
3. **REFACTOR**: Improve code quality
4. **VERIFY**: Check coverage (>90% target)

See `dd/commands/apm.py` and `tests/commands/test_apm.py` as reference implementations.

## Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| apm | 15 | 94% |
| monitor | 40+ | 96% |
| metric | 30+ | 95% |
| event | 20+ | 94% |
| host | 30+ | 97% |
| utils | 40+ | 98% |
| **Total** | **176** | **96%** |

## Architecture

```
dd-cli/
├── dd/                    # Main package
│   ├── cli.py            # CLI entry point
│   ├── client.py         # Datadog API client wrapper
│   ├── config.py         # Configuration management
│   ├── commands/         # Command implementations
│   │   ├── apm.py       # APM commands
│   │   ├── monitor.py   # Monitor commands
│   │   ├── metric.py    # Metric commands
│   │   ├── event.py     # Event commands
│   │   └── host.py      # Host commands
│   └── utils/            # Utilities
│       ├── error.py      # Error handling
│       ├── time.py       # Time parsing
│       └── tags.py       # Tag utilities
└── tests/                # Test suite
    ├── conftest.py       # Test fixtures
    ├── commands/         # Command tests
    └── utils/            # Utility tests
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/logs-commands`)
3. Follow TDD: Write tests first, then implementation
4. Ensure all tests pass (`pytest tests/ -v`)
5. Maintain >90% coverage
6. Create pull request

## License

MIT

## Support

For implementation plans and feature roadmap, see `IMPLEMENTATION_PLAN.md`.
EOF
```

### Step 6: Set Up Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package in development mode
pip install -e .

# Or install dependencies directly
pip install click rich datadog-api-client pytest pytest-cov
```

### Step 7: Initialize Git

```bash
# Initialize repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "chore: initial commit - dd cli with APM commands

Features:
- Monitor management (list, get, mute, unmute, validate)
- Metric queries (query, search, metadata)
- Event management (list, get, post)
- Host information (list, get, totals)
- APM commands (services, traces, analytics)

Testing:
- 176 tests, 96% overall coverage
- 15 APM tests, 94% coverage
- Strict TDD implementation

Ready for:
- Logs commands implementation
- Database monitoring commands
- Investigation workflows"

# Create feature branches for upcoming work
git branch feature/logs-commands
git branch feature/dbm-commands
git branch feature/investigation-workflows

# Tag initial release
git tag -a v0.1.0 -m "Release v0.1.0: Core commands + APM"
```

### Step 8: Set Up Remote (Optional)

```bash
# Add GitHub remote (after creating repository)
git remote add origin https://github.com/your-org/dd-cli.git

# Push initial commit
git push -u origin main

# Push tags
git push --tags
```

### Step 9: Verify Everything Works

```bash
# Activate environment
source .envrc

# Run tests
pytest tests/ -v
# Expected: 176 passed in ~0.2s

# Check coverage
pytest tests/ --cov=dd --cov-report=term
# Expected: >96% coverage

# Test CLI
python -m dd.cli --help
python -m dd.cli apm --help
python -m dd.cli apm services --help

# Test with real API (if credentials configured)
./scripts/dd_cli.sh apm services
```

---

## Post-Migration Checklist

- [ ] All files copied successfully
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -e .`)
- [ ] Tests passing (176/176)
- [ ] Coverage >96%
- [ ] Git initialized with initial commit
- [ ] .gitignore created
- [ ] Environment variables configured (.envrc)
- [ ] CLI works (`python -m dd.cli --help`)
- [ ] Real API test successful (optional)
- [ ] README.md created
- [ ] Remote repository set up (optional)

---

## Troubleshooting

### Tests Fail After Migration

```bash
# Ensure you're in the virtual environment
source .venv/bin/activate

# Reinstall package
pip install -e .

# Clear pytest cache
rm -rf .pytest_cache
pytest tests/ -v
```

### Import Errors

```bash
# Check package is installed
pip list | grep dd

# If not found, reinstall
pip install -e .
```

### Environment Variables Not Loaded

```bash
# If using direnv
direnv allow

# Or manually source
source .envrc

# Verify
echo $DD_API_KEY
```

### CLI Command Not Found

```bash
# Use Python module syntax
python -m dd.cli --help

# Or make script executable
chmod +x scripts/dd_cli.sh
./scripts/dd_cli.sh --help
```

---

## Next Steps

After successful migration:

1. **Set up CI/CD**
   ```yaml
   # .github/workflows/test.yml
   name: Tests
   on: [push, pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         - uses: actions/setup-python@v2
           with:
             python-version: 3.14
         - run: pip install -e .
         - run: pytest tests/ -v --cov=dd --cov-report=xml
         - uses: codecov/codecov-action@v2
   ```

2. **Implement Phase 1: Logs**
   - Follow `IMPLEMENTATION_PLAN.md`
   - Create branch: `git checkout feature/logs-commands`
   - Implement with strict TDD
   - Target: 23 tests, >90% coverage

3. **Implement Phase 2: DBM**
   - Create branch: `git checkout feature/dbm-commands`
   - Target: 24 tests, >90% coverage

4. **Documentation**
   - Add command examples to README
   - Create user guide
   - Add API documentation

---

## Comparison: Before and After

### Before (Troubleshooter Workspace)
```
/Users/sergio.francisco/code/kojo/infrastructure/troubleshooter/
├── dd/                 # DD CLI code
├── tests/              # Tests
├── apps.md            # App configurations
├── cli-reference.md   # CLI reference
├── investigation-report.md  # Investigation notes
└── ... (other troubleshooting files)
```

### After (Standalone Repository)
```
~/code/dd-cli/          # Clean, focused repository
├── dd/                 # DD CLI code only
├── tests/              # Tests only
├── README.md          # Complete documentation
├── IMPLEMENTATION_PLAN.md  # Development roadmap
├── .git/              # Git version control
└── .github/           # CI/CD workflows
```

**Benefits:**
- ✅ Clean separation of concerns
- ✅ Version control for DD CLI
- ✅ Independent release cycle
- ✅ Easier to share/open-source
- ✅ CI/CD integration
- ✅ Clear development roadmap

---

**Questions?** Refer to `IMPLEMENTATION_PLAN.md` for development details.
