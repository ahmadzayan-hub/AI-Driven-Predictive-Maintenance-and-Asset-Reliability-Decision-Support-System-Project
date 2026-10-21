"""The maintenance KPI register (SaaS milestone S1).

One controlled definition per measure, shared by the governed stages, the
dashboard, the report and the deck. The point of a register is that a
figure cannot mean two things: if the report says first-time fix is 76.6%
and a slide says 64.7%, the disagreement is not a rounding question, it
is two different measures wearing one name.

Four rules are enforced here rather than left to each caller.

**A rate is a ratio of sums.** The numerator and denominator are summed
over the population and then divided. The mean of per-row rates is a
different quantity, and it is available - as `row_mean`, under its own
name - because sometimes it is the one a source published and the job is
to show the two apart, not to pretend only one exists.

**A rate carries its population.** First-time fix is measured on
corrective work. Including rows where the measure does not apply does not
make the estimate more complete, it dilutes it with rows that were never
measured.

**A zero denominator is not perfect performance.** It is an absence, and
it is reported as one.

**A record with nothing to divide by is exposure, not an event.** MTBF is
operating hours over failures, summed over every record. A record with no
failure adds its operating hours to the numerator and nothing to the
denominator: it is censored. Giving it one failure at the end of its hours,
as a stored per-record MTBF does, and then averaging, overstates the result
(the 2026-10-21 decision).

**An unmeasured cell is not a zero** (ADR 0042). A record counts only when
every column the arithmetic reads holds a finite number; the rest are
excluded from the sums and from the record count, and reported as
`records_unmeasured`. A blank means "none happened" only where a KPI
declares `missing=ZERO`, because that is a fact about a source rather
than a default.
"""

import math
from collections import OrderedDict

from . import contract


def _num(value):
    """A finite float, or None.

    None means "not a measurement here" and is never silently treated as
    zero. An infinity or a NaN is also None: both arise from a broken
    upstream calculation, and averaging them produces a figure that looks
    like an answer.
    """
    try:
        number = float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError, AttributeError):
        return None
    return number if math.isfinite(number) else None


def corrective_only(row):
    """Records of corrective work."""
    return str(row.get("Work_Order_Type", "")).strip().lower() == "corrective"


corrective_only.columns = ("Work_Order_Type",)


def with_failure(row):
    """Records where at least one failure was recorded."""
    return (_num(row.get("Failure_Count")) or 0) > 0


with_failure.columns = ("Failure_Count",)


def every_record(row):
    return True


every_record.columns = ()


# A denominator that is the number of records in the population rather
# than the sum of a column. "Per record" is the honest comparison when
# periods or groups hold different numbers of records, so it needs to be
# expressible without inventing a column of ones.
RECORDS = "__records__"

class Count:
    """A term that counts the records satisfying a condition.

    For a share of records, not of a column's total: "the share of jobs that
    met their SLA target" counts jobs. The condition names the columns it
    reads (`columns`) so the register can require them and report a record
    that lacks one as unmeasured instead of as a miss.
    """

    def __init__(self, predicate, columns, description):
        self.predicate = predicate
        self.columns = tuple(columns)
        self.description = description


def met_sla(row):
    """Response time achieved is within the response time promised.

    Equality counts as met: a job finished exactly on target kept its promise.
    """
    actual, target = _num(row.get("SLA_Actual_Hours")), _num(row.get("SLA_Target_Hours"))
    return actual is not None and target is not None and actual <= target


met_sla.columns = ("SLA_Actual_Hours", "SLA_Target_Hours")


# What a KPI does with a record whose formula columns are not all
# measurable. EXCLUDE drops the record from the sums *and* from the
# record count, and reports it; ZERO declares that a blank is a measured
# zero for this KPI. EXCLUDE is the default because the alternative is to
# claim a measurement nobody took: a missing downtime reading counted as
# zero downtime lowers the average and reads as good news. ZERO is only
# correct where the source leaves a count blank to mean none happened,
# which is a fact about that source, so it is declared per KPI and never
# assumed.
EXCLUDE, ZERO = "exclude", "zero"

# Dashboard groups for the register's measures.
FAMILIES = ("reliability", "execution", "cost", "other")

