import os
import sys
import csv
import json

# Ensure repo root is on sys.path
repo_root = os.path.abspath(os.path.dirname(__file__))
code_dir = os.path.join(repo_root, "code")
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from engine import DeletionAuditEngine
except (ImportError, ModuleNotFoundError):
    from code.engine import DeletionAuditEngine

def validate():
    dataset_dir = os.path.join(repo_root, "dataset")
    cache_dir = os.path.join(repo_root, "cache")

    print(f"Initializing DeletionAuditEngine...")
    engine = DeletionAuditEngine(dataset_dir, cache_dir)
    print("Engine initialized successfully.")

    sample_reqs_path = os.path.join(dataset_dir, "sample_deletion_requests.csv")
    sample_out_path = os.path.join(dataset_dir, "sample_output.csv")

    with open(sample_reqs_path, "r", encoding="utf-8") as f:
        reqs = list(csv.DictReader(f))

    with open(sample_out_path, "r", encoding="utf-8") as f:
        expected = {r["case_id"]: r for r in csv.DictReader(f)}

    total = len(reqs)
    status_matches = 0
    exact_matches = 0

    print(f"\nEvaluating {total} sample cases against sample_output.csv:")
    print("=" * 70)

    for r in reqs:
        cid = r["case_id"]
        exp = expected[cid]
        exp_status = exp["deletion_status"]
        exp_steps = json.loads(exp["steps_json"])

        pred_status, pred_steps = engine.audit_case(
            case_id=cid,
            email=r["email"],
            request_text=r["request_text"],
            audit_at=r["audit_at"]
        )

        st_match = (pred_status == exp_status)
        if st_match:
            status_matches += 1

        # Check steps match
        steps_match = (len(pred_steps) == len(exp_steps))
        if steps_match:
            for s1, s2 in zip(pred_steps, exp_steps):
                for k in ["phase", "operation", "system_id", "resource_id", "state", "evidence_id"]:
                    if s1.get(k) != s2.get(k):
                        steps_match = False
                        break
                if not steps_match:
                    break

        if st_match and steps_match:
            exact_matches += 1
            print(f"[PASS] {cid:8s} | Status: {pred_status:14s} | Steps: {len(pred_steps):2d}")
        else:
            print(f"[FAIL] {cid:8s} | Status: pred={pred_status:12s} exp={exp_status:12s} | Steps: pred={len(pred_steps):2d} exp={len(exp_steps):2d}")
            if pred_status != exp_status:
                print(f"       Status mismatch: expected {exp_status}, got {pred_status}")
            if not steps_match:
                print(f"       Steps diff:")
                print(f"         Expected: {exp_steps}")
                print(f"         Actual:   {pred_steps}")

    print("=" * 70)
    print(f"SUMMARY: Status Accuracy: {status_matches}/{total} ({status_matches/total*100:.1f}%)")
    print(f"         Exact Match:     {exact_matches}/{total} ({exact_matches/total*100:.1f}%)")

    if exact_matches == total:
        print("\nSUCCESS: All 32 sample cases passed with 100% exact match!")
        return 0
    else:
        print(f"\nWARNING: {total - exact_matches} cases need convergence in Ralph Loop.")
        return 1

if __name__ == "__main__":
    code = validate()
    sys.exit(code)
