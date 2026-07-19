# ADR 0001: Bound model generation to semantic content

## Status

Accepted

## Context

dodai must make meaningful use of GPT-5.6 while producing stable projections
from an unchanged origin. Asking a model to emit an unrestricted repository
would make output difficult to validate, secure, and reproduce.

## Decision

GPT-5.6 derives one structured, role-neutral content bundle from the origin.
Audited deterministic renderers turn that bundle into developer and stakeholder
projections. The bundle is cached by a digest of the complete origin and the
active projection pins. An unchanged digest reuses the exact bundle.

The default model is `gpt-5.6`, the GPT-5.6 Sol alias documented by OpenAI. A
local sample provider exists for tests and keyless evaluation, but it does not
replace the GPT-5.6 path used for real origin changes.

## Consequences

- GPT-5.6 owns the high-judgment translation from intent to shared product
  meaning.
- Executable structure remains reviewable and testable.
- Stable regeneration does not depend on sampling behavior.
- An origin change requires model access unless a matching approved bundle is
  already available.

