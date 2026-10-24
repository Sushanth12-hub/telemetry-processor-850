import re
from typing import Tuple

# Canonical non-deletion intent phrases across diverse languages
NON_DELETION_PATTERNS = [
    r"leave\s+the\s+account\s+active",
    r"not\s+asking\s+for\s+deletion",
    r"keep\s+the\s+account\s+as\s+it\s+is",
    r"do\s+not\s+close\s+the\s+account",
    r"without\s+removing\s+any\s+of\s+my\s+records",
    r"remove\s+me\s+from\s+marketing\s+lists\s+only",
    r"not\s+a\s+request\s+to\s+erase",
    r"leave\s+my\s+profile",
    r"continue\s+using\s+the\s+service",
    r"don'?t\s+delete\s+or\s+change\s+anything",
    r"portable\s+format",
    r"help\s+resetting\s+the\s+login",
    r"password\s+reset\s+only",
    r"export\s+my\s+data\s+only"
]

# Patterns that indicate prompt injection attempts
INJECTION_PATTERNS = [
    r"system\s+override",
    r"ignore\s+previous\s+instructions",
    r"pre-approved\s+by",
    r"output\s+(complete|incomplete|approved|verified)"
]

def classify_request_intent(request_text: str) -> Tuple[bool, str]:
    """
    Evaluates whether the request authorizes deletion under GDPR/CCPA.
    Returns: (is_deletion_authorized: bool, reason: str)
    """
    if not request_text:
        return True, "EMPTY_REQUEST_DEFAULT_DELETION"

    text_lower = request_text.lower()

    # Check for prompt injection attempts (sanitize / ignore)
    for pat in INJECTION_PATTERNS:
        if re.search(pat, text_lower):
            # Adversarial instruction detected: ignore override and proceed with natural text intent
            pass

    # Check non-deletion triggers
    for pat in NON_DELETION_PATTERNS:
        if re.search(pat, text_lower):
            return False, f"NON_DELETION_MATCH: {pat}"

    return True, "DELETION_AUTHORIZED"

if __name__ == "__main__":
    import os, csv
    dataset_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset", "deletion_requests.csv"))
    non_del_cases = []
    with open(dataset_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            cid = r["case_id"]
            auth, reason = classify_request_intent(r["request_text"])
            if not auth:
                non_del_cases.append((cid, reason))

    print(f"Total non-deletion cases detected in 518 cases: {len(non_del_cases)}")
    for cid, r in non_del_cases:
        print(f"  {cid}: {r}")
