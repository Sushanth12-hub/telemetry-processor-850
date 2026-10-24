import os
import sys
import unittest

# Runner for all evaluation checks (sample dataset validation + custom test suite)
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
val_script = os.path.join(repo_root, "validate_sample.py")

if __name__ == "__main__":
    print("=" * 70)
    print("STAGE 1: Executing 32-Case Sample Validation Harness")
    print("=" * 70)
    if os.path.exists(val_script):
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        import validate_sample
        ret = validate_sample.validate()
        if ret != 0:
            print(f"Sample validation failed with return code {ret}")
            sys.exit(ret)
    else:
        print("validate_sample.py not found at repository root.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("STAGE 2: Executing Custom Adversarial Evaluation Test Suite")
    print("=" * 70)
    eval_dir = os.path.dirname(__file__)
    if eval_dir not in sys.path:
        sys.path.insert(0, eval_dir)
    import test_suite
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_suite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if not result.wasSuccessful():
        print("Adversarial test suite failed!")
        sys.exit(1)

    print("\nSUCCESS: All sample cases and custom evaluation suites passed 100%!")
    sys.exit(0)
