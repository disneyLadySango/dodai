# ADR 0002: Apply origin changes as governed transactions

## Status

Accepted after layer-four approval on 2026-07-20.

## Context

An origin editor that writes directly to authoritative layer files can leave the
origin, projections, verification, and history in different states. A preview
also becomes unsafe if the origin changes between inspection and approval.

## Decision

Dodai treats an edit as a candidate revision addressed by the digest of its
base origin, target layer, and proposed meaning. Preview validates an isolated
origin and calculates downstream record and projection impact without changing
the authoritative origin.

Approval first validates and regenerates the complete candidate in isolation.
Only a successful result replaces the authoritative layer and active
projections. The base digest prevents approval after concurrent origin change.
The accepted change connects the approver, before and after origin identities,
validation result, and resulting projection identity.

Candidate and history persistence are local operational projections. Their
current locations are ignored implementation details, not origin requirements.

## Consequences

- Preview and rejection cannot modify the authoritative origin.
- Model, validation, or rendering failure cannot partially approve a change.
- A stale candidate must be previewed again.
- History is produced by approval rather than reconstructed afterward.
