# ADR 0005: Make presentation evidence explicit

Status: Accepted

## Context

An origin digest proves that files were generated together, but it does not tell
a product owner which user pain, outcome, and verification justify each active
presentation. A runnable sample can also be mistaken for Dodai's product value,
and raw operational telemetry does not explain which layer failed.

## Decision

Projection-side `presentation-map.yaml` pins explicitly connect every active
developer and stakeholder presentation to an existing story, acceptance
criterion, and test specification. Generation validates complete coverage and
writes the auditable mapping to `projections/evidence.yaml`.

The guided result keeps the approved actor, pain, and outcome visible, labels
the waitlist journey as an interchangeable proof sample, and reports satisfied
and unsatisfied verification. Outcome evidence is classified into problem
understanding, verification approach, produced presentation, or inconclusive;
each diagnosis states what remains fixed and what changes next.

## Consequences

- An orphan active presentation prevents accepted generation.
- Evidence metadata changes the projection identity because its pin is an
  explicit projection-side decision.
- Reusable workspaces receive the same mapping without product-specific code.
- The current diagnosis is deterministic and local; production telemetry
  integration remains outside the MVP.
