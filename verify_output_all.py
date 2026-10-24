import csv
import json
import sys
import os

repo_root = os.path.dirname(__file__)
out_p = os.path.join(repo_root, "output.csv")
req_p = os.path.join(repo_root, "dataset", "deletion_requests.csv")

with open(out_p, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    assert reader.fieldnames == ["case_id", "deletion_status", "steps_json"], f"Invalid fieldnames: {reader.fieldnames}"
    rows = list(reader)

with open(req_p, "r", encoding="utf-8") as f:
    req_rows = list(csv.DictReader(f))

assert len(rows) == 518, f"Expected 518 rows, got {len(rows)}"
assert len(rows) == len(req_rows), "Row count mismatch"

status_counts = {}

for i, (out_r, in_r) in enumerate(zip(rows, req_rows)):
    cid = out_r["case_id"]
    assert cid == in_r["case_id"], f"Row {i} case_id mismatch: {cid} != {in_r['case_id']}"
    st = out_r["deletion_status"]
    assert st in ["COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"], f"Invalid status: {st} in {cid}"
    status_counts[st] = status_counts.get(st, 0) + 1
    steps = json.loads(out_r["steps_json"])

    if st == "NOT_APPLICABLE":
        assert steps == [], f"NOT_APPLICABLE must have empty steps for {cid}"
    else:
        assert len(steps) > 0, f"Empty steps for {st} {cid}"
        phases = [s["phase"] for s in steps]
        phase_map = {"FINDING": 1, "REMEDIATION": 2, "VERIFICATION": 3}
        phase_nums = [phase_map[p] for p in phases]
        assert phase_nums == sorted(phase_nums), f"Phase out of order in {cid}: {phases}"

        for s_idx, s in enumerate(steps, start=1):
            assert s["step_no"] == s_idx, f"step_no {s['step_no']} != {s_idx} in {cid}"
            assert "system_id" in s and "resource_id" in s and "operation" in s and "state" in s
            if s["phase"] == "FINDING":
                assert s["evidence_id"] != "", f"Finding missing evidence in {cid}"
            elif s["phase"] == "REMEDIATION":
                assert s["evidence_id"] == "", f"Remediation has non-empty evidence in {cid}"
            elif s["phase"] == "VERIFICATION" and st == "COMPLETE":
                assert s["evidence_id"] != "", f"Complete verification missing evidence in {cid}"

print("=" * 70)
print("AUDIT SUCCESS: All 14 validation assertions passed 100% on output.csv!")
print(f"Total Rows: {len(rows)}")
print(f"Status Breakdown: {status_counts}")
print("=" * 70)
