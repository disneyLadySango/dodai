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

The product begins with a guided Japanese journey rather than an internal
specification editor. A product owner names a bet, describes an actor and pain,
recovers intent when solution vocabulary appears, defines business terms and
falsifiable outcomes, and approves proposed verification before generation.
Dodai shows the maximum model-request count, cost guardrail, and cache state
before explicit consent.

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

The origin workbench makes this discipline operational. A person can edit any
of the four layers, validate a candidate without changing the authoritative
origin, inspect every affected record and projection, and explicitly approve or
reject the complete change. Approval regenerates all active projections and
records the connected decision history. Failed or stale candidates cannot
partially change the origin. Projection pins are attributed separately, and
`dodai init` applies the same discipline to a second product intent.

After generation, the product owner can immediately operate the generated
experience, see behavioral verification and stakeholder meaning from the same
origin, request a plain-language change, inspect its actual affected records and
projections, and approve or reject atomic regeneration. Outcome evidence
produces an explained continue, revise-verification, or end-bet decision. Every
product bet is resumable with its current stage, next decision, failures,
approvals, and learning history visible.

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
projections were produced by verified live GPT-5.6 requests: the initial
vertical slice and one approved origin evolution. Tests and demos reuse the
active approved bundle and do not spend additional model tokens.

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

Then open <http://127.0.0.1:8000>. Create a product bet and complete the guided
journey through pain, outcomes, verification approval, generation consent, and
the runnable result. Submit a valid email, repeat it to see duplicate handling,
and try an invalid value. Request a plain-language change to inspect its impact,
then enter telemetry to exercise continue, verification-change, and exit
decisions. Product state and registrations remain local and survive restarts.

`demo-web.sh` uses the inspectable sample provider, so this full journey is
keyless and makes no API request. Audit mode at `/workbench` exposes the complete
four-layer source and the repository proof remains at `/proof`.

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

Both demos make no OpenAI API request. The terminal demo is read-only with
respect to the checkout; browser product state stays in ignored local data under
`.dodai/workspaces/`.

## Submission fields still requiring the owner

- Public YouTube demo URL
- Primary Codex `/feedback` Session ID
- Final repository commit SHA in private local submission state
- Devpost receipt confirmation
