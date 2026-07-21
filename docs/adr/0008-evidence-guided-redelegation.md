# ADR 0008: Re-delegate from immutable interaction evidence

Status: Accepted

## Context

A passing automated check proves that delegated behavior matches its current
verification. It does not prove that operating the result produced the approved
business outcome. Asking a person to identify an origin layer would transfer
Dodai's diagnostic responsibility back to the user.

## Decision

After operating a delegated result, a person answers three plain questions:
whether the pain remains, whether the behavior completed, and whether the
approved outcome occurred. They also record one observed fact.

Dodai stores that interaction evidence as an immutable record linked to the
delegation attempt and derives the learning boundary itself. When behavior
passes but the outcome does not occur, Dodai prepares a Layer 4 candidate only.
The approved story and acceptance criteria remain byte-identical. Re-delegation
starts only after explicit approval of the revised verification.

Every completed delegation attempt is archived. After re-delegation, Dodai
compares the latest two attempts and presents their artifacts, verification,
and prior interaction observation together.

## Consequences

- People report observable facts instead of selecting a technical failure layer.
- An outcome gap cannot silently rewrite the problem or business outcome.
- Verification revision and repository work remain separately consented actions.
- Attempt evidence is retained for comparison instead of being overwritten.
- Problem invalidation and presentation failure are diagnosed and recorded, but
  their governed revision journeys remain future vertical slices.
