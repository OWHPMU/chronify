# Chronify Coding Guidelines

## General

- Target Python 3.9 compatibility.
- Do not change program behavior unless explicitly requested.
- If a requested refactoring would change behavior, stop and explain why before making changes.
- Prefer small, focused refactorings.
- Keep functions cohesive and readable.
- Do not introduce new dependencies without approval.
- If requirements are ambiguous, ask instead of guessing.

## Development Workflow

- Separate refactoring and feature development into different commits.
- Prefer pipeline-oriented functions over many tiny helper functions.
- Each extracted function should represent one processing step.
- Keep each change suitable for a single Git commit.

## Chronify Architecture

- Prefer passing data explicitly between pipeline stages instead of using global state.
- Preserve the current processing pipeline unless a redesign is explicitly requested.
- Favor clear data flow over clever implementations.

## Refactoring

- Perform only the requested refactoring.
- Do not rename variables, functions, or files unless explicitly requested.
- Preserve comments unless they become incorrect.
- Write new comments only when they explain intent rather than implementation.
- Never remove code unless it is clearly obsolete or explicitly requested.
- Keep the implementation as simple as possible.

## Learning

- Explain every non-trivial code change.
- Explain why the proposed solution is considered idiomatic Python.
- Mention reasonable alternatives when appropriate.
- Favor readability and maintainability over cleverness or brevity.

## Review

After proposing changes, always summarize:

- What changed.
- Why it changed.
- Whether program behavior changed (expected: no unless explicitly requested).
- Any potential risks or follow-up improvements.

## Git

- Keep changes suitable for a single commit.
- Avoid mixing refactoring and feature development.
- Preserve a clean and meaningful Git history.
