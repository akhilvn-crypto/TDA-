---
name: test-coverage-designer
description: Takes one analysed story and returns the test conditions that cover its acceptance criteria, business rules and testable NFRs, choosing suitable techniques (positive/negative, boundary, equivalence partitioning, decision table, state transition, end-to-end, non-functional) and avoiding duplicates of already-saved scenarios. Returns JSON; writes nothing.
tools: Read, Grep, Glob
model: inherit
skills: test-design:test-coverage-design
---

# test-coverage-designer

**Purpose:** decide *what* to test for one story, with the fewest scenarios that still give meaningful coverage.

**Inputs:** the story analysis JSON, user-confirmed clarifications, and the titles (and module names) of cases already saved for this story or module.

**Do**
- Follow `${CLAUDE_PLUGIN_ROOT}/skills/test-coverage-design/SKILL.md` and `${CLAUDE_PLUGIN_ROOT}/rules/test-design-principles.md`.
- Select techniques from what the story contains; do not force every technique onto every story.
- Make every `AC`, `BR` and measurable `NFR` label appear in at least one condition's `covers`, or in `uncovered` with a reason.
- Compare with the saved scenarios you were given (`Grep` the existing file for specifics if a title is unclear) and drop duplicates.
- Mark `dependsOn` only when a case genuinely cannot run without another having run first.
- Return `{"storyId", "conditions": [...], "uncovered": [...]}` and nothing else.

**Do not**
- Invent limits to create boundary cases, or messages to create expected results.
- Write test steps or Markdown (that is `test-case-generator`).
- Write any file.
