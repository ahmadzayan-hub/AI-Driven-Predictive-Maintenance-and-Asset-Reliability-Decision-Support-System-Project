"""What-if scenarios: planned replacement intervals against run to failure (R3).

Owner slice R3 (31 October 2026). For each asset class the reliability model
fits, the standard age-replacement model compares running each unit until it
fails with servicing or replacing it after T days of running:

    failures per day       = F(T) / L(T)
    planned jobs per day   = R(T) / L(T)
    cost per day           = (Cp x R(T) + Cf x F(T)) / L(T)

where R is the class's Weibull survival, F = 1 - R, and L(T) is the average
running time per cycle, the integral of R from 0 to T. Run to failure is the
limit T -> infinity: failures per day 1 / mean life, cost per day Cf / mean
life. Cf is the class's recorded cost per failure (as in R2); Cp the class's
average recorded cost of a preventive record without a failure.

The intervals compared are the owner's (stage option `intervals_days`) or,
by default, a quarter, a half and three quarters of the class's average life.
When both costs are recorded, the interval with the lowest cost per day is
searched for. A class whose failure pattern is not wear (its whole likely
shape range above 1) is told plainly that planned replacement does not
reduce its failures.

Advisory only: a comparison for engineering review. Standard library only.
"""
import math

from server import analytics
from server.maintenance import reliability as R
from server.maintenance import risk_ranking as K

DEFAULT_FRACTIONS = (0.25, 0.5, 0.75)
MAX_INTERVALS = 6
PER = 1000          # figures per 1,000 asset-days
SEARCH_POINTS = 240
MIN_SAVING = 0.01   # an interval must save at least 1% per day to be named


def survival(t, shape, scale):
    return math.exp(-((t / scale) ** shape))


def mean_running(T, shape, scale, steps=2000):
    """Integral of the survival curve from 0 to T, by Simpson's rule."""
    steps += steps % 2
    h = T / steps
    total = survival(0, shape, scale) + survival(T, shape, scale)
    for i in range(1, steps):
        total += (4 if i % 2 else 2) * survival(i * h, shape, scale)
    return total * h / 3


def at_interval(T, shape, scale, cp=None, cf=None):
    """Rates per day for planned replacement after T running days."""
    length = mean_running(T, shape, scale)
    r = survival(T, shape, scale)
    out = {"interval_days": T, "failures": (1 - r) / length, "planned": r / length}
    out["cost"] = (cp * r + cf * (1 - r)) / length if cp is not None and cf is not None else None
    return out


def run_to_failure(shape, scale, cf=None):
    life = scale * math.gamma(1 + 1 / shape)
    return {"interval_days": None, "failures": 1 / life, "planned": 0.0,
            "cost": cf / life if cf is not None else None}


def best_interval(shape, scale, cp, cf):
    """The interval with the lowest cost per day, if it beats run to failure."""
    baseline = run_to_failure(shape, scale, cf)["cost"]
    life = scale * math.gamma(1 + 1 / shape)
    best = None
    for i in range(1, SEARCH_POINTS + 1):
        candidate = at_interval(3 * life * i / SEARCH_POINTS, shape, scale, cp, cf)
        if best is None or candidate["cost"] < best["cost"]:
            best = candidate
    if best["cost"] > baseline * (1 - MIN_SAVING):
        return None
    return best


