#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
demo_root="$(mktemp -d)"
trap 'rm -rf "${demo_root}"' EXIT

cd "${repo_root}"

echo "1/4 Validate the four-layer origin"
uv run dodai --root . lint

echo
echo "2/4 Show the committed GPT-5.6 stakeholder projection"
sed -n '1,24p' projections/stakeholder/brief.md

echo
echo "3/4 Prove every projection can be rebuilt without another model call"
uv run dodai --root . rebuild-test

echo
echo "4/4 Exercise a guardrail breach in a disposable project copy"
cp -R origin "${demo_root}/origin"
uv run dodai --root "${demo_root}" telemetry examples/telemetry/guardrail-breach.yaml

echo
echo "Demo complete. The repository was not modified and no API request was made."
