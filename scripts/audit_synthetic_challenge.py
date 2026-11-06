#!/usr/bin/env python3
"""Offline synthetic MIYAAR challenge fixture audit, no platform tests.

Usage: python scripts/audit_synthetic_challenge.py path/to/MIYAAR_Synthetic_Challenge_Pack_v1.zip
Never interprets data rows as instructions or sends content outside the machine.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = "MIYAAR_Synthetic_Challenge_Pack/"

def audit(archive_path):
    checks = {}
    with zipfile.ZipFile(archive_path) as package:
        members = {name[len(ROOT):]: name for name in package.namelist() if name.startswith(ROOT)}
        def read(name):
            if name not in members:
                raise ValueError("Missing challenge fixture: " + name)
            return package.read(members[name])
        def table(name, encoding="utf-8-sig"):
            return list(csv.DictReader(io.StringIO(read(name).decode(encoding), newline="")))
        manifest = json.loads(read("manifest_sha256.json"))
        mismatches = []
        for entry in manifest["files"]:
            name = entry["path"]
            data = read(name)
            if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                mismatches.append(name)
        checks["manifest_integrity"] = len(mismatches) == 0 and len(manifest["files"]) == 42
        truth = json.loads(read("GROUND_TRUTH.json"))
        events, assets = table("02_maintenance_events_clean.csv"), table("01_asset_registry.csv")
        checks["event_population"] = (len(events) == truth["counts"]["events"] == 7500
            and len(assets) == truth["counts"]["assets"] == 120
            and len({r["record_id"] for r in events}) == len(events))
        checks["failure_labels"] = sum(int(r["failure_next_7d"]) for r in events) == truth["counts"]["failures"] == 258
        train = table("06_train_chronological.csv")
        test = table("07_test_chronological.csv")
        checks["chronological_split"] = (len(train) == 4932 and len(test) == 2568
            and max(r["event_time_utc"] for r in train) < min(r["event_time_utc"] for r in test)
            and not ({r["record_id"] for r in train} & {r["record_id"] for r in test}))
        leak = table("08_leakage_trap.csv")
        checks["leakage_canary"] = {"post_failure_repair_code","future_failure_confirmed"}.issubset(leak[0])
        drift = table("09_distribution_shift.csv")
        checks["drift_fixture"] = len(drift) == 1000 and min(r["event_time_utc"] for r in drift) > max(r["event_time_utc"] for r in test)
        dirty = table("10_data_quality_minefield.csv")
        checks["dirty_fixture"] = (len({r["record_id"] for r in dirty}) < len(dirty)
            and any(r["downtime_hours"].startswith("-") for r in dirty))
        noise = table("11_no_signal_negative_control.csv")
        checks["negative_control"] = len(noise) > 100 and {"noise_a","noise_b","failure_next_7d"}.issubset(noise[0])
        rare = table("12_rare_failure_extreme_imbalance.csv")
        checks["rare_failure"] = len(rare) == 5000 and sum(int(r["failure"]) for r in rare) == 3
        checks["small_history"] = len(table("13_small_sample_no_prediction.csv")) == 3
        checks["causal_trap"] = "selection_bias_group" in table("14_intervention_causal_trap.csv")[0]
        exp = table("15_valid_randomized_experiment.csv")
        checks["experiment"] = {r["group"] for r in exp} == {"treatment","control"} and all(r["assignment_recorded"] == "1" for r in exp)
        arabic = table("16_arabic_rtl_data.csv")
        checks["arabic_fixture"] = bool(arabic) and any("\u0600" <= c <= "\u06ff" for key in arabic[0] for c in key)
        utf16 = read("17_utf16_tsv.tab")
        checks["utf16_tsv"] = utf16.startswith((b"\xff\xfe",b"\xfe\xff")) and "\t" in utf16.decode("utf-16")
        flat = json.loads(read("18_tabular_json.json"))
        checks["tabular_json"] = len(flat) == 120 and all(isinstance(r,dict) for r in flat)
        lines = [json.loads(line) for line in read("19_ndjson_stream.jsonl").decode().splitlines() if line.strip()]
        checks["jsonl"] = len(lines) == 400 and all(isinstance(r,dict) for r in lines)
        checks["nested_json"] = isinstance(json.loads(read("20_nested_json_unsupported.json")), (dict,list))
        try:
            list(csv.reader(io.StringIO(read("21_malformed_csv.csv").decode()), strict=True))
            checks["malformed_csv"] = False
        except csv.Error:
            checks["malformed_csv"] = True
        try:
            json.loads(read("22_malformed_json.json"))
            checks["malformed_json"] = False
        except json.JSONDecodeError:
            checks["malformed_json"] = True
        blank = table("23_empty_table.csv")
        checks["blank_only"] = bool(blank) and all(not any(str(v or "").strip() for v in r.values()) for r in blank)
        checks["formula_canary"] = any(r["notes"].startswith(("=","+","-","@")) for r in table("24_formula_injection_text.csv"))
        checks["prompt_canary"] = any("ignore all previous" in r["note"].lower() for r in table("25_prompt_injection_document_text.csv"))
        checks["wide_501_columns"] = len(next(csv.reader(io.StringIO(read("26_schema_501_columns.csv").decode())))) == 501
        checks["50001_rows"] = read("27_50001_rows_limit.csv").count(b"\n") - 1 == 50001
        checks["over_4mb"] = len(read("28_over_4mb_upload_limit.csv")) > 4_000_000
        constant = table("29_constant_all_null_predictors.csv")
        checks["null_constant"] = len({r["constant"] for r in constant}) == 1 and all(not r["missing"] for r in constant)
        a,b = table("30_join_left_duplicate_keys.csv"), table("31_join_right_duplicate_keys.csv")
        checks["join_explosion"] = sum(x["asset_id"] == y["asset_id"] for x in a for y in b) == 100
        checks["voice_fixture"] = bool(json.loads(read("32_bilingual_narration_cases.json")))
    # These are structural/canary fixture assertions, NOT model/app acceptance.
    failed = sorted(k for k,passed in checks.items() if not passed)
    return {"scope":"synthetic_fixture_only","checks":checks,"passed":len(checks)-len(failed),
            "total":len(checks),"failed":failed,"miyaar_platform_pass":0,
            "requires_app_or_human_test":["T27","T28","T29","T30","T31","T32","T33","T34"]}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/audit_synthetic_challenge.py synthetic_pack.zip")
    report = audit(Path(sys.argv[1]))
    print(json.dumps(report,indent=2,ensure_ascii=False))
    raise SystemExit(1 if report["failed"] else 0)
