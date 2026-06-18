# ADR-004: De-personalization / shareability boundary
Status: Accepted

## Context
Hard Constraint #4: the Lab must be shippable as a standalone, general-audience learning tool with
zero builder-specific private context. This is a posture, not a someday-cleanup — it must hold from
the first line of code.

## Decision
- **No personal/private context anywhere** in code, copy, examples, comments, or committed data:
  no names, no job/business/trading/life references, no system-internal context.
- All game framings use **canonical** (the classic stories) or **neutral/whimsical** content.
- No analytics, telemetry, or anything that captures a real user's identity or decisions beyond the
  ephemeral game session.
- The **application** (`app.py` + `gtlab/`) contains zero personal context and ships as-is. The
  build-process docs (`CLAUDE.md`, `docs/`, `.claude/commands/`) are INTERNAL dev records and may
  reference the builder by name; exclude or scrub them before any public release of the repo.

## Alternatives considered
- "Personalize now, de-personalize before sharing later" — rejected; private context leaks and
  cleanup passes miss things. Same ship-clean posture as a sibling Streamlit project.

## Consequences
- Every contribution is checked against this boundary. If a framing would only make sense to one
  specific person, it doesn't belong here.
