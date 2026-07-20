# ADR 0006: Delegate into a project-owned isolated repository

Status: Accepted

## Context

Dodai could derive a fixed executable proof sample and connect presentations to
origin evidence, but it did not yet perform the product work being delegated.
A product owner still needed to run a coding agent separately, gather changed
artifacts and verification, and reconstruct why the result should be accepted.

Running an agent against an arbitrary local path would expand the MVP trust
boundary and could modify unrelated work. Persisting raw agent events would also
risk retaining session identifiers or sensitive command output.

## Decision

Each approved product bet can start one explicitly consented delegation into a
Git repository owned by that bet under ignored local state. Dodai initializes
the repository with the approved intent and durable agent guidance, then invokes
`codex exec` in ephemeral `workspace-write` mode with that repository as the
only working root.

Codex chooses the technical method, changes the repository, adds verification,
and returns a schema-constrained result. JSONL events remain in memory only;
Dodai retains only successful command names as verification evidence. Git status
and file digests independently identify changed artifacts, and likely secrets
cause evidence acceptance to fail. Raw events, stderr, environment values,
session identifiers, and credentials are not persisted.

The browser presents file contents, verification, stakeholder meaning, and the
Story-to-AC-to-test connection together. Adoption is an explicit decision. A
re-delegation carries prior-result evidence while keeping the approved origin
unchanged.

Sample mode performs the same repository and evidence journey locally without
calling Codex or an OpenAI API.

## Consequences

- The product now demonstrates real agent delegation rather than implying that
  the waitlist proof sample is the delegated result.
- Concurrent or repeated consent cannot start duplicate attempts.
- A failed attempt is resumable without changing approved intent.
- Arbitrary existing repositories, cloud execution, authentication, deployment,
  and independent execution of untrusted project commands remain outside this
  MVP.
