---
name: workflow-resume
description: Read the checkpoint state, verify source fingerprints and output hashes, classify each story, and resume an interrupted Test Design run without duplicating completed work or overwriting output. Also reports status. Use for /test-design:resume, /test-design:status, and when /test-design:start finds an existing run.
user-invocable: false
---

# Workflow resume

State lives in `<root>/test-design/state/`: `workflow.json` (checkpoint, schema `schemas/workflow-state.schema.json`), `traceability.json`, `source-fingerprints.json`, `audit.jsonl`. `PY` / `SCRIPTS` as in `story-source-discovery`.

## Locate the run

Use a project root the user gave; otherwise the nearest ancestor of the working directory containing `test-design/state/workflow.json`. If none is found, say so and ask for the project root. Do not search the whole disk.

## Procedure

1. **Read `workflow.json`.** Missing or unparsable: stop. Explain exactly what is wrong (`state file missing` / `not valid JSON`), list what output files exist, and ask the user how to proceed (start over keeping the existing cases, repair by hand, or point to a backup in `state/backups/`). Never assume the run was complete and never rewrite a corrupt state file.
2. **Check outputs.** `PY SCRIPTS/safe-file-operations.py hash "<root>/test-design/test-cases/test-cases.md" "<root>/test-design/state/traceability.json"` and compare with `outputs.*.sha256`.
   - `test-cases.md` missing although stories are `saved`: report as missing output; ask. Do not regenerate silently.
   - Hash differs: the file was edited since the last checkpoint. Not an error. Keep appending only; mention it.
   - Run `validate-traceability.py`. A case present in the file but unmapped (`ORPHAN_CASE`) after a crash between steps: tell the user and offer to map it from its title and story if unambiguous, or leave it flagged.
3. **Verify sources.** `PY SCRIPTS/fingerprint-sources.py compare <each selected source file> --previous "<root>/test-design/state/source-fingerprints.json" --root "<root>" --traceability "<root>/test-design/state/traceability.json"`. Exit 1 means changes. Read `files`, `stories.changed|added|removed`, and `affectedTestCases` (story -> case IDs). A source file that no longer exists is `removed`.
4. **Classify every story** in `workflow.json`:
   - `saved` and unchanged: done, skip.
   - `saved` and source changed (or removed): **affected**. Do not touch its cases. See "Reconcile".
   - `pending`, `analysing`, `designing`, `generating`, `validating`, `needs_clarification`, `failed`, or the story named by `inProgressOperation`: **incomplete**. Resume from the beginning of that story (drafts are transient). If its cases already exist in `test-cases.md` and are mapped in `traceability.json`, validate them and mark the story `saved` instead of regenerating.
   - In `stories.added` but not in `workflow.json`: **new**. Offer to add it.
5. **Present a short summary**: counts per class, affected stories with their test case IDs, new stories, and any state problems. Then ask what to do.
6. **Continue** with the orchestrator's per-story loop for the incomplete (and approved new) stories only. Update `sourceFiles`, the stories map and `source-fingerprints.json` (a fresh `snapshot --output`) only after the user decided on the changed stories.

## Reconcile changed stories (always ask first)

For each affected story show: what changed (file/story hash), the linked case IDs and titles. Options:

1. **Keep** existing cases as they are (record that the story changed after generation).
2. **Review and update**: re-analyse the story, produce updated cases as drafts, and for each existing case that should change ask before using `replace-case --yes`; new scenarios are appended; cases whose behaviour disappeared are listed for the user to remove by hand (this plugin does not delete cases).
3. **Skip** for now (stays flagged in status).

Never regenerate, replace or delete a case without the user choosing option 2 for that story.

## Status report (read-only)

Show: run ID and status, project root, current phase and story, per-story status table (story ID, status, case count, validation outcome), totals (stories processed / total, cases generated), unresolved clarifications, source drift (from step 3) and the output paths. Make no writes.
