# ADR 0009: Repair failed behavior without revising origin

Status: Accepted

## Context

Interaction evidence can show that produced behavior did not complete as
approved. This differs from behavior that passes verification but does not
produce the business outcome. The latter requires a Layer 4 revision; the
former means the current Presentation failed the already approved origin.

## Decision

Dodai prepares a Presentation repair plan when plain interaction answers show a
behavior failure. It stores the failed observation against the delegation
attempt and records the complete origin snapshot digest. It does not prepare an
origin candidate or call GPT-5.6 again.

A person explicitly approves one repair attempt. Codex receives the unchanged
approved intent and the failed observation, then reconstructs the produced
behavior in the same isolated repository. Dodai verifies the origin snapshot
again before accepting the attempt evidence.

The comparison may state that repaired behavior passed verification. It must
continue to state that the business outcome is unconfirmed until a person
operates the repaired result and records new interaction evidence.

## Consequences

- The inner loop can replace disposable Presentation without authority drift.
- Behavior repair does not consume a new GPT-5.6 semantic derivation.
- Repair remains bounded by explicit consent and one delegation claim.
- Prior attempt and interaction evidence remain immutable and comparable.
- A passing repair verification is not presented as empirical outcome success.
