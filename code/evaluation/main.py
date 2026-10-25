import os
import sys
import csv
import json
import unittest

eval_dir = os.path.abspath(os.path.dirname(__file__))
candidate_code_dirs = [
    eval_dir,
    os.path.abspath(os.path.join(eval_dir, "..")),
    os.path.abspath(os.path.join(eval_dir, "..", "code")),
    os.path.abspath(os.path.join(eval_dir, "..", "..", "code")),
    os.path.abspath(os.path.join(os.getcwd(), "code")),
    os.path.abspath(os.getcwd())
]
code_dir = None
for cd in candidate_code_dirs:
    if os.path.isdir(cd) and os.path.exists(os.path.join(cd, "engine.py")):
        code_dir = cd
        if cd not in sys.path:
            sys.path.insert(0, cd)
        break

repo_root = os.path.abspath(os.path.join(code_dir if code_dir else eval_dir, ".."))
for p in [eval_dir, repo_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

def discover_dataset_dir():
    """Dynamically discover dataset directory via environment variable or search paths."""
    if "DATASET_DIR" in os.environ and os.path.exists(os.environ["DATASET_DIR"]):
        return os.path.abspath(os.environ["DATASET_DIR"])

    candidates = [
        os.path.join(repo_root, "dataset"),
        os.path.join(code_dir, "..", "dataset"),
        os.path.join(os.getcwd(), "dataset"),
        os.path.join(os.getcwd(), "..", "dataset"),
        os.path.abspath(os.path.join(eval_dir, "..", "..", "dataset"))
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isdir(c):
            return os.path.abspath(c)
    return None

def run_sample_validation(dataset_dir: str) -> bool:
    """Execute 32-case sample validation directly without external script dependency."""
    try:
        from engine import DeletionAuditEngine
    except (ImportError, ModuleNotFoundError):
        from code.engine import DeletionAuditEngine

    sample_req_path = os.path.join(dataset_dir, "sample_deletion_requests.csv")
    sample_out_path = os.path.join(dataset_dir, "sample_output.csv")

    if not os.path.exists(sample_req_path) or not os.path.exists(sample_out_path):
        print(f"[INFO] Sample benchmark files not found in {dataset_dir}; skipping CSV regression.")
        return True

    print("Initializing DeletionAuditEngine for sample evaluation...")
    engine = DeletionAuditEngine(dataset_dir)

    with open(sample_req_path, "r", encoding="utf-8") as f:
        reqs = list(csv.DictReader(f))

    with open(sample_out_path, "r", encoding="utf-8") as f:
        expected = {r["case_id"]: r for r in csv.DictReader(f)}

    total = len(reqs)
    matches = 0
    print(f"Evaluating {total} sample cases against sample_output.csv:")
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
            audit_at=r["audit_at"],
            requested_at=r.get("requested_at")
        )

        st_match = (pred_status == exp_status)
        steps_match = (pred_steps == exp_steps)

        if st_match and steps_match:
            matches += 1
            print(f"[PASS] {cid:8s} | Status: {pred_status:14s} | Steps: {len(pred_steps):2d}")
        else:
            print(f"[FAIL] {cid:8s} | Status: pred={pred_status} exp={exp_status}")

    print("=" * 70)
    print(f"SUMMARY: Exact Match: {matches}/{total} ({matches/total*100:.1f}%)")
    return matches == total

if __name__ == "__main__":
    print("=" * 70)
    print("TELEMETRY PROCESSOR 850: EVALUATION RUNNER")
    print("=" * 70)

    dataset_dir = discover_dataset_dir()
    if dataset_dir:
        print(f"Discovered Dataset Directory: {dataset_dir}")
        print("\nSTAGE 1: Executing 32-Case Sample Validation Harness")
        print("-" * 70)
        success = run_sample_validation(dataset_dir)
        if not success:
            print("Sample validation did not achieve 100% exact match.")
            sys.exit(1)
    else:
        print("[NOTICE] Running in zero-dataset sandbox environment. Gracefully bypassing CSV regression.")

    print("\nSTAGE 2: Executing Custom Adversarial Evaluation Test Suite")
    print("-" * 70)
    import test_suite
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_suite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if not result.wasSuccessful():
        print("Adversarial test suite failed!")
        sys.exit(1)

    print("\nSUCCESS: All available evaluation suites completed with 100% pass rate.")
    sys.exit(0)
