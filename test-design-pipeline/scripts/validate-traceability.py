#!/usr/bin/env python3
"""Check story-to-test mappings in traceability.json against the saved test cases.

    validate-traceability.py --test-cases test-cases.md --traceability traceability.json
                             [--fingerprints source-fingerprints.json]

Errors: schema violations, a test case with no mapping or no story, a mapping to a story that is
not tracked, a ``covers`` entry that names an unknown story/criterion.
Warnings: mappings whose case is no longer in the file, stories (or criteria) with no covering
case, stories missing from the source fingerprints, a case whose module-level ``User Story ID``
is not among the stories it is mapped to. Exit 1 on errors.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import td_common as td  # noqa: E402


def load_json(path: Path, label: str) -> dict:
    if not path.is_file():
        raise td.fail("FILE_MISSING", f"{label} not found: {path}", td.EXIT_MISSING)
    try:
        return json.loads(td.read_text(path))
    except ValueError:
        raise td.fail("STATE_CORRUPT", f"{label} is not valid JSON ({path.name}). Ask the user how to proceed.", td.EXIT_MISSING)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test-cases", required=True)
    ap.add_argument("--traceability", required=True)
    ap.add_argument("--fingerprints")
    args = ap.parse_args()

    tc_path = Path(args.test_cases)
    if not tc_path.is_file():
        raise td.fail("FILE_MISSING", f"Test-case file not found: {tc_path}", td.EXIT_MISSING)
    doc = td.parse_test_cases(td.read_text(tc_path))
    trace = load_json(Path(args.traceability), "traceability.json")

    findings: list[td.Finding] = []

    def err(code, msg, cid=None):
        findings.append(td.Finding(code, "error", msg, None, cid))

    def warn(code, msg, cid=None):
        findings.append(td.Finding(code, "warning", msg, None, cid))

    for e in td.validate_json(trace, td.load_schema("traceability")):
        err("SCHEMA", e)

    stories = trace.get("stories", {}) if isinstance(trace.get("stories"), dict) else {}
    mapped = trace.get("cases", {}) if isinstance(trace.get("cases"), dict) else {}
    file_ids = [c.id for c in doc.cases if c.id]

    for c in doc.cases:
        if not c.id:
            err("ORPHAN_CASE", f"Test case '{c.title}' (line {c.line}) has no ID, so it cannot be mapped to a story")
        elif c.id not in mapped:
            err("ORPHAN_CASE", f"{c.id} is in the test-case file but has no entry in traceability.json", c.id)
    for c in doc.cases:
        meta = mapped.get(c.id) if c.id else None
        if c.story_id and isinstance(meta, dict) and meta.get("storyIds") and c.story_id not in meta["storyIds"]:
            warn("STORY_ID_MISMATCH",
                 f"{c.id} sits under 'User Story ID: {c.story_id}' but traceability.json maps it to "
                 f"{', '.join(meta['storyIds'])}", c.id)
    for cid in mapped:
        if cid not in file_ids:
            warn("STALE_MAPPING", f"{cid} is mapped in traceability.json but no longer in the test-case file", cid)

    covered_by_story: dict[str, set[str]] = {}
    covered_criteria: set[str] = set()
    for cid, meta in mapped.items():
        sids = meta.get("storyIds", []) if isinstance(meta, dict) else []
        if not sids:
            err("NO_STORY", f"{cid} maps to no source story", cid)
        for sid in sids:
            covered_by_story.setdefault(sid, set()).add(cid)
            if sid not in stories:
                err("UNKNOWN_STORY", f"{cid} maps to story {sid}, which is not tracked in traceability.json", cid)
        for ref in meta.get("covers", []) if isinstance(meta, dict) else []:
            sid, _, crit = ref.partition("#")
            if sid not in stories or crit not in stories[sid].get("criteria", []):
                err("BAD_COVERS", f"{cid} covers '{ref}', which is not a known story criterion", cid)
            else:
                covered_criteria.add(ref)

    total_criteria = 0
    for sid, s in stories.items():
        if s.get("status") == "no_testable_behaviour":
            continue
        if sid not in covered_by_story:
            warn("STORY_UNCOVERED", f"Story {sid} has no test case")
        for crit in s.get("criteria", []):
            total_criteria += 1
            if f"{sid}#{crit}" not in covered_criteria and sid in covered_by_story:
                warn("CRITERION_UNCOVERED", f"{sid} criterion {crit} is not covered by any test case")

    if args.fingerprints:
        fp = load_json(Path(args.fingerprints), "source-fingerprints.json")
        known = {sid for f in fp.get("files", {}).values() for sid in f.get("stories", {})}
        for sid in stories:
            if sid not in known:
                warn("SOURCE_STORY_MISSING", f"Story {sid} is tracked but not found in the source fingerprints")

    n_err = sum(f.severity == "error" for f in findings)
    n_warn = len(findings) - n_err
    td.emit({
        "ok": n_err == 0,
        "summary": {"casesInFile": len(doc.cases), "casesMapped": sum(1 for i in file_ids if i in mapped),
                    "storiesTracked": len(stories), "storiesWithCases": sum(1 for s in stories if s in covered_by_story),
                    "criteria": total_criteria, "criteriaCovered": len(covered_criteria), "errors": n_err, "warnings": n_warn},
        "findings": [f.as_dict() for f in findings],
    })
    return td.EXIT_FINDINGS if n_err else td.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