# Each population's Arabic name. The English name stays the code that
# exports and stored policies match on; this is what an Arabic reader sees.
POPULATION_AR = {
    "all records": "جميع السجلات",
    "corrective records": "سجلات الصيانة التصحيحية",
    "records with a failure": "السجلات التي سُجّل فيها عطل",
}
MISSING_POLICIES = (EXCLUDE, ZERO)


class Kpi:
    """One controlled measure.

    `numerator` and `denominator` are each a column name, a tuple of
    column names to be summed, or `RECORDS` for the population's row
    count. A tuple matters: the denominator of a share is often several
    columns added, and spelling that out keeps the formula printable and
    checkable instead of hidden in a caller.

    `scale` is what the *result* is on, which is not always what the
    source columns are on - the commonest way a dashboard ends up a
    hundred times out.
    """

    def __init__(self, key, title, title_ar, numerator, denominator, population,
                 population_name, scale, meaning, *, edge_cases=None,
                 missing=EXCLUDE, complement=False, family=None, definition=1,
                 per=1):
        self.key = key
        # A fixed multiplier for "per 1,000 planned hours" style measures.
        # Still a ratio of sums: the sums are divided first, then scaled.
        self.per = per
        # Raised whenever what the measure means changes, so a display target
        # set for the earlier meaning is held for review (ADR, 21 October).
        self.definition = definition
        self.title = title
        self.title_ar = title_ar
        self.numerator = numerator
        self.denominator = denominator
        self.population = population
        self.population_name = population_name
        self.scale = scale
        self.meaning = meaning
        self.edge_cases = edge_cases or ""
        if missing not in MISSING_POLICIES:
            raise ValueError(f"{key}: missing policy {missing!r} is not one of "
                             f"{', '.join(MISSING_POLICIES)}")
        self.missing = missing
        # True for a measure defined as one minus a ratio of sums, such as
        # availability: the time NOT lost. The result is still a ratio of
        # sums, taken from the complement, so no per-record rate is averaged.
        self.complement = complement
        # The group a dashboard shows this measure in. A grouping only, never
        # a verdict: whether a figure is good is a target's job (performance).
        if family is not None and family not in FAMILIES:
            raise ValueError(f"{key}: family {family!r} is not one of {', '.join(FAMILIES)}")
        if population_name not in POPULATION_AR:
            raise ValueError(f"{key}: population {population_name!r} has no Arabic name in POPULATION_AR")
        self.family = family or "other"

    @staticmethod
    def _columns(term):
        """A term as the tuple of columns it reads."""
        if isinstance(term, Count):
            return term.columns
        if term == RECORDS:
            return ()
        return (term,) if isinstance(term, str) else tuple(term)

    @classmethod
    def _describe(cls, term):
        if isinstance(term, Count):
            return f"count(records where {term.description})"
        if term == RECORDS:
            return "count(records)"
        return f"sum({' + '.join(cls._columns(term))})"

    def _total(self, term, rows):
        """The sum of a term over rows already known to be measurable.

        No `or 0` here. An unmeasured cell is not a zero, and deciding
        that is `measurable` and `compute`'s job, above this arithmetic.
        """
        if isinstance(term, Count):
            return float(sum(1 for row in rows if term.predicate(row)))
        if term == RECORDS:
            return float(len(rows))
        total = 0.0
        for row in rows:
            for column in self._columns(term):
                number = _num(row.get(column))
                # Under EXCLUDE every cell here is already a number;
                # under ZERO a blank is this source's way of writing none.
                total += 0.0 if number is None else number
        return total

    def measurable(self, row):
        """Whether every column this KPI's arithmetic reads is a number.

        Under the ZERO policy a blank counts as a measured zero, so every
        row qualifies. Under EXCLUDE a row with a gap in the formula is
        not a record this measure can speak for.
        """
        if self.missing == ZERO:
            return True
        return all(_num(row.get(c)) is not None for c in self.formula_columns)

    @property
    def formula(self):
        ratio = f"{self._describe(self.numerator)} / {self._describe(self.denominator)}"
        if self.per != 1:
            ratio = f"{self.per:,} × {ratio}"
        return f"1 - {ratio}" if self.complement else ratio

    @property
    def formula_columns(self):
        """Columns the arithmetic reads, each named once."""
        seen, out = set(), []
        for column in self._columns(self.numerator) + self._columns(self.denominator):
            if column not in seen:
                seen.add(column)
                out.append(column)
        return tuple(out)

    @property
    def population_columns(self):
        """Columns the population predicate reads.

        Without these the predicate silently matches nothing or
        everything, and the KPI is reported on a population that was
        never actually selected.
        """
        return tuple(getattr(self.population, "columns", ()))

    @property
    def source_columns(self):
        """Every column this KPI needs, formula and population alike."""
        seen, out = set(), []
        for column in self.formula_columns + self.population_columns:
            if column not in seen:
                seen.add(column)
                out.append(column)
        return tuple(out)

    def rows_in_population(self, rows):
        return [r for r in rows if self.population(r)]

    def compute(self, rows):
        """The measure, as a ratio of sums over its own population.

        Returns a result dict rather than a bare number, because a figure
        without its population, its denominator and its row count is not
        auditable, and every consumer here needs those to print a claim.
        """
        population = self.rows_in_population(rows)
        measured = [r for r in population if self.measurable(r)]
        unmeasured = len(population) - len(measured)
        numerator = self._total(self.numerator, measured)
        denominator = self._total(self.denominator, measured)
        value = None if denominator == 0 else numerator / denominator
        if value is not None and self.complement:
            value = 1 - value
        if value is not None:
            value *= self.per
        if self.scale == contract.PERCENT and value is not None:
            value *= 100
        if not measured and population:
            undefined = (f"no record in the {self.population_name} population has "
                         f"a measurement in every column of {self.formula}, so the "
                         f"measure is undefined rather than zero")
        elif value is None:
            undefined = (f"{self._describe(self.denominator)} is zero over the "
                         f"population, so the measure is undefined rather "
                         f"than zero")
        else:
            undefined = None
        return {
            "key": self.key,
            "title": self.title,
            "title_ar": self.title_ar,
            "value": value,
            "scale": self.scale,
            "numerator": numerator,
            "denominator": denominator,
            "formula": self.formula,
            "population": self.population_name,
            "population_ar": POPULATION_AR[self.population_name],
            "definition": self.definition,
            # `records` is what the figure is actually computed on, so a
            # reader dividing numerator by it gets the printed value.
            # The two counts beside it say who was left out and why.
            "records": len(measured),
            "records_excluded": len(rows) - len(population),
            "records_unmeasured": unmeasured,
            "missing_policy": self.missing,
            "family": self.family,
            # An absence, said out loud. A caller that prints 0% here is
            # claiming perfection from no evidence.
            "undefined_reason": undefined,
            "edge_cases": self.edge_cases,
        }

    def row_mean(self, rows, column):
        """The mean of a stored per-row rate - a *different* measure.

        Provided so the two can be shown side by side when a source
        published the row average, with the gap stated. Never substitute
        it for `compute`.
        """
        population = self.rows_in_population(rows)
        values = [_num(r.get(column)) for r in population]
        values = [v for v in values if v is not None]
        if not values:
            return None
        mean = sum(values) / len(values)
        return mean * 100 if self.scale == contract.PERCENT else mean


