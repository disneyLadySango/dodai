# dodai Origin

This directory is the authoritative origin for dodai. It records intent and
constraints; generated code, tests, documents, decisions, and dependency pins
are projections and do not belong here.

## Layer files

| Layer | File | Responsibility |
| --- | --- | --- |
| 1 | `01-definitions.yaml` | Defines the vocabulary available to lower layers. |
| 2 | `02-user-stories.yaml` | Records actors and durable pains without solution choices. |
| 3 | `03-acceptance-criteria.yaml` | Records falsifiable outcomes, guardrails, and exit conditions. |
| 4 | `04-test-specifications.yaml` | Defines observable verification of layer 3 without implementation nouns. |

The representation is deliberately constrained YAML: stable identifiers,
closed field sets, explicit references, and short declarative values. YAML is
only the human-auditable container for the origin, not a product mechanism or
a requirement imposed on projections.

## Schema

Every layer document has exactly these top-level fields:

- `origin`: the stable product identifier (`dodai`)
- `layer`: the layer number and name
- `revision`: a positive integer changed only when that layer changes
- one layer-specific collection

Layer-specific records use stable lowercase identifiers. References point from
less stable layers to more stable layers. A record is never silently repurposed:
change its content for the same meaning, or retire it and create a new ID when
the meaning changes.

Layer 1 terms declare where they may be used. Boundary terms declare language
that is forbidden in stories or test specifications. Inflected forms and
case variants count as the same term. A warning is sufficient for the first
MVP; a clean vocabulary check has no warnings.

Layer 2 records contain only `id`, `who`, and `pain`. They must not contain a
desired feature, mechanism, interface, architecture, or technology.

Layer 3 records contain an observable statement and a classification:
`outcome`, `guardrail`, or `exit_condition`. Quantitative conditions include
their measure, comparator, threshold, and observation scope.

Layer 4 records contain `id`, `verifies`, `given`, `when`, and `then`. Each
record references one or more layer 3 IDs. Together, the records must cover
every active layer 3 criterion. They describe externally observable behavior
and must not name a data representation, storage structure, framework,
library, protocol, or internal component.

## Change discipline

1. Change the highest layer whose meaning actually changed.
2. Treat the change as a candidate revision; the current origin remains
   authoritative while its lower-layer consequences are reviewed.
3. Derive or revise layer 4 and obtain explicit human approval before changing
   product code, tests, documents, or any other projection.
4. After approval, make the complete origin revision authoritative and
   regenerate every active projection as one change.
5. If a guardrail is breached, keep layers 2 and 3 fixed and revise layer 4.
6. If an exit condition is reached, append a losing record to the affected
   story before proposing another approach.
7. Decisions that merely stabilize regeneration belong in projection-side
   decision records or pins, never in this directory.

An origin-review change deliberately leaves committed projections at the last
approved origin. A rebuild mismatch is therefore expected until the candidate
revision is approved and projections are regenerated. Origin lint, reference
integrity, vocabulary boundaries, and complete layer-3 coverage must pass before
approval is requested.
