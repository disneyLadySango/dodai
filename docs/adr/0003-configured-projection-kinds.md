# ADR 0003: Select reusable projection kinds through pins

## Status

Accepted after layer-four approval on 2026-07-20.

## Context

The first renderer proved one waitlist journey but embedded that product shape
inside Dodai. A second product origin must use the same four-layer discipline
without requiring product-specific changes to Dodai itself.

## Decision

Projection-side pins select an audited renderer kind. The existing `waitlist`
kind retains the complete interactive vertical slice. The reusable `brief` kind
produces executable shared meaning with verification and a stakeholder
explanation for origins that do not need the waitlist interaction.

`dodai init` creates a valid, minimal four-layer origin and selects the reusable
kind. GPT-5.6 still derives the role-neutral semantic bundle; deterministic
renderers remain responsible for executable structure.

## Consequences

- Different business vocabularies and minimal journeys remain isolated.
- Adding a new audited presentation shape is a projection decision, not a layer
  two story requirement.
- Pins participate in projection identity and are attributed separately from
  origin meaning.
- Arbitrary executable generation remains deliberately out of scope.
