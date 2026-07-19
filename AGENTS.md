# Repository Instructions

These instructions apply to the entire repository.

## Hackathon constraints

- Read `HACKATHON.md` before planning or changing the project.
- Treat the official OpenAI Build Week rules as the source of truth. Do not relax a requirement without an official source.
- The project must make meaningful, demonstrable use of both Codex and GPT-5.6.
- Keep the project runnable and consistent with the README, submission description, and demo video.
- Preserve truthful evidence of work completed during the submission period through commits and Codex sessions.
- Keep the public README current with setup, testing, architecture, Codex collaboration, GPT-5.6 usage, and important human decisions.
- Write public submission materials in English. Code, identifiers, comments, and docstrings must also be in English.

## Private information

- Never commit a Codex Session ID, API key, token, password, judge credential, personal information, or confidential data.
- Store local submission state only in `.hackathon/submission.local.md`, which must remain ignored by Git.
- Store judge credentials in a password manager or the private Devpost testing instructions, not in this repository.
- Before committing or submitting, inspect the staged diff for secrets and third-party material that cannot be published.

## Delivery

- Use focused commits whose timestamps and messages make the hackathon work easy to verify.
- Add tests for observable behavior once implementation begins.
- Before reporting implementation complete, run the available tests, lint, and build checks and update the submission checklist in `HACKATHON.md`.
- Do not claim that the project, video, repository access, Session ID, submission, judging, or award state has been verified unless it was actually observed.
