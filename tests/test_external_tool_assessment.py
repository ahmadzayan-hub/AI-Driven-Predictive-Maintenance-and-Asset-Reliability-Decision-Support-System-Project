"""Deterministic offline safety-gate regression tests."""
import importlib.util
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "scripts" / "ExternalToolAssessment.py"
spec = importlib.util.spec_from_file_location("external_tool_assessment", module_path)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

def approved_fixture():
    return {"name":"Fixture","repository":"https://github.com/example/fixture",
    "license_verified":True,"revision_pinned":True,"security_review":"passed",
    "data_classification":"synthetic","external_egress":False,
    "human_owner":"Named reviewer","operational_write_access":False,"runtime":"isolated"}

def test_synthetic_approved_with_evidence():
    assert tool.assess(approved_fixture())["status"] == "ELIGIBLE_FOR_ISOLATED_TRIAL"

def test_missing_required_fields_fail_closed():
    for field in tool.REQUIRED:
        candidate = approved_fixture()
        del candidate[field]
        assert tool.assess(candidate)["status"] == "BLOCKED", field

def test_production_access_and_egress_blocked():
    for field, value in (("operational_write_access",True),("external_egress",True),
                         ("data_classification","restricted"),("security_review","pending")):
        candidate = approved_fixture()
        candidate[field] = value
        assert tool.assess(candidate)["status"] == "BLOCKED", field
