#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

echo "Starting the generated dodai waitlist at http://127.0.0.1:8000"
echo "Press Ctrl+C to stop. No OpenAI API request is made."
exec uv run python projections/developer/waitlist.py --host 127.0.0.1 --port 8000
