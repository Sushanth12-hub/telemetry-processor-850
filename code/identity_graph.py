import os
import csv
import hashlib
from typing import Dict, Set, Optional

class IdentityGraph:
    """
    Transitive Identity Resolution across all 850 users and historical audit logs.
    Connects user_id, current/historical emails, phones, and email hashes.
    """
    def __init__(self, dataset_dir: str):
        self.dataset_dir = dataset_dir
        self.user_bundles: Dict[str, dict] = {}
        self.lookup_to_uid: Dict[str, str] = {}
        self._build_graph()

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower() if email else ""

    def _normalize_phone(self, phone: str) -> str:
        if not phone:
            return ""
        # Standardize stripped phone
        return phone.strip()

    def _compute_hashes(self, text: str) -> Set[str]:
        if not text:
            return set()
        s = text.encode("utf-8")
        return {
            hashlib.sha256(s).hexdigest().lower(),
            hashlib.md5(s).hexdigest().lower()
        }

    def _build_graph(self):
        # 1. Load user_identities.csv
        identities_path = os.path.join(self.dataset_dir, "user_identities.csv")
        with open(identities_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                uid = r["user_id"].strip()
                name = r["name"].strip()
                email = self._normalize_email(r["email"])
                phone = self._normalize_phone(r.get("phone", ""))
                ehash = r.get("email_hash", "").strip().lower()

                emails = {email} if email else set()
                phones = {phone} if phone else set()
                hashes = {ehash} if ehash else set()
                if email:
                    hashes.update(self._compute_hashes(email))

                bundle = {
                    "user_id": uid,
                    "name": name,
                    "primary_email": email,
                    "emails": emails,
                    "phones": phones,
                    "email_hashes": hashes
                }
                self.user_bundles[uid] = bundle
                self.lookup_to_uid[uid.lower()] = uid
                if email:
                    self.lookup_to_uid[email] = uid
                if phone:
                    self.lookup_to_uid[phone] = uid
                for h in hashes:
                    self.lookup_to_uid[h] = uid

        # 2. Load user_audit_log.csv for historical changes
        audit_path = os.path.join(self.dataset_dir, "user_audit_log.csv")
        if os.path.exists(audit_path):
            with open(audit_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    uid = r["user_id"].strip()
                    if uid not in self.user_bundles:
                        continue
                    bundle = self.user_bundles[uid]
                    fn = r.get("field_name", "").strip().lower()
                    old_v = r.get("old_value", "").strip()
                    new_v = r.get("new_value", "").strip()

                    if fn == "email":
                        for em in [old_v, new_v]:
                            nem = self._normalize_email(em)
                            if nem:
                                bundle["emails"].add(nem)
                                bundle["email_hashes"].update(self._compute_hashes(nem))
                                self.lookup_to_uid[nem] = uid
                                for h in self._compute_hashes(nem):
                                    self.lookup_to_uid[h] = uid
                    elif fn == "phone":
                        for ph in [old_v, new_v]:
                            nph = self._normalize_phone(ph)
                            if nph:
                                bundle["phones"].add(nph)
                                self.lookup_to_uid[nph] = uid
                    elif fn == "email_hash":
                        for eh in [old_v, new_v]:
                            neh = eh.lower()
                            if neh:
                                bundle["email_hashes"].add(neh)
                                self.lookup_to_uid[neh] = uid

    def resolve_identifier(self, identifier: Optional[str]) -> Optional[str]:
        """Resolves any email, phone, user_id, or email_hash to canonical user_id."""
        if not identifier or not isinstance(identifier, str):
            return None
        ident_clean = identifier.strip().lower()
        if ident_clean in self.lookup_to_uid:
            return self.lookup_to_uid[ident_clean]
        # Try raw (for phones with spaces)
        raw = identifier.strip()
        if raw in self.lookup_to_uid:
            return self.lookup_to_uid[raw]
        return None

    def get_bundle(self, user_id: str) -> Optional[dict]:
        return self.user_bundles.get(user_id)

    def matches_user(self, user_id: str, candidate_val: Optional[str]) -> bool:
        if not candidate_val or not isinstance(candidate_val, str):
            return False
        c = candidate_val.strip().lower()
        b = self.user_bundles.get(user_id)
        if not b:
            return False
        if c == user_id.lower():
            return True
        if c in b["emails"]:
            return True
        if candidate_val.strip() in b["phones"]:
            return True
        if c in b["email_hashes"]:
            return True
        return False

if __name__ == "__main__":
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset"))
    graph = IdentityGraph(base)
    print(f"Total resolved user identities: {len(graph.user_bundles)}")
    print(f"Total index lookup entries: {len(graph.lookup_to_uid)}")
    # Test user_12 historical email hash resolution
    h_test = "44a65154bfd8e408852578fbd76813d094d1944f255ac1769ee81ba90492f10e"
    print(f"Resolve historical hash {h_test[:10]}... -> {graph.resolve_identifier(h_test)}")
