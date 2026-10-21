"""The maintenance data contract (SaaS milestone S1).

A dataset is not a domain. Before a figure about downtime or reliability
means anything, four things have to be settled: what one row *is*, what
each column measures and on what scale, which rows a measure applies to,
and which columns were knowable before the decision the model supports.
This module states those four things once, so the KPI register, the
governed stages, the model targets and the dashboard all read the same
answer instead of each inventing one.

It is a description, never a transformation. Nothing here rewrites a
source value. A column that does not meet the contract is reported as
not meeting it, because the alternative - quietly coercing it - is how a
dataset comes to disagree with itself.

The contract is deliberately separate from `server/detectors.py`. The
detectors are domain-agnostic and ask "is this dataset internally
coherent?". The contract is domain-specific and asks "is this a
maintenance dataset, and which parts of it can this product speak
about?". Keeping them apart is what lets the detectors transfer to data
nobody has seen while the contract stays opinionated about maintenance.
"""

from collections import OrderedDict

# --- Scales -----------------------------------------------------------
# A name is not a scale. A column called *_Pct holding 0.97 is a
# fraction, and reporting it as 97% or as 0.97% are both wrong, so the
# scale is declared rather than guessed from the name.
COUNT = "count"
HOURS = "hours"
MONEY = "money"
FRACTION = "fraction"       # 0 to 1
PERCENT = "percent"         # 0 to 100
RATIO = "ratio"             # one total as a multiple of another ("4.5 times")
SCORE = "score"             # a bounded index with no natural unit
CATEGORY = "category"
DATE = "date"
IDENTIFIER = "identifier"

# --- Timing -----------------------------------------------------------
# Whether a column could have been known when the decision was taken.
# This is the single most consequential field here: a model fed OUTCOME
# columns scores beautifully and is useless, and the engine cannot infer
# timing from data that carries one date per row.
BEFORE = "before"           # available at decision time
OUTCOME = "outcome"         # observed after the work happened
DERIVED = "derived"         # computed from others; inherits their timing
UNKNOWN = "unknown"         # timing not established - must be stated, not assumed


class Field:
    """One column's meaning, scale, timing and population rule."""

    def __init__(self, name, scale, timing, meaning, *, population=None,
                 aliases=(), required=False, notes=None):
        self.name = name
        self.scale = scale
        self.timing = timing
        self.meaning = meaning
        # Which rows this field is measured on. None means every row.
        self.population = population
        self.aliases = tuple(aliases)
        self.required = required
        self.notes = notes

    def matches(self, column):
        """Whether a dataset column is this field, by name or alias."""
        candidate = column.strip().lower().replace(" ", "_")
        return candidate == self.name.lower() or candidate in {
            a.lower() for a in self.aliases}

    def __repr__(self):
        return f"Field({self.name!r}, {self.scale}, {self.timing})"


# --- The fields -------------------------------------------------------
# Only what this product actually reasons about. A maintenance export
# carries more columns than this, and they are preserved and ignored
# rather than forced into a role they do not have.

