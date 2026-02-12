#!/bin/bash
# Wrapper script for dd CLI - automatically activates venv

set -euo pipefail

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Run dd CLI with all arguments passed through
dd "$@"
