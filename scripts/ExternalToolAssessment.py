"""Offline third-party AI tool assessment; no installation or network access.
Owner: Ahmed Zaian
"""
import argparse
import json

REQUIRED = ("name", "repository", "license_verified", "revision_pinned", "security_review", "data_classification", "external_egress", "human_owner", "operational_write_access", "runtime")

def assess(candidate):
    issues = ["Missing: " + key for key in REQUIRED if key not in candidate or candidate[key] is None or candidate[key] == ""]
    if not str(candidate.get("repository", "")).startswith("https://github.com/"):
        issues.append("Canonical repository missing")
    if candidate.get("license_verified") is not True:
        issues.append("Licence not verified")
    if candidate.get("revision_pinned") is not True:
        issues.append("Immutable revision not pinned")
    if candidate.get("security_review") != "passed":
        issues.append("Security review not passed")
    if candidate.get("data_classification") not in ("public", "synthetic"):
        issues.append("Only public or synthetic inputs permitted")
    if candidate.get("external_egress") is not False:
        issues.append("Outbound transfers not blocked")
    if not isinstance(candidate.get("human_owner"), str) or not candidate.get("human_owner").strip():
        issues.append("Accountable human reviewer missing")
    if candidate.get("operational_write_access") is not False:
        issues.append("Operational write access must be disabled")
    if candidate.get("runtime") not in ("offline", "isolated"):
        issues.append("Isolated or offline trial required")
    return {"name": candidate.get("name", "unknown"), "status": "BLOCKED" if issues else "ELIGIBLE_FOR_ISOLATED_TRIAL", "issues": sorted(set(issues))}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog")
    args = parser.parse_args()
    with open(args.catalog, encoding="utf-8") as source:
        candidates = json.load(source)
    if not isinstance(candidates, list) or any(not isinstance(x, dict) for x in candidates):
        parser.error("Expected a JSON array of candidate objects")
    result = [assess(x) for x in candidates]
    print(json.dumps({"policy": "fail-closed-v1", "results": result}, ensure_ascii=False, indent=2))
    return 2 if any(x["status"] == "BLOCKED" for x in result) else 0

if __name__ == "__main__":
    raise SystemExit(main())