FIELDS = (
    Field("Record_ID", IDENTIFIER, BEFORE,
          "The maintenance record. The unit of analysis.", required=True),
    Field("Record_Date", DATE, BEFORE,
          "When the record was raised.", required=True),
    Field("Asset_ID", IDENTIFIER, BEFORE,
          "The asset the record concerns.",
          notes="Must be checked for identity stability before any per-asset "
                "claim. A label that mixes asset classes is not an asset."),

    Field("Work_Order_Type", CATEGORY, BEFORE,
          "Preventive or corrective work."),
    Field("Failure_Mode", CATEGORY, OUTCOME,
          "How the asset failed, known once it has.",
          notes="Encodes whether a failure happened at all, so it leaks any "
                "failure target."),
    Field("Criticality", CATEGORY, BEFORE, "Consequence class of the asset."),
    Field("Maintenance_Strategy", CATEGORY, BEFORE,
          "How the asset is maintained."),
    Field("Site", CATEGORY, BEFORE, "Where the asset sits."),
    Field("Technician_Team", CATEGORY, BEFORE, "Who did the work."),
    Field("Shift", CATEGORY, BEFORE, "When the work was done."),

    Field("Asset_Age_Years", COUNT, BEFORE, "Age at the time of the record."),
    Field("Operating_Hours", HOURS, OUTCOME, "Hours actually run."),
    Field("Planned_Operating_Hours", HOURS, BEFORE, "Hours the asset was meant to run."),
    Field("Downtime_Hours", HOURS, OUTCOME, "Hours lost to this record."),
    Field("Failure_Count", COUNT, OUTCOME, "Failures recorded."),

    Field("Preventive_WO_Count", COUNT, OUTCOME, "Preventive orders on the record."),
    Field("Corrective_WO_Count", COUNT, OUTCOME, "Corrective orders on the record."),
    Field("Completed_WO_Count", COUNT, OUTCOME, "Orders completed."),
    Field("Overdue_WO_Count", COUNT, OUTCOME, "Orders past their due date."),
    Field("First_Time_Fix_Count", COUNT, OUTCOME,
          "Repairs that held first time.",
          population="Work_Order_Type == 'Corrective'"),
    Field("Repeat_Repair_Count", COUNT, OUTCOME,
          "Repairs that came back.",
          population="Work_Order_Type == 'Corrective'"),

    Field("MTBF_Hours", HOURS, DERIVED, "Mean operating hours between failures.",
          population="records with at least one failure",
          notes="On a record with no failure a stored value is a censored lower "
                "bound, not a failure interval. Never average it; the register's "
                "mtbf is total operating hours over total failures."),
    Field("MTTR_Hours", HOURS, DERIVED, "Mean hours to restore.",
          notes="Behaves as downtime per failure (the restoration-time variant), "
                "not active repair time. The register's mttr is total downtime "
                "over total failures."),

    Field("Maintenance_Cost_USD", MONEY, OUTCOME, "Total maintenance spend."),
    Field("Spare_Parts_Cost_USD", MONEY, OUTCOME, "Parts component of spend."),
    Field("Labor_Cost_USD", MONEY, OUTCOME, "Labour component of spend.",
          notes="Parts plus labour need not reconcile to the total. Check "
                "before presenting the three as an accounting identity."),
    Field("Production_Loss_USD", MONEY, OUTCOME,
          "Value of lost output attributed to the downtime.",
          notes="Usually the source's own valuation rather than a measured "
                "amount. Report the basis or say it is undocumented."),

    Field("Temperature_C", SCORE, UNKNOWN, "Sensor reading."),
    Field("Vibration_mm_s", SCORE, UNKNOWN, "Sensor reading."),
    Field("Pressure_Bar", SCORE, UNKNOWN, "Sensor reading."),
    Field("Condition_Score", SCORE, UNKNOWN, "Composite condition."),

    Field("Availability_Pct", FRACTION, DERIVED,
          "Share of planned hours the asset was available.",
          notes="Named percent; commonly stored 0 to 1. Confirm the scale and "
                "which definition it uses before quoting it."),
    Field("Utilization_Pct", FRACTION, DERIVED, "Share of capacity used."),
    Field("SLA_Target_Hours", HOURS, BEFORE, "Response time promised."),
    Field("SLA_Actual_Hours", HOURS, OUTCOME, "Response time achieved."),
    Field("Inventory_Stockout_Count", COUNT, OUTCOME, "Parts unavailable when needed."),
    Field("Spare_Parts_Lead_Days", COUNT, BEFORE, "Days to obtain a part."),
    Field("Safety_Incident_Count", COUNT, OUTCOME, "Safety incidents."),
)

BY_NAME = OrderedDict((f.name, f) for f in FIELDS)
REQUIRED = tuple(f.name for f in FIELDS if f.required)


def resolve(columns):
    """Map a dataset's columns onto contract fields.

    Returns (mapping, unmapped). `mapping` is column -> Field for what the
    product understands; `unmapped` is every other column, preserved and
    reported rather than dropped, because a column this product does not
    model is still the customer's data.
    """
    mapping, unmapped = OrderedDict(), []
    for column in columns:
        for field in FIELDS:
            if field.matches(column):
                mapping[column] = field
                break
        else:
            unmapped.append(column)
    return mapping, unmapped


def tier(columns):
    """How far this product can speak about a dataset.

    Three answers, and the system says which one it is rather than
    degrading quietly:

    - "maintenance": the required fields and enough measures are present.
    - "general": tabular, but not a maintenance dataset. Governance and
      descriptive work still apply; the domain agents stand down by name.
    - "unusable": not enough to analyse at all.
    """
    mapping, _ = resolve(columns)
    if not columns:
        return "unusable"
    present = {f.name for f in mapping.values()}
    missing_required = [n for n in REQUIRED if n not in present]
    measures = [f for f in mapping.values()
                if f.scale in (HOURS, MONEY, COUNT) and f.timing != BEFORE]
    if not missing_required and len(measures) >= 3:
        return "maintenance"
    if len(columns) >= 2:
        return "general"
    return "unusable"


def model_inputs(columns):
    """Columns legitimately usable to predict, and why the rest are not.

    Returns (usable, excluded) where `excluded` maps a column to the
    reason. Timing is the whole point: an OUTCOME column is excluded even
    when it correlates beautifully, and an UNKNOWN one is excluded with a
    different reason, because "we did not establish this" is not the same
    claim as "this is not available".
    """
    mapping, unmapped = resolve(columns)
    usable, excluded = [], OrderedDict()
    for column, field in mapping.items():
        if field.scale == IDENTIFIER:
            excluded[column] = "an identifier, not a measurement"
        elif field.timing == OUTCOME:
            excluded[column] = "recorded after the outcome; using it leaks the target"
        elif field.timing == DERIVED:
            excluded[column] = "derived from outcome columns, so it carries their timing"
        elif field.timing == UNKNOWN:
            excluded[column] = ("reading time not established; treat as an assumption "
                                "and report the sensitivity of dropping it")
        else:
            usable.append(column)
    for column in unmapped:
        excluded[column] = "not in the maintenance contract; timing unknown"
    return usable, excluded