REGISTER = OrderedDict()


def _add(kpi):
    REGISTER[kpi.key] = kpi
    return kpi


_add(Kpi("preventive_share", "Preventive share of work orders",
         "نسبة أوامر العمل الوقائية",
         "Preventive_WO_Count",
         ("Preventive_WO_Count", "Corrective_WO_Count"), every_record,
         "all records", contract.PERCENT,
         "How much of the completed work was planned rather than reactive.",
         edge_cases="Measured against preventive plus corrective work, not "
                    "against every completed order: the completed count may "
                    "cover a wider population and gives a different, higher "
                    "figure for the same words.",
         family="execution"))

_add(Kpi("first_time_fix", "First-time fix rate", "معدل الإصلاح من المرة الأولى",
         "First_Time_Fix_Count", "Corrective_WO_Count", every_record,
         "all records", contract.PERCENT,
         "Share of corrective work that held without a return visit.",
         # 2: was summed over records typed "Corrective" only until 21 October.
         definition=2,
         edge_cases="Corrective work orders counted wherever a record carries "
                    "them, as the Power BI Method page defines it: a record "
                    "typed preventive with corrective counts on it adds them. "
                    "A record with no corrective work adds 0 to both sums, so "
                    "placeholders do not dilute the rate.",
         family="execution"))

_add(Kpi("repeat_repair", "Repeat repair rate", "معدل تكرار الإصلاح",
         "Repeat_Repair_Count", "Corrective_WO_Count", every_record,
         "all records", contract.PERCENT,
         "Share of corrective work that came back.",
         # 2: was summed over records typed "Corrective" only until 21 October.
         definition=2,
         edge_cases="Same population as first-time fix, so the two agree.",
         family="execution"))

