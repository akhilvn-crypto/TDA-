# TDA – Test Design Automation plugins

This repository is a Claude Code **plugin marketplace** (`tda`). It currently ships one plugin:

| Plugin | Version | What it does |
|---|---|---|
| [`test-design-pipeline`](test-design-pipeline/README.md) | 0.4.0 | Turns Markdown user stories into automation-ready, traceable test cases |

Test Design decides **what to validate**. A downstream automation tool decides how to automate and run it. The plugin does not edit your stories, repeat BA gap analysis, or write Playwright code.

---

## Install

**Requirements:** Claude Code (or Cowork), and Python 3.9+ on the machine that runs Claude (standard library only, nothing extra to install).

### From the terminal

```bash
# 1. add this marketplace
claude plugin marketplace add akhilvn-crypto/TDA-

# 2. install the plugin
claude plugin install test-design-pipeline@tda
```

### From inside Claude Code

```text
/plugin marketplace add akhilvn-crypto/TDA-
/plugin install test-design-pipeline@tda
```

### Verify

Run `/help` (or type `/test-design-pipeline:`) and check these four commands are listed:

```text
/test-design-pipeline:start
/test-design-pipeline:status
/test-design-pipeline:resume
/test-design-pipeline:validate
```

### Try it from a local checkout (no install)

```bash
git clone https://github.com/akhilvn-crypto/TDA-.git
claude --plugin-dir ./TDA-/test-design-pipeline
```

---

## Update

Plugins are updated when the marketplace's copy has a **new `version`** in `plugin.json`. Pull the latest marketplace, then update the plugin:

```bash
# 1. refresh the marketplace listing
claude plugin marketplace update tda

# 2. update the installed plugin
claude plugin update test-design-pipeline@tda
```

Inside Claude Code: `/plugin marketplace update tda`, then `/plugin update test-design-pipeline@tda` (or use the `/plugin` menu → *Installed* → the plugin → *Update*). **Restart Claude Code** (or run `/reload-plugins`) afterwards so the new commands and agents load.

Check what you have with `claude plugin list`.

**Moving from an older install?** Before 0.3.0 the plugin was named `test-design`. Remove it and install the new name:

```bash
claude plugin uninstall test-design
claude plugin install test-design-pipeline@tda
```

**Uninstall:** `claude plugin uninstall test-design-pipeline`. Your generated `test-design/` folders inside your projects are not touched.

**Team-wide auto-install:** add this to a project's `.claude/settings.json` so teammates are prompted to install it when they open the project:

```json
{
  "extraKnownMarketplaces": {
    "tda": { "source": { "source": "github", "repo": "akhilvn-crypto/TDA-" } }
  },
  "enabledPlugins": { "test-design-pipeline@tda": true }
}
```

---

## Quick start

```text
/test-design-pipeline:start                          # asks where your stories are
/test-design-pipeline:start docs/stories             # a directory (searched recursively for .md)
/test-design-pipeline:start docs/stories/login.md    # a single file
```

You get a consolidated `test-design/test-cases/test-cases.md` in your project, plus resumable state under `test-design/state/`. Your story files are never modified.

| Command | Purpose |
|---|---|
| `/test-design-pipeline:start [path]` | Run the full workflow. Offers to resume if a run already exists |
| `/test-design-pipeline:status [root]` | Read-only: phase, per-story progress, case counts, whether stories changed since generation |
| `/test-design-pipeline:resume [root]` | Continue an interrupted run; asks before touching anything affected by changed stories |
| `/test-design-pipeline:validate [root]` | Check saved cases (format, IDs, data, dependencies, expected results) and traceability |

---

## What the plugin does – the flows

### 1. Main flow (`start`)

```text
 Markdown user stories
        │
        ▼
 ┌─────────────────────────┐
 │ Phase 0  Capability check│  Python available? can read stories / write to project root?
 └────────────┬────────────┘
              ▼
 ┌─────────────────────────┐
 │ Phase 1  Discover        │  find .md stories, resolve ambiguous matches, confirm in ONE
 │          & confirm       │  question: files, project root, output folder (+ optional shared
 │                          │  rules file). Snapshot story fingerprints, create workflow.json
 └────────────┬────────────┘
              ▼
 ┌──────────────────────────────────────────────────────────────┐
 │ Per-story loop – strictly one story at a time, in file order  │
 │                                                               │
 │  A. Analyse    fresh story-analyser worker (isolated)         │
 │  B. Design     test-coverage-designer → test conditions       │
 │  C. Generate   test-case-generator → draft cases + metadata   │
 │  D. Validate   scripts + test-case-quality-checker (≤2 repairs)│
 │  E. Save       traceability first, then append to test-cases.md│
 │                                                               │
 │  checkpoint before and after every step                       │
 └────────────┬─────────────────────────────────────────────────┘
              ▼
 ┌─────────────────────────┐
 │ Phase 5  Finalise        │  audit check, whole-file validation, source-drift check,
 │                          │  summary + list of env: variables you must provide
 └─────────────────────────┘
```

