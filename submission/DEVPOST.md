# Devpost Submission Draft

## Project name

dodai

## Track

Developer Tools

## Tagline

Manage AI agents by product intent and falsifiable outcomes, not technical micromanagement.

## Description

When AI agents write code, tests, and documentation, those artifacts drift and
teams lose track of which one is authoritative. The usual response is a more
detailed technical specification, but that turns delegation back into
micromanagement.

dodai treats product intent as the origin and every implementation artifact as
a disposable projection. Its origin has four layers: shared definitions,
solution-free user stories, falsifiable acceptance criteria, and
implementation-independent test specifications. A vocabulary linter protects
the boundaries between those layers.

GPT-5.6 performs the judgment-heavy translation from the origin into one
structured semantic bundle. Deterministic renderers then produce executable
developer code with behavioral tests and an aligned stakeholder brief. The
bundle is addressed by the origin digest, so an unchanged origin regenerates
identical output without another model request.

The vertical slice also demonstrates the outer learning loop. Simulated
telemetry that breaches a guardrail proposes revised verification while keeping
the story and acceptance criterion fixed. Reaching an exit condition records a
lost bet so the same disproven approach is not proposed again. A rebuild test
discards projections, regenerates them from the origin, and exposes decisions
that leaked outside the authoritative intent.

## How Codex was used

The human owner defined the business problem, language boundaries, user pains,
acceptance criteria, guardrails, and exit condition. Codex was delegated the
technical How. It designed the origin representation, derived the layer-four
test specifications, selected the bounded GPT-5.6 architecture, implemented the
CLI with red-green-refactor cycles, diagnosed a long-copy defect revealed by a
live model output, and delivered the work through reviewed CI-backed pull
requests. The commit history and README preserve that collaboration.

## How GPT-5.6 was used

dodai calls the OpenAI Responses API with `gpt-5.6` and strict structured
output. GPT-5.6 translates the complete origin and projection pins into
role-neutral product meaning: audience, promise, value proposition, action, and
stakeholder summary. The committed semantic bundle and generated waitlist
projections were produced by one verified live GPT-5.6 request. Tests and demos
reuse that approved bundle and do not spend additional model tokens.

## Judge testing instructions

Requirements: Python 3.12+ and `uv`. No API key is required.

```bash
git clone https://github.com/disneyLadySango/dodai.git
cd dodai
uv sync --locked --extra dev
bash scripts/demo.sh
```

For the interactive browser showcase:

```bash
bash scripts/demo-web.sh
```

Then open <http://127.0.0.1:8000>. The first screen explains the repository-backed
origin-to-projection lineage. Run the isolated guardrail scenario, then open the
generated product and submit a valid email. Repeat it to see duplicate handling,
and try an invalid value. Registrations remain local and survive server restarts.

For the complete verification suite:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
uv run pytest -q projections/developer
uv run dodai --root . rebuild-test
uv build
```

Both demos make no OpenAI API request. The terminal demo and guardrail scenario
are read-only with respect to the checkout; waitlist registration writes only
ignored local sample data under `.dodai/demo/`.

## Submission fields still requiring the owner

- Public YouTube demo URL
- Primary Codex `/feedback` Session ID
- Final repository commit SHA in private local submission state
- Devpost receipt confirmation
