import os
import sys
import csv
import json
import time
import argparse
from typing import List, Dict, Any

# Ensure module import resolution
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
code_dir = os.path.join(repo_root, "code")
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from engine import DeletionAuditEngine
except (ImportError, ModuleNotFoundError):
    from code.engine import DeletionAuditEngine

def run_pipeline(dataset_dir: str, requests_file: str, output_file: str):
    start_time = time.time()
    print("=" * 80)
    print(" HACKERRANK ORCHESTRATE: GHOST DATA STILL EXISTS")
    print(" PRODUCTION PIPELINE EXECUTION ('LLM DESCRIBES, PYTHON DECIDES')")
    print("=" * 80)
    print(f"Dataset Directory : {dataset_dir}")
    print(f"Requests Input    : {requests_file}")
    print(f"Target Output     : {output_file}")
    print("-" * 80)

    # 1. Initialize Engine
    t0 = time.time()
    print("Initializing Multi-Modal Evidence Indexer & Deletion Audit Engine...")
    engine = DeletionAuditEngine(dataset_dir)
    print(f"Engine initialized in {time.time() - t0:.2f} seconds.")

    # 2. Load Requests
    with open(requests_file, "r", encoding="utf-8") as f:
        requests = list(csv.DictReader(f))
    total_cases = len(requests)
    print(f"Loaded {total_cases} requests from {os.path.basename(requests_file)}.")

    # 3. Process each case
    results: List[Dict[str, str]] = []
    status_counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}
    total_steps = 0

    print("\nAuditing cases across all subsystems...")
    for idx, req in enumerate(requests, start=1):
        cid = req["case_id"]
        email = req["email"]
        req_text = req.get("request_text", "")
        audit_at = req["audit_at"]

        status, steps = engine.audit_case(
            case_id=cid,
            email=email,
            request_text=req_text,
            audit_at=audit_at,
            requested_at=req.get("requested_at")
        )

        steps_str = json.dumps(steps, separators=(",", ":"))
        results.append({
            "case_id": cid,
            "deletion_status": status,
            "steps_json": steps_str
        })

        status_counts[status] = status_counts.get(status, 0) + 1
        total_steps += len(steps)

        if idx % 50 == 0 or idx == total_cases:
            print(f"  Processed [{idx:3d}/{total_cases:3d}] cases... (Latest: {cid} -> {status})")

    # 4. Write output.csv
    print(f"\nWriting results to {output_file}...")
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "deletion_status", "steps_json"])
        writer.writeheader()
        writer.writerows(results)

    elapsed = time.time() - start_time
    print("-" * 80)
    print("PIPELINE EXECUTION SUMMARY:")
    print(f"  Total Cases Processed : {total_cases}")
    print(f"  COMPLETE Cases        : {status_counts.get('COMPLETE', 0)}")
    print(f"  INCOMPLETE Cases      : {status_counts.get('INCOMPLETE', 0)}")
    print(f"  NOT_APPLICABLE Cases  : {status_counts.get('NOT_APPLICABLE', 0)}")
    print(f"  Total Action Steps    : {total_steps}")
    print(f"  Total Execution Time  : {elapsed:.2f} s ({elapsed / total_cases * 1000:.1f} ms/case)")
    print(f"  Output CSV Created    : {os.path.abspath(output_file)} ({os.path.getsize(output_file)} bytes)")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(description="HackerRank Orchestrate Ghost Data Audit Pipeline")
    parser.add_argument("--dataset-dir", default=os.path.join(repo_root, "dataset"), help="Path to dataset directory")
    parser.add_argument("--requests", default=None, help="Path to input deletion requests CSV")
    parser.add_argument("--output", default=os.path.join(repo_root, "output.csv"), help="Path to output CSV")
    args = parser.parse_args()

    requests_path = args.requests
    if not requests_path:
        default_prod = os.path.join(args.dataset_dir, "deletion_requests.csv")
        default_sample = os.path.join(args.dataset_dir, "sample_deletion_requests.csv")
        requests_path = default_prod if os.path.exists(default_prod) else default_sample

    run_pipeline(args.dataset_dir, requests_path, args.output)

if __name__ == "__main__":
    main()
