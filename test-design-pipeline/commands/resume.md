---
description: Resume the last incomplete Test Design run safely - verifies the checkpoint, output hashes and source fingerprints, continues only unfinished stories, and asks before reconciling changed stories. Never regenerates or overwrites existing test cases on its own.
argument-hint: "[project root]"
disable-model-invocation: true
---

# /test-design-pipeline:resume

Arguments: `$ARGUMENTS`

1. Read `${CLAUDE_PLUGIN_ROOT}/agents/test-design-orchestrator.md` (if the variable is not expanded, find the installed `test-design-pipeline` plugin folder) and **act as that orchestrator in this conversation**.
2. Load the `workflow-resume` skill and follow it exactly: locate the run (`$ARGUMENTS` as the project root if given), read the checkpoint, verify output hashes and source fingerprints, classify every story, and present a short summary of what is done, incomplete, affected by source changes, and new.
3. If the checkpoint or outputs are missing or corrupt, explain the problem and ask how to proceed. Never assume the work was completed.
4. For source stories that changed since generation, ask the user before doing anything (keep, review and update, or skip). Never regenerate, replace or delete existing cases without an explicit yes.
5. Continue the orchestrator's per-story loop for the incomplete stories only, then finish with its summary. If nothing is incomplete, say so and point to `/test-design-pipeline:validate`.
