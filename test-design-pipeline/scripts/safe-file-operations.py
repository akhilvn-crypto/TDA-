#!/usr/bin/env python3
"""Safe, confined file operations for generated Test Design artefacts.

Every write stays inside ``<root>/test-design/`` (so source stories and the plugin are never
touched), uses a temp file + atomic replace, refuses to overwrite without permission or a
matching hash, keeps a backup of anything it replaces under ``state/backups/`` and verifies the
result by reading it back.

    safe-file-operations.py check-access --root R [--source FILE ...]
    safe-file-operations.py hash FILE...
    safe-file-operations.py write        --root R --target T --source FILE [--expect-sha256 H | --allow-overwrite]
                                         [--schema NAME] [--validate-cases] [--no-backup]
    safe-file-operations.py merge-cases  --root R --target T --source DRAFT [--expect-sha256 H] [--on-conflict fail|skip]
    safe-file-operations.py replace-case --root R --target T --id ID --source DRAFT --expect-sha256 H --yes
    safe-file-operations.py merge-json   --root R --target T --patch-file P [--schema NAME] [--create] [--touch FIELD]
    safe-file-operations.py append-jsonl --root R --target T (--entry JSON | --entry-file F)

``merge-cases`` appends validated cases to the end of their module in the target and leaves every
existing byte untouched (user edits survive). ``replace-case`` swaps one case and needs ``--yes``,
which the caller may pass only after the user agreed. All commands print JSON.
Exit codes: 0 ok, 1 validation findings, 2 usage, 3 conflict/exists, 4 missing/corrupt, 5 outside
the output folder, 6 I/O error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import td_common as td  # noqa: E402


def _summ(report: dict) -> dict:
    return {"errors": report["summary"]["errors"], "warnings": report["summary"]["warnings"],
            "findings": report["findings"]}


def cmd_check_access(a) -> int:
    root = Path(a.root).resolve()
    out = td.output_dir(root)
    res = {"root": td.check_dir_access(root, probe=False),
           "outputDir": td.check_dir_access(out, probe=True)}
    res["sources"] = []
    for s in a.source:
        p = Path(s)
        ok = p.is_file() and os.access(p, os.R_OK)
        res["sources"].append({"path": str(p), "readable": ok})
    ok = res["outputDir"]["writable"] and res["outputDir"]["readable"] and all(x["readable"] for x in res["sources"])
    td.emit({"ok": ok, **res})
    return td.EXIT_OK if ok else td.EXIT_IO


def cmd_hash(a) -> int:
    out = {}
    for f in a.files:
        p = Path(f)
        out[f] = td.sha256_file(p) if p.is_file() else None
    td.emit({"ok": True, "hashes": out})
    return td.EXIT_OK


def _read_source(path: str) -> bytes:
    p = Path(path)
    if not p.is_file():
        raise td.SafeOpError("SOURCE_MISSING", f"Source file not found: {p}", td.EXIT_MISSING)
    return p.read_bytes()


def cmd_write(a) -> int:
    data = _read_source(a.source)
    if a.schema:
        try:
            value = json.loads(data.decode("utf-8-sig"))
        except ValueError:
            raise td.SafeOpError("INVALID_JSON", "Content is not valid JSON", td.EXIT_FINDINGS)
        errs = td.validate_json(value, td.load_schema(a.schema))
        if errs:
            td.emit({"ok": False, "error": {"code": "SCHEMA", "message": "Content does not match the schema"}, "errors": errs})
            return td.EXIT_FINDINGS
    if a.validate_cases:
        doc = td.parse_test_cases(data.decode("utf-8-sig"))
        report = td.validation_report(doc, td.validate_doc(doc, None))
        if not report["ok"]:
            td.emit({"ok": False, "error": {"code": "VALIDATION", "message": "Test cases failed validation; nothing was written"},
                     **_summ(report)})
            return td.EXIT_FINDINGS
    res = td.safe_write(Path(a.root), Path(a.target), data, expect_sha=a.expect_sha256,
                        allow_overwrite=a.allow_overwrite, backup=not a.no_backup)
    td.emit({"ok": True, **res})
    return td.EXIT_OK


def cmd_merge_cases(a) -> int:
    root = Path(a.root)
    target = td.confine(root, a.target)
    src_text = _read_source(a.source).decode("utf-8-sig")
    src = td.parse_test_cases(src_text)
    target_text = td.read_text(target) if target.is_file() else ""
    if a.expect_sha256 and not target.is_file():
        raise td.SafeOpError("MISSING", f"{target.name} is missing although a previous hash was expected; "
                             "ask the user how to proceed.", td.EXIT_MISSING)
    current_sha = td.sha256_file(target) if target.is_file() else None
    user_edits = bool(a.expect_sha256 and current_sha and current_sha != a.expect_sha256)

    existing = td.parse_test_cases(target_text) if target_text.strip() else None
    existing_ids = {c.id for c in existing.cases if c.id} if existing else set()
    conflicts = sorted({c.id for c in src.cases if c.id and c.id in existing_ids})
    skipped: list[str] = []
    if conflicts:
        if a.on_conflict == "fail":
            td.emit({"ok": False, "error": {"code": "ID_CONFLICT",
                                            "message": "These IDs already exist in the target; nothing was written. "
                                                       "Ask the user whether to skip or replace them."},
                     "conflicts": conflicts})
            return td.EXIT_CONFLICT
        keep = [c for c in src.cases if c.id not in conflicts]
        src_text = _rebuild(src, keep) if keep else ""
        src = td.parse_test_cases(src_text)
        skipped = conflicts

    if skipped and not src.cases:
        td.emit({"ok": True, "added": [], "skippedExisting": skipped, "note": "Every draft case already exists; nothing to add"})
        return td.EXIT_OK
    report = td.validation_report(src, td.validate_doc(src, existing))
    if not report["ok"]:
        td.emit({"ok": False, "error": {"code": "VALIDATION", "message": "Draft failed validation; nothing was written"},
                 **_summ(report)})
        return td.EXIT_FINDINGS

    merged, placed = td.merge_cases_text(target_text, src)
    data = merged.encode("utf-8")
    res = td.safe_write(root, target, data, expect_sha=current_sha, allow_overwrite=current_sha is None, backup=True)
    final = td.parse_test_cases(merged)
    new_ids = {c.id for c in src.cases}
    final_report = td.validation_report(final, td.validate_doc(final))
    td.emit({"ok": True, **res, "added": [c.id for c in src.cases], "skippedExisting": skipped,
             "placement": placed, "userEditsDetected": user_edits,
             "totalCases": len(final.cases),
             "warnings": [f for f in final_report["findings"] if f.get("caseId") in new_ids and f["severity"] == "warning"],
             "fileWideErrors": final_report["summary"]["errors"]})
    return td.EXIT_OK


def _rebuild(doc: td.Doc, keep: list) -> str:
    """Re-emit only the kept cases (used when --on-conflict skip drops some)."""
    out: list[str] = []
    last_mod = object()
    for c in keep:
        if c.module != last_mod:
            if c.module:
                out += ([""] if out else []) + [f"# {c.module}"]
            last_mod = c.module
        out += [""] + td.case_block(doc, c) if out else td.case_block(doc, c)
    return doc.newline.join(out) + doc.newline


def cmd_replace_case(a) -> int:
    if not a.yes:
        raise td.SafeOpError("CONSENT_REQUIRED", "replace-case needs --yes, passed only after the user agreed to replace this case",
                             td.EXIT_USAGE)
    root = Path(a.root)
    target = td.confine(root, a.target)
    if not target.is_file():
        raise td.SafeOpError("MISSING", f"{target.name} does not exist", td.EXIT_MISSING)
    text = td.read_text(target)
    doc = td.parse_test_cases(text)
    old = doc.by_id().get(a.id)
    if not old:
        raise td.SafeOpError("CASE_NOT_FOUND", f"{a.id} is not in {target.name}", td.EXIT_MISSING)
    src = td.parse_test_cases(_read_source(a.source).decode("utf-8-sig"))
    if len(src.cases) != 1 or src.cases[0].id != a.id:
        raise td.SafeOpError("SOURCE_MISMATCH", f"The draft must contain exactly one case with ID {a.id}", td.EXIT_USAGE)
    rest = td.parse_test_cases(td.remove_case_text(text, a.id))
    report = td.validation_report(src, td.validate_doc(src, rest))
    if not report["ok"]:
        td.emit({"ok": False, "error": {"code": "VALIDATION", "message": "Replacement failed validation; nothing was written"},
                 **_summ(report)})
        return td.EXIT_FINDINGS
    block = td.case_block(src, src.cases[0])
    lines = doc.lines[:old.start] + block + doc.lines[old.end:]
    res = td.safe_write(root, target, (doc.newline.join(lines) + doc.newline).encode("utf-8"),
                        expect_sha=a.expect_sha256, backup=True)
    td.emit({"ok": True, **res, "replaced": a.id})
    return td.EXIT_OK


def cmd_merge_json(a) -> int:
    root = Path(a.root)
    target = td.confine(root, a.target)
    try:
        patch = json.loads(td.read_text(Path(a.patch_file)))
    except (OSError, ValueError):
        raise td.SafeOpError("PATCH_UNREADABLE", f"Cannot read a JSON patch from {a.patch_file}", td.EXIT_USAGE)
    sha = None
    if target.is_file():
        try:
            current = json.loads(td.read_text(target))
        except ValueError:
            raise td.SafeOpError("STATE_CORRUPT", f"{target.name} is not valid JSON. It was not changed; "
                                 "explain this to the user and ask how to proceed.", td.EXIT_MISSING)
        sha = td.sha256_file(target)
    elif a.create:
        current = {}
    else:
        raise td.SafeOpError("MISSING", f"{target.name} does not exist (use --create to start it)", td.EXIT_MISSING)
    merged = td.merge_patch(current, patch)
    if a.touch and isinstance(merged, dict):
        merged[a.touch] = td.utc_now()
    if a.schema:
        errs = td.validate_json(merged, td.load_schema(a.schema))
        if errs:
            td.emit({"ok": False, "error": {"code": "SCHEMA", "message": "Result does not match the schema; nothing was written"},
                     "errors": errs})
            return td.EXIT_FINDINGS
    data = (json.dumps(merged, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    res = td.safe_write(root, target, data, expect_sha=sha, allow_overwrite=sha is None, backup=a.backup)
    td.emit({"ok": True, **res})
    return td.EXIT_OK


def cmd_append_jsonl(a) -> int:
    root = Path(a.root)
    target = td.confine(root, a.target)
    raw = a.entry if a.entry else td.read_text(Path(a.entry_file)) if a.entry_file else None
    if raw is None:
        raise td.SafeOpError("USAGE", "Give --entry JSON or --entry-file F", td.EXIT_USAGE)
    try:
        entry = json.loads(raw)
    except ValueError:
        raise td.SafeOpError("INVALID_JSON", "The audit entry is not valid JSON", td.EXIT_USAGE)
    if not isinstance(entry, dict):
        raise td.SafeOpError("INVALID_JSON", "The audit entry must be a JSON object", td.EXIT_USAGE)
    entry.setdefault("ts", td.utc_now())
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
    if td.contains_secret(line):
        raise td.SafeOpError("SECRET_DETECTED", "The audit entry looks like it contains a secret; use env: names only. Nothing was written.",
                             td.EXIT_FINDINGS)
    target.parent.mkdir(parents=True, exist_ok=True)
    prefix = ""
    if target.is_file() and target.stat().st_size:
        with open(target, "rb") as fh:
            fh.seek(-1, os.SEEK_END)
            prefix = "" if fh.read(1) == b"\n" else "\n"
    try:
        with open(target, "ab") as fh:
            fh.write((prefix + line + "\n").encode("utf-8"))
            fh.flush()
            os.fsync(fh.fileno())
    except OSError as e:
        raise td.SafeOpError("IO_ERROR", f"Could not append to {target.name}: {type(e).__name__}", td.EXIT_IO)
    last = td.read_text(target).rstrip("\n").splitlines()[-1]
    if last != line:
        raise td.SafeOpError("READBACK_FAILED", "Read-back of the appended audit line failed", td.EXIT_IO)
    td.emit({"ok": True, "path": str(target), "entry": entry})
    return td.EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("check-access")
    p.add_argument("--root", required=True)
    p.add_argument("--source", action="append", default=[])
    p.set_defaults(fn=cmd_check_access)

    p = sub.add_parser("hash")
    p.add_argument("files", nargs="+")
    p.set_defaults(fn=cmd_hash)

    p = sub.add_parser("write")
    p.add_argument("--root", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--expect-sha256")
    p.add_argument("--allow-overwrite", action="store_true")
    p.add_argument("--schema")
    p.add_argument("--validate-cases", action="store_true")
    p.add_argument("--no-backup", action="store_true")
    p.set_defaults(fn=cmd_write)

    p = sub.add_parser("merge-cases")
    p.add_argument("--root", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--expect-sha256")
    p.add_argument("--on-conflict", choices=["fail", "skip"], default="fail")
    p.set_defaults(fn=cmd_merge_cases)

    p = sub.add_parser("replace-case")
    p.add_argument("--root", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--expect-sha256", required=True)
    p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_replace_case)

    p = sub.add_parser("merge-json")
    p.add_argument("--root", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--patch-file", required=True)
    p.add_argument("--schema")
    p.add_argument("--create", action="store_true")
    p.add_argument("--touch", help="top-level field to set to the current UTC time (e.g. updatedAt)")
    p.add_argument("--backup", action="store_true")
    p.set_defaults(fn=cmd_merge_json)

    p = sub.add_parser("append-jsonl")
    p.add_argument("--root", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--entry")
    p.add_argument("--entry-file")
    p.set_defaults(fn=cmd_append_jsonl)
    return ap


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(args)
    except td.SafeOpError as e:
        td.emit({"ok": False, "error": {"code": e.code, "message": str(e)}})
        return e.exit_code
    except td.SchemaError as e:
        td.emit({"ok": False, "error": {"code": "SCHEMA_UNKNOWN", "message": str(e)}})
        return td.EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
