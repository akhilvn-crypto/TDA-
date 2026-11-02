# Safe file operations

1. **Source stories are read-only.** Never edit, move or delete them, and never "enrich" them. `scripts/safe-file-operations.py` refuses any write outside `<project-root>/test-design/`, which also protects them.
2. **Never write generated artefacts with the Write/Edit tools.** Go through `scripts/safe-file-operations.py` (temp file, atomic replace, read-back hash check, backup in `test-design/state/backups/`). The only files you create directly are drafts and patches in the session's scratch/temp folder, never inside the project.
3. **Never silently overwrite.** Saving cases is an append (`merge-cases`) that leaves existing bytes untouched, so hand edits survive. Replacing an existing case (`replace-case`) needs the user's explicit yes first.
4. **Track the hash.** Record the SHA-256 of `test-cases.md` after each save in `workflow.json` and pass it back as `--expect-sha256` on the next save. A different hash means the user or a tool edited the file: continue with append-only operations and mention it in the summary.
5. **Corrupt or missing state is not completion.** If `workflow.json`, `traceability.json` or the output file is missing or unparsable, say what is wrong, show the evidence, and ask how to proceed. Never recreate state silently or assume the work was done.
6. **No automatic installation.** If Python 3.9+ is missing, say why it is needed (deterministic validation and safe writes) and ask permission before installing anything. The scripts use only the standard library; never install packages.
7. **Ask before replacing conflicting outputs**: an ID that already exists with different content, a changed source story whose generated cases exist, a `test-design/` folder with a different structure.
8. Never put secrets in any file you write (see `test-data-and-secrets.md`); the scripts refuse content that looks like a secret.
