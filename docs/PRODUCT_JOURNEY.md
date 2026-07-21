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
| Result | Judge delegated work against the still-visible actor, pain, and outcome | Show produced artifacts, satisfied and unsatisfied verification, and trace every role presentation to its story, criterion, and specification | `test_approved_story_remains_visible_from_verification_through_result`, `test_delegation_result_distinguishes_proof_sample_and_reports_origin_evidence` |
| Delegation plan | Review approved intent, isolated scope, one-attempt limit, and expected evidence | Keep Codex stopped until explicit consent and claim one attempt under concurrent submission | `test_codex_delegation_requires_consent_and_starts_only_once` |
| Repository work | Leave or revisit while Codex works in the bet-owned repository | Preserve progress, constrain writes to the isolated repository, and expose a recoverable failure | `test_failed_codex_delegation_is_resumable_without_losing_intent` |
| Delegation evidence | Inspect changed file contents, successful verification, stakeholder meaning, and origin evidence | Derive artifact evidence from repository changes and connect every result to Story, AC, and test specification | `test_delegation_result_connects_repository_evidence_to_origin` |
| Delegated product | Operate the actual delegated behavior from the decision screen | Require an experienceable result, serve only its bounded delivery tree, and block repository escape | `test_delegated_product_is_immediately_experienceable_and_path_bounded` |
| Adoption | Accept the result or add prior-result evidence and approve another attempt | Record explicit adoption or retain the same approved origin for re-delegation | `test_result_can_be_accepted_or_redelegated_without_changing_origin` |
| Change | Describe changed intent in plain language | Identify the highest layer and actual downstream records and projections | `test_ready_journey_previews_changes_and_evaluates_learning` |
| Approval | Approve or reject the complete candidate | Apply regeneration atomically and retain history | `test_ready_journey_previews_changes_and_evaluates_learning` |
| Interaction learning | Answer whether the pain remained, the behavior worked, and the outcome occurred; add one observed fact | Derive the learning boundary without asking for a layer, retain immutable evidence against the attempt, and prepare only a Layer 4 candidate for a verified outcome gap | `test_plain_interaction_result_prepares_reverification_and_compares_attempts`, `test_successful_interaction_result_does_not_prepare_an_origin_change` |
| Re-delegation comparison | Approve revised verification and inspect the next result against the previous attempt | Keep Story and AC fixed, carry the observed gap into the next bounded delegation, and compare both attempts' artifacts, verification, and interaction evidence | `test_plain_interaction_result_prepares_reverification_and_compares_attempts`, `test_each_delegation_attempt_is_archived_for_comparison` |
| Presentation repair | Report that the produced behavior did not complete, then approve one repair attempt | Keep every origin layer byte-identical, send the failed observation to Codex, compare both attempts, and distinguish verified repair from an unconfirmed business outcome | `test_behavior_failure_repairs_only_presentation_and_keeps_outcome_unconfirmed`, `test_origin_snapshot_changes_when_any_approved_layer_changes` |
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
- Real Codex delegation writes only inside a product-bet-owned repository. Raw
  JSONL events, session identifiers, stderr, and environment values are not
  persisted. Sample mode exercises the same evidence path without Codex.
- Delegated products run in a sandboxed frame, can load only their bounded
  static delivery tree, and cannot make outbound connections. Codex automation
  ignores unrelated user configuration and keeps default secret exclusions for
  generated commands.

## MVP boundaries

This product intentionally remains local and single-user. SaaS hosting,
authentication, multitenancy, production telemetry connections, automatic
deployment, and unrestricted repository generation are not part of this MVP.
Selecting or mutating an arbitrary existing repository is also outside the MVP;
delegation is intentionally confined to a repository created for the product bet.
The audited renderer set currently uses one complete waitlist-shaped vertical
journey as an interchangeable proof sample and one reusable executable-meaning
journey. Waitlist generation is not Dodai's product value and does not prove
support for unrestricted product generation.
