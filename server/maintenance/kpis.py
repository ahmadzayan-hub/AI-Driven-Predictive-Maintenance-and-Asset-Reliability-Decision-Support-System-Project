"""The maintenance KPI register (SaaS milestone S1).

One controlled definition per measure, shared by the governed stages, the
dashboard, the report and the deck. The point of a register is that a
figure cannot mean two things: if the report says first-time fix is 76.6%
and a slide says 64.7%, the disagreement is not a rounding question, it
is two different measures wearing one name.

Three rules are enforced here rather than left to each caller.

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
"""

from collections import OrderedDict

from . import contract


def _num(value):
    try:
        return float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError, AttributeError):
        return None


def corrective_only(row):
    """Records of corrective work."""
    return str(row.get("Work_Order_Type", "")).strip().lower() == "corrective"


def with_failure(row):
    """Records where at least one failure was recorded."""
    return (_num(row.get("Failure_Count")) or 0) > 0


def every_record(row):
    return True


# A denominator that is the number of records in the population rather
# than the sum of a column. "Per record" is the honest comparison when
# periods or groups hold different numbers of records, so it needs to be
# expressible without inventing a column of ones.
RECORDS = "__records__"


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
                 population_name, scale, meaning, *, edge_cases=None):
        self.key = key
        self.title = title
        self.title_ar = title_ar
        self.numerator = numerator
        self.denominator = denominator
        self.population = population
        self.population_name = population_name
        self.scale = scale
        self.meaning = meaning
        self.edge_cases = edge_cases or ""

    @staticmethod
    def _columns(term):
        """A term as the tuple of columns it sums over."""
        if term == RECORDS:
            return ()
        return (term,) if isinstance(term, str) else tuple(term)

    @classmethod
    def _describe(cls, term):
        if term == RECORDS:
            return "count(records)"
        return f"sum({' + '.join(cls._columns(term))})"

    def _total(self, term, population):
        if term == RECORDS:
            return float(len(population))
        return sum((_num(r.get(c)) or 0)
                   for r in population for c in self._columns(term))

    @property
    def formula(self):
        return f"{self._describe(self.numerator)} / {self._describe(self.denominator)}"

    @property
    def source_columns(self):
        """Every column this KPI reads."""
        return self._columns(self.numerator) + self._columns(self.denominator)

    def rows_in_population(self, rows):
        return [r for r in rows if self.population(r)]

    def compute(self, rows):
        """The measure, as a ratio of sums over its own population.

        Returns a result dict rather than a bare number, because a figure
        without its population, its denominator and its row count is not
        auditable, and every consumer here needs those to print a claim.
        """
        population = self.rows_in_population(rows)
        numerator = self._total(self.numerator, population)
        denominator = self._total(self.denominator, population)
        value = None if denominator == 0 else numerator / denominator
        if self.scale == contract.PERCENT and value is not None:
            value *= 100
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
            "records": len(population),
            "records_excluded": len(rows) - len(population),
            # An absence, said out loud. A caller that prints 0% here is
            # claiming perfection from no evidence.
            "undefined_reason": (None if value is not None else
                                 f"{self._describe(self.denominator)} is zero over the "
                                 f"population, so the measure is undefined rather "
                                 f"than zero"),
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
                    "figure for the same words."))

_add(Kpi("first_time_fix", "First-time fix rate", "معدل الإصلاح من المرة الأولى",
         "First_Time_Fix_Count", "Corrective_WO_Count", corrective_only,
         "corrective records", contract.PERCENT,
         "Share of corrective work that held without a return visit.",
         edge_cases="Measured on corrective work only. Preventive records "
                    "commonly store a placeholder of 0 and must be excluded, "
                    "not averaged in."))

_add(Kpi("repeat_repair", "Repeat repair rate", "معدل تكرار الإصلاح",
         "Repeat_Repair_Count", "Corrective_WO_Count", corrective_only,
         "corrective records", contract.PERCENT,
         "Share of corrective work that came back.",
         edge_cases="Same population as first-time fix, so the two agree."))

_add(Kpi("overdue_share", "Overdue share of work orders", "نسبة أوامر العمل المتأخرة",
         "Overdue_WO_Count", "Completed_WO_Count", every_record,
         "all records", contract.PERCENT,
         "Backlog pressure as a share of completed work.",
         edge_cases="Overdue is a stock at a moment; completed is activity over "
                    "a period. Comparing them is a ratio, not a conservation."))

_add(Kpi("availability", "Availability", "الجاهزية",
         "Operating_Hours", "Planned_Operating_Hours", every_record,
         "all records", contract.PERCENT,
         "Share of planned hours the asset actually ran.",
         edge_cases="A stored Availability_Pct column may use a different "
                    "definition, usually (planned - downtime) / planned, and may "
                    "be a 0-1 fraction. State which definition a figure uses."))

_add(Kpi("downtime_per_record", "Downtime per record", "التوقف لكل سجل",
         "Downtime_Hours", RECORDS, every_record,
         "all records", contract.HOURS,
         "Average hours lost per maintenance record.",
         edge_cases="Per record, not per period: record volume differs between "
                    "periods, so a falling total need not mean less downtime."))

_add(Kpi("loss_per_downtime_hour", "Loss per downtime hour", "الخسارة لكل ساعة توقف",
         "Production_Loss_USD", "Downtime_Hours", every_record,
         "all records", contract.MONEY,
         "Economic consequence of an hour of downtime.",
         edge_cases="Usually the source's own valuation. Report the basis, or "
                    "state that it is undocumented."))

_add(Kpi("cost_per_operating_hour", "Maintenance cost per operating hour",
         "تكلفة الصيانة لكل ساعة تشغيل",
         "Maintenance_Cost_USD", "Operating_Hours", every_record,
         "all records", contract.MONEY,
         "What it costs to keep the asset running for an hour.",
         edge_cases="Confirm the financial scope of the cost column before "
                    "comparing it across sites or contracts."))


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
