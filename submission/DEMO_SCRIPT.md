# Demo Script and Shot List

Target duration: 2 minutes 35 seconds. Narration and on-screen text are English.

## 0:00–0:20 — Problem

**Screen:** Show the four files under `origin/`, then the generated developer and
stakeholder projections.

**Narration:**

> When AI agents write code, tests, and documents, those artifacts drift. Teams
> respond with more technical instructions, turning delegation into
> micromanagement. dodai makes product intent authoritative and treats every
> implementation artifact as a disposable projection.

## 0:20–0:50 — The four-layer origin

**Screen:** Open the definitions, user stories, acceptance criteria, and test
specifications. Run `uv run dodai --root . lint`.

**Narration:**

> The origin has four layers. Definitions supply the business vocabulary. User
> stories contain only actors and pains. Acceptance criteria define falsifiable
> outcomes, guardrails, and exit conditions. Test specifications verify those
> outcomes without naming implementation details. The vocabulary linter reports
> solution language in the wrong layer.

## 0:50–1:20 — GPT-5.6 and projections

**Screen:** Run `bash scripts/demo-web.sh`, open the local browser experience,
submit an email, and show the success state. Briefly show the matching
stakeholder projection. Do not run `--refresh` during recording.

**Narration:**

> GPT-5.6 reads the complete origin and derives one strict structured bundle of
> shared product meaning. Deterministic renderers turn that bundle into this
> working browser experience, behavioral tests, and an aligned stakeholder
> brief. This committed bundle came from one live GPT-5.6 request. The origin
> digest makes later regeneration stable without spending more model tokens.

## 1:20–1:50 — Rebuild and outer loop

**Screen:** Run `bash scripts/demo.sh`. Highlight the rebuild match and the
guardrail proposal path.

**Narration:**

> The rebuild test regenerates every projection from the origin and approved
> bundle. A mismatch exposes a decision that leaked outside the origin. In the
> slower outer loop, simulated telemetry that breaches a guardrail proposes new
> verification without discarding the user problem. Reaching an exit condition
> records the lost bet.

## 1:50–2:20 — Codex collaboration

**Screen:** Show the pull-request commit history, CI success, and ADR 0001.

**Narration:**

> I defined the product language, user pains, outcomes, and constraints. I
> delegated all technical How to Codex. Codex designed the representation,
> derived tests from the outcomes, implemented the vertical slice with TDD, and
> created reviewed pull requests. A live GPT-5.6 output exposed a long-copy bug;
> Codex fixed the renderer and added a regression test without another API call.

## 2:20–2:35 — Close

**Screen:** Return to the origin and the two role projections.

**Narration:**

> dodai is a small but complete proof: one origin, multiple trustworthy
> projections, and explicit learning when a product bet fails. Manage agents by
> outcomes, not methods.

## Recording checklist

- Keep the final export below 2 minutes 59 seconds.
- Use audible English narration or provide a complete English translation.
- Upload publicly to YouTube.
- Do not show terminals containing keys, environment dumps, account details, or Session IDs.
- Do not include copyrighted music, third-party marks, or unlicensed assets.