_add(Kpi("overdue_share", "Overdue as a share of completed work",
         "المتأخر كنسبة من الأعمال المنجزة",
         "Overdue_WO_Count", "Completed_WO_Count", every_record,
         "all records", contract.PERCENT,
         "Backlog pressure as a share of completed work.",
         edge_cases="Overdue is a stock at a moment; completed is activity over "
                    "a period. Comparing them is a ratio, not a conservation. "
                    "Not the overdue rate: that divides by all work raised "
                    "(preventive plus corrective), so the two differ for the "
                    "same data.",
         family="execution"))

_add(Kpi("overdue_rate", "Overdue rate of work orders raised",
         "معدل التأخر في أوامر العمل",
         "Overdue_WO_Count",
         ("Preventive_WO_Count", "Corrective_WO_Count"), every_record,
         "all records", contract.PERCENT,
         "Share of the work orders raised that are overdue.",
         edge_cases="A count share, not a standards backlog: a backlog is "
                    "outstanding work hours divided by weekly craft capacity, in "
                    "weeks, which needs fields most exports lack. Matches the "
                    "stored WO_Backlog_Rate per record, pooled.",
         family="execution"))

_add(Kpi("availability", "Availability", "الجاهزية",
         "Downtime_Hours", "Planned_Operating_Hours", every_record,
         "all records", contract.PERCENT,
         "Share of planned time the asset was not down.",
         complement=True,
         # 2: was operating / planned (now utilisation) until 21 October.
         definition=2,
         edge_cases="Operational availability on planned time: 1 - downtime / "
                    "planned, pooled. It is only as complete as the downtime "
                    "recorded: where no preventive downtime is recorded it is "
                    "not technical availability, and it cannot separate logistic "
                    "delay. Operating divided by planned is utilisation, a "
                    "different measure that this register used to publish under "
                    "this name. A stored Availability_Pct column is a per-record "
                    "0-1 fraction; its mean is not this figure.",
         family="reliability"))

_add(Kpi("utilisation", "Utilisation", "نسبة الاستخدام",
         "Operating_Hours", "Planned_Operating_Hours", every_record,
         "all records", contract.PERCENT,
         "Share of planned hours the asset actually ran.",
         edge_cases="Idle time that was planned, or demand that was not there, "
                    "lowers utilisation without any failure. It says how much of "
                    "the plan was used, not how reliable the asset was.",
         family="reliability"))

_add(Kpi("availability_inherent", "Inherent availability (operating-time basis)",
         "الجاهزية الذاتية (على أساس زمن التشغيل)",
         "Operating_Hours", ("Operating_Hours", "Downtime_Hours"), every_record,
         "all records", contract.PERCENT,
         "Operating time as a share of operating time plus downtime.",
         edge_cases="Equals MTBF / (MTBF + MTTR) when every downtime hour follows "
                    "a failure. A different time base from availability, so the "
                    "two differ for the same data: name the variant.",
         family="reliability"))

_add(Kpi("mtbf", "Mean time between failures", "متوسط الزمن بين الأعطال",
         "Operating_Hours", "Failure_Count", every_record,
         "all records", contract.HOURS,
         "Operating hours per failure, for repairable items.",
         edge_cases="Pooled: total operating hours over total failures. A record "
                    "with no failure is censored; its hours count as exposure and "
                    "it adds no failure. Averaging a stored per-record MTBF, "
                    "which gives such a record one failure at the end of its "
                    "hours, overstates the figure. Undefined, not zero or "
                    "infinite, when no failure was recorded.",
         family="reliability"))

_add(Kpi("mttr", "Mean time to restore (downtime per failure)",
         "متوسط زمن الاستعادة (التوقف لكل عطل)",
         "Downtime_Hours", "Failure_Count", every_record,
         "all records", contract.HOURS,
         "Hours of downtime per failure.",
         # 2: counted downtime on records with a failure only until 21 October.
         definition=2,
         edge_cases="All recorded downtime over all failures, as the Power BI "
                    "Method page defines it. Downtime on a record with no "
                    "failure, such as planned work, is counted too, so where "
                    "planned downtime is recorded this overstates time to "
                    "restore a failure. It includes detection, waiting and "
                    "logistic delay; it is not active repair time.",
         family="reliability"))

