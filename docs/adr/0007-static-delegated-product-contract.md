# ADR 0007: Serve a bounded static delegated product

Status: Accepted

## Context

Repository changes and passing verification are necessary evidence, but they do
not let a product owner experience the behavior being judged. Starting an
arbitrary generated server would add dependency installation, process
lifecycle, port allocation, network access, and command-execution risks to the
local MVP.

Codex automation can also inherit unrelated user configuration. Required MCP
servers, profiles, approval policies, or shell environment settings can make a
bounded non-interactive attempt fail or expose credentials to generated test
commands.

## Decision

The projection-side delivery contract requires an immediately usable static web
result rooted at `product/index.html` in the product-bet-owned repository.
Codex remains free to choose its HTML, CSS, JavaScript, structure, and testing
approach within that boundary.

Dodai validates that entry point before accepting delegation evidence and serves
only files that resolve inside `product/`. The product is embedded in a
sandboxed frame and receives a restrictive content security policy that blocks
network connections. Symlinks and traversal outside the delivery root are
rejected.

Real automation uses `codex exec --ignore-user-config` with an explicit
`workspace-write` sandbox, no interactive approvals, and a trimmed shell
environment whose default secret exclusions remain active. CLI authentication
is retained, while unrelated profiles, MCP requirements, and repository-external
configuration do not control the attempt.

Failures are reduced to bounded user-facing categories such as authentication,
capacity, timeout, invalid result, or missing verification. Raw stdout, stderr,
environment values, and session identifiers are not persisted or displayed.
If Codex finishes successfully but its final structured message is absent, Dodai
recovers the handoff only when the static entry point, stakeholder explanation,
and at least one successful verification command are independently observable.
The recovered summary is deterministic and clearly attributed to Dodai rather
than treated as a model claim.

## Consequences

- A person can operate the delegated result from the same evidence and adoption
  screen.
- The MVP avoids starting arbitrary generated processes or installing generated
  dependencies.
- Products requiring server-side behavior are outside this delivery contract
  until a separately governed execution boundary is introduced.
- Ignoring user configuration improves repeatability but intentionally prevents
  personal MCP servers and profiles from influencing delegated work.