class WhatIfScenarios:
    """Planned replacement intervals against run to failure, per asset class."""

    role = "what_if_scenarios"
    title = "Scenario Agent — what if we service on a schedule?"
    title_ar = "وكيل السيناريوهات: ماذا لو كانت الصيانة مجدولة؟"
    after = "sensitivity"
    question = "How would failures and cost change with a planned replacement interval?"
    can_fail_run = False

    def __init__(self, intervals_days=None):
        intervals = list(intervals_days or [])
        if len(intervals) > MAX_INTERVALS or not all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                and math.isfinite(v) and v > 0 for v in intervals):
            raise ValueError(f"intervals_days must be up to {MAX_INTERVALS} positive numbers")
        self.intervals = sorted(set(round(v) for v in intervals))

    def _unavailable(self, en, ar):
        return {"status": "succeeded", "summary": en, "claims": [], "calculations": [],
                "quality_checks": [{"name": "field_contract", "passed": False, "detail": en}],
                "output": {"applicable": False, "reason": en, "reason_ar": ar,
                           "classes": [], "human_approval_required": True}}

    def run(self, ctx):
        rows = analytics._rows(ctx)
        columns = list(analytics._columns(ctx))
        asset = R._column(columns, "Asset_ID")
        date = R._column(columns, "Record_Date")
        count = R._column(columns, "Failure_Count")
        if not (asset and date and count):
            return self._unavailable(
                "Scenarios unavailable: they need Asset_ID, Record_Date and Failure_Count. "
                "No scenario was compared.",
                "السيناريوهات غير متاحة: تحتاج Asset_ID وRecord_Date وFailure_Count. "
                "لم تُقارن أي سيناريوهات.")
        group_col = next((c for c in columns if c.strip().lower() == "asset_class"), None)
        kind_col = R._column(columns, "Work_Order_Type")
        cost_cols = [c for c in (R._column(columns, "Maintenance_Cost_USD"),
                                 R._column(columns, "Production_Loss_USD")) if c]
        records, failure_cost, planned_cost = {}, {}, {}
        for row in rows:
            day, failures, unit = R._day(row.get(date)), R._failures(row.get(count)), row.get(asset)
            if day is None or failures is None or unit in (None, ""):
                continue
            group = (str(row.get(group_col) or "").strip() or "unclassified") \
                if group_col else "all assets"
            records.setdefault(group, []).append((str(unit), day, failures))
            amounts = [K._money(row.get(c)) for c in cost_cols]
            if not cost_cols or any(a is None for a in amounts):
                continue
            preventive = (kind_col and failures == 0 and
                          "prevent" in str(row.get(kind_col) or "").lower())
            target = failure_cost if failures > 0 else planned_cost if preventive else None
            if target is not None:
                total, n = target.get(group, (0.0, 0))
                target[group] = (total + sum(amounts), n + 1)
        prepared = sorted(((R.intervals(items), group) for group, items in records.items()),
                          key=lambda item: (-len(item[0][0]), item[1]))
        classes = []
        for index, ((failed, running, _), group) in enumerate(prepared):
            fit = (R.fit(failed, running)
                   if len(failed) >= R.MIN_FAILURES and index < R.MAX_GROUPS else None)
            if fit is None:
                continue
            classes.append(self._compare(group, fit, failure_cost.get(group),
                                         planned_cost.get(group)))
        if not classes:
            return self._unavailable(
                "Scenarios unavailable: no asset class has enough failures for the "
                "reliability model. No scenario was compared.",
                "السيناريوهات غير متاحة: لا توجد فئة أصول فيها أعطال كافية لنموذج "
                "الموثوقية. لم تُقارن أي سيناريوهات.")
        return self._result(ctx, classes)

    def _compare(self, group, fit, failure_cost, planned_cost):
        shape, scale = fit["shape"], fit["scale"]
        cf = failure_cost[0] / failure_cost[1] if failure_cost else None
        cp = planned_cost[0] / planned_cost[1] if planned_cost else None
        costed = cf is not None and cp is not None
        life = fit["mean_life"]
        intervals = self.intervals or [round(f * life) for f in DEFAULT_FRACTIONS]
        options = [at_interval(T, shape, scale, cp if costed else None, cf if costed else None)
                   for T in intervals if T > 0]
        baseline = run_to_failure(shape, scale, cf if costed else None)
        best = best_interval(shape, scale, cp, cf) if costed else None
        return {"group": group, "pattern": R.pattern(fit), "shape": round(shape, 2),
                "cost_per_failure": round(cf) if cf is not None else None,
                "cost_per_planned_job": round(cp) if cp is not None else None,
                "costed": costed, "declared": bool(self.intervals),
                "run_to_failure": baseline, "options": options, "best": best}

    def _result(self, ctx, classes):
        p = self.role + "."
        calcs, claims, lines = [], [], ["## What if: planned replacement intervals", ""]

        def per(value):
            return round(value * PER, 2)

        for i, c in enumerate(classes):
            rtf = c["run_to_failure"]
            ids = [f"{p}c_group_{i}", f"{p}c_rtf_{i}"]
            calcs += [
                {"id": ids[0], "name": "asset_class", "value": c["group"],
                 "method": "classes the reliability model fitted"},
                {"id": ids[1], "name": "run_to_failure_per_1000_days",
                 "value": f"{per(rtf['failures'])} failures"
                          + (f", {round(rtf['cost'] * PER):,} USD" if rtf["cost"] is not None else ""),
                 "method": "1 / Weibull mean life, times the cost per failure, per 1,000 "
                           "asset-days"},
            ]
            for j, o in enumerate(c["options"]):
                ids.append(f"{p}c_option_{i}_{j}")
                calcs.append({
                    "id": ids[-1], "name": f"replace_after_{o['interval_days']}_days",
                    "value": f"{o['interval_days']:,} days: {per(o['failures'])} failures, "
                             f"{per(o['planned'])} planned jobs"
                             + (f", {round(o['cost'] * PER):,} USD" if o["cost"] is not None else ""),
                    "method": "age replacement: F(T) / L(T) failures and R(T) / L(T) planned "
                              "jobs per 1,000 asset-days, L(T) the integral of survival to T"})
            if c["best"] is not None:
                ids.append(f"{p}c_best_{i}")
                calcs.append({"id": ids[-1], "name": "lowest_cost_interval",
                              "value": f"{round(c['best']['interval_days']):,} days: "
                                       f"{round(c['best']['cost'] * PER):,} USD",
                              "method": f"search over {SEARCH_POINTS} intervals up to three "
                                        f"average lives, lowest cost per day"})
            rtf_cost = f"{round(rtf['cost'] * PER):,}" if rtf["cost"] is not None else "n/a"
            lines += [f"### {c['group']} ({c['pattern']}, shape {c['shape']})", "",
                      "| Policy | Failures per 1,000 asset-days | Planned jobs | Cost per 1,000 asset-days (USD) |",
                      "| --- | --- | --- | --- |",
                      f"| Run to failure | {per(rtf['failures'])} | 0 | {rtf_cost} |"]
            for o in c["options"]:
                cost = f"{round(o['cost'] * PER):,}" if o["cost"] is not None else "n/a"
                lines.append(f"| Replace after {o['interval_days']:,} days | "
                             f"{per(o['failures'])} | {per(o['planned'])} | {cost} |")
            lines.append("")
            claim, extra = self._claim(ctx, p, i, c, ids, per)
            claims.append(claim)
            calcs += extra
        claims.append(analytics._claim(
            ctx, p + "cl_assumptions", "assumption",
            "Each scenario replaces or restores a unit to as good as new after the stated "
            "running days, or at failure if sooner, under the class's fitted pattern. "
            "Costs are recorded averages: a failure record's maintenance cost plus "
            "production loss, and a preventive record's cost. The comparison is for "
            "engineering review; no interval changes without approval.",
            "يفترض كل سيناريو استبدال الوحدة أو إعادتها كالجديدة بعد أيام التشغيل المذكورة، "
            "أو عند العطل إن كان أسبق، وفق النمط المقدَّر للفئة. التكاليف متوسطات مسجلة: "
            "تكلفة الصيانة وخسارة الإنتاج في سجل العطل، وتكلفة السجل الوقائي. المقارنة "
            "للمراجعة الهندسية، ولا يتغير أي فاصل دون اعتماد.",
            [f"{p}c_group_0"]))
        lines.append("Figures are per 1,000 asset-days. A comparison for engineering "
                     "review; it changes no maintenance plan.")
        summary = f"Compared planned replacement with run to failure for {len(classes)} asset classes."
        return {"status": "succeeded", "summary": summary, "claims": claims,
                "calculations": calcs,
                "quality_checks": [
                    {"name": "field_contract", "passed": True,
                     "detail": "Asset_ID, Record_Date and Failure_Count available"},
                    {"name": "costs_recorded", "passed": all(c["costed"] for c in classes),
                     "detail": f"{sum(c['costed'] for c in classes)} of {len(classes)} "
                               f"classes have failure and preventive costs"}],
                "output": {"applicable": True, "classes": classes,
                           "intervals_declared": bool(self.intervals),
                           "per_asset_days": PER, "human_approval_required": True,
                           "plan_changed": False, "question": self.question,
                           "report_markdown": "\n".join(lines)}}

    def _claim(self, ctx, p, i, c, ids, per):
        rtf, name = c["run_to_failure"], c["group"]
        if c["pattern"] != "wear":
            en = (f"{name}: planned replacement does not reduce failures for this class, "
                  f"because its failures are not shown to grow with age. Run to failure "
                  f"gives {per(rtf['failures'])} failures per 1,000 asset-days; look at "
                  f"installation, repair quality or condition checks instead.")
            ar = (f"{name}: الاستبدال المخطط لا يقلل أعطال هذه الفئة، لأن أعطالها لم يثبت "
                  f"أنها تزداد مع العمر. التشغيل حتى العطل يعطي {per(rtf['failures'])} عطلًا "
                  f"لكل 1,000 يوم تشغيل للأصل؛ ويُنظر بدلًا من ذلك في التركيب أو جودة "
                  f"الإصلاح أو فحوص الحالة.")
            return analytics._claim(ctx, f"{p}cl_scenario_{i}", "limitation", en, ar,
                                    ids[:2]), []
        if c["best"] is not None:
            best = c["best"]
            saving = round(100 * (1 - best["cost"] / rtf["cost"]))
            en = (f"{name}: replacing after about {round(best['interval_days']):,} running "
                  f"days costs {round(best['cost'] * PER):,} USD per 1,000 asset-days against "
                  f"{round(rtf['cost'] * PER):,} USD for run to failure, about {saving}% less, and "
                  f"cuts failures from {per(rtf['failures'])} to {per(best['failures'])}.")
            ar = (f"{name}: الاستبدال بعد نحو {round(best['interval_days']):,} يوم تشغيل "
                  f"يكلف {round(best['cost'] * PER):,} دولار لكل 1,000 يوم تشغيل للأصل مقابل "
                  f"{round(rtf['cost'] * PER):,} دولار للتشغيل حتى العطل، أي أقل بنحو {saving}%، "
                  f"ويخفض الأعطال من {per(rtf['failures'])} إلى {per(best['failures'])}.")
            extra = [{"id": f"{p}c_failures_best_{i}",
                      "name": "failures_at_lowest_cost_interval",
                      "value": per(best["failures"]),
                      "method": "F(T) / L(T) per 1,000 asset-days at the lowest-cost interval"},
                     {"id": f"{p}c_saving_{i}", "name": "saving_against_run_to_failure",
                      "value": saving / 100, "method": "1 - lowest cost per day / run-to-failure "
                                                       "cost per day"}]
            claim = analytics._claim(ctx, f"{p}cl_scenario_{i}", "recommendation", en, ar,
                                     ids + [e["id"] for e in extra])
            return claim, extra
        options = "; ".join(f"after {o['interval_days']:,} days {per(o['failures'])}"
                            for o in c["options"])
        options_ar = "؛ ".join(f"بعد {o['interval_days']:,} يوم {per(o['failures'])}"
                               for o in c["options"])
        reason = ("no interval saves cost against run to failure" if c["costed"] else
                  "failure and preventive costs are not both recorded, so no interval is "
                  "recommended on cost")
        reason_ar = ("لا يوفر أي فاصل تكلفة مقارنة بالتشغيل حتى العطل" if c["costed"] else
                     "تكلفة العطل والتكلفة الوقائية غير مسجلتين معًا، فلا يُوصى بفاصل على "
                     "أساس التكلفة")
        en = (f"{name}: failures grow with age. Failures per 1,000 asset-days: run to "
              f"failure {per(rtf['failures'])}; replace {options}. {reason[0].upper()}"
              f"{reason[1:]}.")
        ar = (f"{name}: الأعطال تزداد مع العمر. الأعطال لكل 1,000 يوم تشغيل للأصل: التشغيل "
              f"حتى العطل {per(rtf['failures'])}؛ الاستبدال {options_ar}. {reason_ar}.")
        return analytics._claim(ctx, f"{p}cl_scenario_{i}", "calculation", en, ar, ids), []
