# Traceability

1. Every generated case maps to at least one source story ID. A case that cannot be mapped is not written.
2. The mapping is **internal metadata** in `test-design/state/traceability.json` (schemas: `schemas/traceability.schema.json`, `schemas/test-case-metadata.schema.json`). The only story reference allowed in `test-cases.md` is the module-level `User Story ID:` line (see `test-case-format.md`); never add criterion labels or any other unrequested field to it, and never put a story ID inside a test case. `validate-traceability.py` warns (`STORY_ID_MISMATCH`) when a case's section story ID is not among the stories it is mapped to.
3. `stories` records each analysed story: `sourceFile`, `title`, `criteria` (labels you assign while analysing: `AC-1`.., `BR-1`.., `NFR-1`..) and `status` (`analysed`, or `no_testable_behaviour` with the reason in the run summary).
4. `cases` records, per case ID: `title`, `module`, `storyIds`, `covers` (`<storyId>#<label>`), `techniques`, and `scenarioKey` (from `generate-stable-id.py`).
5. Criterion labels are numbered in the order they appear in the story and stay stable between runs unless the story changes. The file stores labels only, not criterion text.
6. When a case is edited by the user or regenerated, keep its ID and mapping. When a story changes, update `criteria` and report which mapped cases are affected; do not delete or rewrite them without the user's decision.
7. Run `scripts/validate-traceability.py` after every save. Errors block completion; warnings (uncovered criterion, stale mapping) go into the run summary.
