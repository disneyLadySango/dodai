# Product Journey and Completion Evidence

Dodai is for product managers and engineers who delegate technical How to AI
agents while retaining authority over business language, user pain, outcomes,
guardrails, exit conditions, and human approval.

The ordinary journey never requires editing YAML. Internal representations,
digests, pins, and raw projection files remain available in audit mode.

## End-to-end journey

| Stage | Product-owner action | Dodai responsibility | Executable evidence |
| --- | --- | --- | --- |
| Portfolio | See what to provide, what Dodai owns, and the three resulting artifacts; create, find, and resume a product | Preserve stage, next decision, and recoverable error | `test_home_starts_and_resumes_multiple_product_bets` |
| Problem | Describe the actor and pain | Detect prescribed How and recover the intended outcome | `test_solution_vocabulary_returns_discovery_to_intended_outcome` |
| Outcomes | Describe observable improvement and the person's first action through final result; optionally clarify one product-specific term | Apply operational defaults and produce valid origin layers one through three without exposing those mechanics | `test_outcome_questions_are_lightweight_and_operational_defaults_are_internal` |
| Verification | Review intent, observable checks, and what approval starts in decision language | Cover every active outcome before generation without exposing internal identifiers or verification notation | `test_verification_review_shows_approved_meaning_and_can_return_for_revision` |
| Generation plan | Inspect projection work, request maximum, cost guardrail, and cache status | Remain stopped until explicit consent and claim one generation under concurrent submission | `test_generation_requires_consent_and_never_requests_same_identity_twice`, `test_concurrent_generation_submissions_claim_one_model_request` |
| Progress | Leave or revisit while generation runs | Persist progress and move to success or recoverable failure | `test_generation_progress_is_visible_and_survives_navigation` |
| Result | Operate the generated product and read stakeholder meaning | Verify behavior and connect both roles to one origin identity | `test_keyless_sample_provider_completes_the_same_product_journey` |
| Change | Describe changed intent in plain language | Identify the highest layer and actual downstream records and projections | `test_ready_journey_previews_changes_and_evaluates_learning` |
| Approval | Approve or reject the complete candidate | Apply regeneration atomically and retain history | `test_ready_journey_previews_changes_and_evaluates_learning` |
| Learning | Enter representative outcome evidence | Explain continue, revise-verification, or end-bet and retain learning | `test_ready_journey_previews_changes_and_evaluates_learning` |
| Recovery | Return after provider failure | Preserve approved decisions and support safe retry | `test_failed_generation_is_visible_and_resumable_without_losing_decisions` |

## Trust boundaries

- New external model work requires visible consent.
- An unchanged approved origin and pins reuse cached semantic meaning.
- Deterministic renderer upgrades reuse an approved meaning bundle without a
  new model request.
- Browser errors never expose provider details or partially approve origin
  changes.
- Local product-bet state is written atomically and is ignored by Git.
- The keyless sample path derives visible meaning from the supplied origin; it
  is not presented as a verified GPT-5.6 result.

## MVP boundaries

This product intentionally remains local and single-user. SaaS hosting,
authentication, multitenancy, production telemetry connections, automatic
deployment, and unrestricted repository generation are not part of this MVP.
The audited renderer set currently proves one complete waitlist-shaped vertical
journey and one reusable executable-meaning journey.
