# 0001. Record decisions and learnings with ADRs

- **Status:** Accepted
- **Date:** 2026-10-29

## Context

Strange Fauna is built quickly, with an AI coding assistant, by a designer.
Decisions get made fast in conversation and are easy to lose: a week later,
nobody remembers why the creature is drawn by a shader rather than modelled in
Blender. The repo is also public, and the reasoning behind the work is part of
what it's meant to show.

## Decision

Record each important decision as an Architecture Decision Record (ADR): a short
numbered Markdown file in `docs/adr/`, based on [the template](template.md).
Each ADR may also capture **learnings**: non-obvious things discovered while
building or testing.

- Write an ADR when we make a choice someone might later question, or when we
  learn something the hard way.
- Add or update the ADR in the same commit as the change it explains.
- Never delete an ADR. If a decision changes, write a new one and mark the old
  one "Superseded by …".

## Consequences

- The project's reasoning is readable without digging through chat history.
- The ADRs double as a process write-up for the portfolio.
- A small amount of extra writing per decision.
