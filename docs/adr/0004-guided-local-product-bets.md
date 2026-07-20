# ADR 0004: Make guided product bets the primary experience

## Status

Accepted after the complete product-journey origin approval on 2026-07-20.

## Context

The repository workbench proved origin governance but required a person to
understand YAML, layer files, and projection internals before receiving value.
That inverted the intended delegation: a product owner should start with an
actor, pain, vocabulary, and outcomes, while implementation details remain
auditable but optional.

The MVP must also remain locally runnable without authentication, tenancy, or a
hosted service. Judges need a keyless full journey, while real product bets must
retain the GPT-5.6 path and make external work explicit.

## Decision

The browser root is a local product-bet workspace. Each bet progresses through
problem discovery, outcome design, verification approval, informed generation,
and use-and-learning. State is written atomically under ignored local data and
can be resumed from the product list. Raw origin files remain available only in
audit mode.

Generation starts only after the request maximum, variable-cost guardrail,
projection outcomes, and cache state are shown. It runs in a background worker
so progress and recoverable failure remain visible. An approved semantic bundle
is reused across interruption, repeat generation, and deterministic renderer
upgrades when the origin and pins are unchanged.

The browser can use the real GPT-5.6 provider or an explicitly selected sample
provider. `demo-web.sh` selects the sample provider for a keyless, inspectable
evaluation path; normal `dodai showcase` uses GPT-5.6 for uncached approved
origins.

## Consequences

- A product owner can complete the vertical journey without editing YAML.
- How vocabulary is intercepted before a story becomes authoritative.
- Verification and model use each have an explicit human gate.
- Generated behavior, verification, stakeholder meaning, governed change, and
  telemetry learning are connected inside one resumable bet.
- Local state is deliberately single-user and process-local; SaaS, auth,
  multitenancy, and deployment remain outside the MVP.
- The audited renderer set still bounds executable generation to supported
  product shapes; arbitrary repository generation is not implied.