_add(Kpi("sla_attainment", "SLA attainment", "نسبة تحقيق مستوى الخدمة",
         Count(met_sla, met_sla.columns, "SLA_Actual_Hours <= SLA_Target_Hours"),
         RECORDS, every_record,
         "all records", contract.PERCENT,
         "Share of records that met their service-level target.",
         edge_cases="A record finished exactly on target counts as met. A record "
                    "missing either hour reading is unmeasured, not a miss. The "
                    "mean of min(1, target / actual) is a performance score, not "
                    "attainment, and is deliberately not in this register.",
         family="execution"))

_add(Kpi("downtime_per_record", "Downtime per record", "التوقف لكل سجل",
         "Downtime_Hours", RECORDS, every_record,
         "all records", contract.HOURS,
         "Average hours lost per maintenance record.",
         edge_cases="Per record, not per period: record volume differs between "
                    "periods, so a falling total need not mean less downtime.",
         family="reliability"))

_add(Kpi("downtime_per_1000_planned", "Downtime per 1,000 planned hours",
         "التوقف لكل 1,000 ساعة مخططة",
         "Downtime_Hours", "Planned_Operating_Hours", every_record,
         "all records", contract.HOURS,
         "Hours lost for every 1,000 hours the asset was meant to run.",
         per=1000,
         edge_cases="The same sums as availability, on another scale: it equals "
                    "1,000 × (1 - availability). Unlike downtime per record, "
                    "it does not move when record volume changes.",
         family="reliability"))

_add(Kpi("failures_per_record", "Failures per record", "الأعطال لكل سجل",
         "Failure_Count", RECORDS, every_record,
         "all records", contract.COUNT,
         "Average number of failures on a maintenance record.",
         edge_cases="Per record, not per operating hour: where records cover "
                    "different running time, MTBF is the fairer comparison.",
         family="reliability"))

_add(Kpi("loss_per_record", "Loss per record", "الخسارة لكل سجل",
         "Production_Loss_USD", RECORDS, every_record,
         "all records", contract.MONEY,
         "Average production loss on a maintenance record.",
         edge_cases="Usually the source's own valuation of lost output. Per "
                    "record, so a group with more, smaller records reads lower.",
         family="cost"))

_add(Kpi("loss_to_maintenance_ratio", "Loss to maintenance ratio",
         "نسبة الخسارة إلى تكلفة الصيانة",
         "Production_Loss_USD", "Maintenance_Cost_USD", every_record,
         "all records", contract.RATIO,
         "Production lost for every unit spent on maintenance.",
         edge_cases="Above 1, failures cost more in lost output than the "
                    "maintenance spend. Both totals must cover the same "
                    "assets and period, and the loss valuation must be stated.",
         family="cost"))

_add(Kpi("loss_per_downtime_hour", "Loss per downtime hour", "الخسارة لكل ساعة توقف",
         "Production_Loss_USD", "Downtime_Hours", every_record,
         "all records", contract.MONEY,
         "Economic consequence of an hour of downtime.",
         edge_cases="Usually the source's own valuation. Report the basis, or "
                    "state that it is undocumented.",
         family="cost"))

_add(Kpi("cost_per_operating_hour", "Maintenance cost per operating hour",
         "تكلفة الصيانة لكل ساعة تشغيل",
         "Maintenance_Cost_USD", "Operating_Hours", every_record,
         "all records", contract.MONEY,
         "What it costs to keep the asset running for an hour.",
         edge_cases="Confirm the financial scope of the cost column before "
                    "comparing it across sites or contracts.",
         family="cost"))


def computable(columns):
    """Which KPIs this dataset supports, and why the rest are missing.

    A register entry whose columns are absent is reported as unavailable
    with the columns named, so the gap is legible instead of silently
    producing a blank card.
    """
    available, unavailable = [], OrderedDict()
    present = set(columns)
    for kpi in REGISTER.values():
        missing = [c for c in kpi.source_columns if c not in present]
        if missing:
            unavailable[kpi.key] = f"needs {', '.join(missing)}"
        else:
            available.append(kpi)
    return available, unavailable


def compute_all(columns, rows):
    """Every supported KPI, each with its population and formula."""
    available, unavailable = computable(columns)
    return {"results": [kpi.compute(rows) for kpi in available],
            "unavailable": unavailable}