| Step | Who | What happens |
|---|---|---|
| **A. Analyse** | `story-analyser` (fresh agent per story) | Extracts behaviour to validate, acceptance criteria, business rules, preconditions, dependencies, NFRs and ambiguities into a structured JSON result. If something *blocks* reliable test design, the orchestrator asks you one focused question |
| **B. Design coverage** | `test-coverage-designer` | Chooses the fewest scenarios that still give meaningful coverage, using positive/negative, boundary, equivalence partitioning, decision table, state transition, end-to-end and non-functional techniques. Drops duplicates of already-saved cases |
| **C. Generate** | `test-case-generator` | Writes cases in the fixed Markdown format with stable `AUTO-xxxxxxxx` IDs (or your own IDs if stories supply them) |
| **D. Validate** | `validate-test-cases.py` + `test-case-quality-checker` | Format, IDs, data, dependencies and expected results are checked; formatting-only issues are auto-fixed; other errors go back for repair or are dropped with a reason. A case that fails validation is **never saved** |
| **E. Save** | `safe-file-operations.py` | Writes `traceability.json` first (so a crash never loses the mapping), then appends the cases to `test-cases.md` atomically with hash checks. Hand edits survive |

Nothing is invented: limits, messages or expected results the story does not state are either asked about or left out and reported.

### 2. Isolated story analysis

Each story is analysed by its **own fresh agent session**, one at a time, so one story's reasoning can't leak into the next and long collections never fill a single context. A worker receives only its story, the shared rules it needs, and small excerpts of explicitly named dependencies. Its JSON result is schema-validated before it is used; an invalid result is retried once in a new worker, then left for `resume`. See the [plugin README](test-design-pipeline/README.md#isolated-story-analysis) for details.

### 3. Resume flow (`resume`)

```text
 read workflow.json ─► verify output hashes + source fingerprints ─► classify each story
        │
        ├─ saved & unchanged ........... left alone
        ├─ incomplete / failed ......... re-run only these (fresh workers)
        ├─ completed analysis, unchanged reused without calling a worker
        └─ story / shared rule changed . ASK: keep, review & update, or skip
                                          (never regenerated automatically)
```

Missing or corrupt state is reported, never assumed complete.

### 4. Status flow (`status`)

Read-only. Shows run status, a per-story table (status, analysis, cases, validation), totals, unresolved clarifications, output paths, and which stories changed since their cases were generated.

### 5. Validate flow (`validate`)

Runs the case and traceability validators over the saved files, groups findings by code with case IDs, and flags stories or criteria with no case. Changes nothing unless you approve a safe, formatting-only fix (a backup is kept).

---

## What it writes

```text
<your-project>/test-design/
├── test-cases/test-cases.md       # consolidated test cases (the handoff file)
└── state/
    ├── workflow.json              # checkpoint: phase, per-story status, hashes
    ├── analysis/<story-id>.json   # validated per-story analysis (no transcripts)
    ├── traceability.json          # which stories each case verifies
    ├── source-fingerprints.json   # story hashes for change detection
    ├── audit.jsonl                # event history (IDs and counts only)
    └── backups/                   # copies of anything replaced
```

**Test data convention:** `env:NAME` for secrets / environment-specific values (set them in `automation/.env`; the plugin never reads or writes it), `literal:value` for deliberately fake fixed values, plain text otherwise. Secret values are never written to any file or message.

## Safety guarantees

- Story files are read-only; all writes stay inside `<root>/test-design/`.
- Existing cases are never overwritten or regenerated without an explicit yes (a backup is kept).
- Writes are atomic (temp file → replace → hash read-back).
- If Python is missing, the plugin explains why and asks before installing anything.

## Repository layout

```text
.claude-plugin/marketplace.json     marketplace manifest (name: tda)
test-design-pipeline/               the plugin
├── .claude-plugin/plugin.json      plugin manifest (version lives here)
├── commands/    agents/    skills/    rules/    schemas/    templates/
├── scripts/                        deterministic Python tools
└── tests/                          unittest suite
```

## For maintainers: releasing an update

1. Make the change in `test-design-pipeline/`.
2. Run the tests: `cd test-design-pipeline && python -m unittest discover -s tests -t tests`
3. Bump `version` in **both** `test-design-pipeline/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (keep them equal). Without a version bump, installed copies will not see the update.
4. Validate: `claude plugin validate .`
5. Commit and push to `main`. Users then run the [update steps](#update).

## License

MIT – see [`test-design-pipeline/LICENSE`](test-design-pipeline/LICENSE).
