# dodai

dodai is an origin-driven development tool for product managers and engineers
who delegate implementation to AI agents. One human-auditable origin produces
executable developer artifacts and stakeholder communication, while fast tests
and simulated telemetry keep implementation failures separate from failed
product bets.

Built for the OpenAI Build Week 2026 Developer Tools track.

## What the vertical slice demonstrates

The bundled waitlist journey deliberately stays narrow:

1. Validate the four origin layers and their vocabulary boundaries.
2. Ask GPT-5.6 to derive one structured semantic content bundle.
3. Render executable code, behavioral tests, and a stakeholder brief together.
4. Reuse an origin-addressed approved bundle when the origin is unchanged.
5. Evaluate simulated telemetry to propose new verification or record a lost bet.
6. Discard and rebuild projections, then report any leaked decision as a diff.

The [origin](origin/README.md) is authoritative. The committed
[projections](projections/) are disposable evidence of what can be regenerated.

## Requirements

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/)
- macOS, Linux, or Windows with a POSIX-like shell for the commands below
- An OpenAI API key only when deriving fresh content with GPT-5.6

## Setup

```bash
git clone https://github.com/disneyLadySango/dodai.git
cd dodai
uv sync --extra dev
```

## Run the keyless demo

The sample provider exercises the complete deterministic projection path
without credentials:

```bash
uv sync --locked --extra dev
bash scripts/demo.sh
```

The script validates the origin, shows the committed GPT-5.6 stakeholder
projection, proves a cache-only rebuild, and evaluates a guardrail breach in a
disposable copy. It does not modify the repository or call the OpenAI API.

The individual commands are:

```bash
uv run dodai --root . lint
uv run dodai --root . project --sample
uv run dodai --root . project --sample
uv run dodai --root . rebuild-test
```

The repository includes an approved bundle for its current origin, so repeated
projection reports `stable` without an API request. A new origin digest reports
`changed` when its first approved bundle is produced. Generated developer code
and tests live under `projections/developer/`, while the shared stakeholder
explanation lives under `projections/stakeholder/`.

## Derive content with GPT-5.6

Set `OPENAI_API_KEY` in your environment or secret manager. Never add it to this
repository. Then force semantic re-derivation:

```bash
uv run dodai --root . project --refresh
```

dodai uses the OpenAI Responses API with the `gpt-5.6` alias and strict
structured output. GPT-5.6 performs the judgment-heavy translation from origin
intent into role-neutral product meaning. Audited renderers own executable
structure, and the approved semantic bundle is cached by origin digest so later
regeneration is stable. The choice is recorded in
[ADR 0001](docs/adr/0001-bounded-model-generation.md).

OpenAI documents `gpt-5.6` as the GPT-5.6 Sol alias and supports both the
Responses API and structured outputs for this model:
[model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-sol).

A live GPT-5.6 generation was verified on 2026-07-20. The committed semantic
bundle and both role projections are the resulting reproducible evidence; no
API key or request identifier is stored in the repository.

## Exercise the outer loop

A guardrail breach keeps the story and acceptance criterion fixed and proposes
revised verification under `.dodai/proposals/`:

```bash
uv run dodai --root . telemetry examples/telemetry/guardrail-breach.yaml
```

The exit-condition example appends an idempotent losing record to the affected
story. Run it only in a disposable checkout because it intentionally changes
the origin:

```bash
uv run dodai --root . telemetry examples/telemetry/exit-condition.yaml
```

## Testing

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
uv run pytest -q projections/developer
uv run dodai --root . lint
uv run dodai --root . rebuild-test
uv build
```

## Architecture

```text
four-layer origin + projection pins
              |
              v
      vocabulary validation
              |
              v
 GPT-5.6 semantic derivation ---> origin-addressed approved cache
              |                              |
              +------------------------------+
                             |
                             v
                deterministic renderers
                   /                 \
                  v                   v
       developer code + tests   stakeholder brief
                  \                   /
                   +---- rebuild ----+

simulated telemetry ---> guardrail proposal | story-level losing record
```

Technical choices are projections, not origin requirements. They are retained
under `docs/adr/` and `pins/` to make regeneration reviewable and stable.

## Codex collaboration

The product contract intentionally delegated technical How to Codex. The human
owner supplied the problem framing, four-layer discipline, falsifiable outcomes,
guardrails, exit condition, and the decision to rename the product from Genten
to dodai. Codex designed the representation, derived layer-4 test specifications,
selected the bounded GPT-5.6 architecture, implemented the vertical slice with
red-green-refactor cycles, and verified the resulting projections.

The primary Codex session identifier is submitted privately through Devpost and
is never stored in this public repository.

## Human decisions

- Manage agents by falsifiable outcomes, not prescribed technical methods.
- Keep user stories free of solution vocabulary.
- Keep test specifications free of implementation nouns.
- Separate guardrail breaches from exit conditions and retain losing records.
- Prove one complete vertical slice before expanding breadth.
- Name the product **dodai (土台)**.

## Hackathon status

The repository checklist is maintained in [HACKATHON.md](HACKATHON.md). A live
demo, video, and Devpost submission are not claimed until they are actually
observed.

Submission drafts and the under-three-minute English shot list are in
[`submission/`](submission/DEVPOST.md).

## License

Licensed under the [MIT License](LICENSE).
