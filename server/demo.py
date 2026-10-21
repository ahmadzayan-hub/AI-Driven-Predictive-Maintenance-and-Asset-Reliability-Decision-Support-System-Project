"""The view-only public demo (ADR 2026-10-21 demo mode).

When AGENTIC_OS_DEMO=1 every visitor is the same read-only principal, so
the demo needs something to read: one fictional fleet dataset and one
analysis of it, owned by that principal. They are made here, on the
server, because no visitor may write. Every record is generated, so no
real organisation's data can reach the demo.
"""

import random

from server import datasets as dataset_reader

GOAL = "Review fleet maintenance performance for 2025 (fictional demo data)"
DATASET_NAME = "demo-fleet-fictional.csv"
PROFILE = "maintenance"
COLUMNS = (
    "month,Site,Record_ID,Work_Order_Type,Downtime_Hours,Operating_Hours,"
    "Planned_Operating_Hours,Preventive_WO_Count,Corrective_WO_Count,"
    "Completed_WO_Count,First_Time_Fix_Count,Repeat_Repair_Count,"
    "Overdue_WO_Count,Maintenance_Cost_USD,Production_Loss_USD"
)
SITES = ("North", "South", "East", "West")


def fleet_csv(seed=7):
    """240 generated records: 12 months, 4 sites, 5 records each. The
    same seed gives the same file, so every cold start shows the same
    figures."""
    rng = random.Random(seed)
    rows = [COLUMNS]
    number = 0
    for month in range(1, 13):
        for site in SITES:
            for _ in range(5):
                number += 1
                kind = rng.choice(("Corrective", "Preventive"))
                planned = 400
                down = round(rng.uniform(2, 30), 1)
                operating = round(planned - down - rng.uniform(0, 10), 1)
                preventive = rng.randint(2, 8) if kind == "Preventive" else 0
                corrective = rng.randint(1, 9) if kind == "Corrective" else 0
                fixed = round(corrective * rng.uniform(0.6, 0.95))
                rows.append(",".join(str(v) for v in (
                    f"2025-{month:02d}", site, f"FICTIONAL-{number:04d}", kind,
                    down, operating, planned, preventive, corrective,
                    preventive + corrective, fixed, corrective - fixed,
                    rng.randint(0, 2), rng.randint(200, 4000), rng.randint(0, 9000))))
    return "\n".join(rows) + "\n"


def mapping():
    roles = {name: "measure" for name in COLUMNS.split(",")}
    roles.update(month="date", Site="dimension", Record_ID="ignore",
                 Work_Order_Type="dimension")
    return {"roles": roles, "measure": "Downtime_Hours", "dimension": "Site",
            "date_order": "auto", "grain": "month"}


def seed(engine, owner, profile=PROFILE, max_steps=200):
    """Make the demo's dataset and analysis once. Returns the run, or
    None when the owner already has one (a warm restart on a lasting
    database), so a demo never accumulates copies."""
    if engine.list_runs(owner=owner):
        return None
    parsed = dataset_reader.read(fleet_csv().encode("utf-8"), DATASET_NAME, "csv", None)
    # The maintenance profile feeds Asset Intelligence as well as the
    # dashboard; a deployment configured without it still gets a demo.
    if profile not in engine.profiles:
        profile = None
    dataset, _ = engine.store_upload(parsed, DATASET_NAME, owner)
    engine.save_mapping(dataset["id"], owner, mapping(), "en")
    run = engine.create_run(GOAL, owner=owner, dataset_id=dataset["id"],
                            profile=profile, language="en")
    for _ in range(max_steps):
        if run["state"] not in ("queued", "running"):
            break
        run = engine.advance(run["id"])
    return run
