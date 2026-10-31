"""Reliability model: how time between failures behaves, per asset class.

Owner slice R1 (31 October 2026). For each asset the stage reads the days
between records that carry a failure, and counts the time since the last
failure (or since the asset was first seen) as still running at the latest
date in the data. A two-parameter Weibull model is fitted to those times by
maximum likelihood with the running times treated as censored, separately
for each asset class. The fitted shape says whether failures come early in
life, at random, or with wear; its likely range comes from the profile
likelihood, so a pattern is named only when the whole range agrees.

Advisory only. It estimates a population pattern, never one asset's
remaining life, and no maintenance decision follows without human review.
Standard library only.
"""
import datetime
import math

from server import analytics
from server.maintenance import contract

MIN_FAILURES = 10          # fewer failure intervals than this: no fit
MAX_GROUPS = 8             # asset classes fitted, the most failures first
CHI2_95 = 3.841458820694124  # one degree of freedom, 95%
SHAPE_BOUNDS = (0.05, 20.0)
MIN_DATED_SHARE = 0.9


def _day(value):
    text = str(value or "").strip()[:10]
    if len(text) < 10:
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def _failures(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0 or not math.isfinite(number) or number != int(number):
        return None
    return int(number)


def _column(columns, field_name):
    field = contract.BY_NAME[field_name]
    return next((c for c in columns if field.matches(c)), None)


def intervals(records):
    """Times in days from (asset, date, failures) records.

    Returns (failure_times, running_times, notes). The clock restarts at each
    failure (a repair is taken as returning the asset to as good as new);
    a failure on the day an asset is first seen, or on the same day as the
    previous one, gives no interval and is counted in notes.
    """
    by_asset = {}
    for asset, day, count in records:
        by_asset.setdefault(asset, []).append((day, count))
    as_of = max(day for _, day, _ in records)
    failure_times, running_times = [], []
    notes = {"no_interval": 0, "several_on_one_record": 0, "as_of": as_of.isoformat(),
             "assets": len(by_asset)}
    for history in by_asset.values():
        history.sort()
        start = history[0][0]
        for day, count in history:
            if count <= 0:
                continue
            notes["several_on_one_record"] += count > 1
            gap = (day - start).days
            if gap > 0:
                failure_times.append(gap)
            else:
                notes["no_interval"] += 1
            start = day
        tail = (as_of - start).days
        if tail > 0:
            running_times.append(tail)
    return failure_times, running_times, notes


def fit(failure_times, running_times):
    """Weibull shape and scale by maximum likelihood with right censoring.

    Returns a dict, or None when the times cannot support a fit (too few
    failures, or no spread to estimate a shape from).
    """
    r = len(failure_times)
    if r < 2:
        return None
    top = max(failure_times + running_times)
    times = [t / top for t in failure_times + running_times]
    log_failed = sum(math.log(t / top) for t in failure_times)

    def sums(shape):
        powered = [t ** shape for t in times]
        return sum(powered), sum(p * math.log(t) for p, t in zip(powered, times))

    def score(shape):
        s0, s1 = sums(shape)
        return s1 / s0 - 1 / shape - log_failed / r

    def loglik(shape):
        s0, _ = sums(shape)
        return r * math.log(shape) - r * math.log(s0 / r) + (shape - 1) * log_failed - r

    low, high = SHAPE_BOUNDS
    if score(low) > 0 or score(high) < 0:
        return None
    for _ in range(200):
        middle = (low + high) / 2
        if score(middle) < 0:
            low = middle
        else:
            high = middle
    shape = (low + high) / 2
    best = loglik(shape)

    def edge(inner, outer):
        if 2 * (best - loglik(outer)) < CHI2_95:
            return outer, True
        for _ in range(200):
            middle = (inner + outer) / 2
            if 2 * (best - loglik(middle)) < CHI2_95:
                inner = middle
            else:
                outer = middle
        return (inner + outer) / 2, False

    shape_low, open_low = edge(shape, SHAPE_BOUNDS[0])
    shape_high, open_high = edge(shape, SHAPE_BOUNDS[1])
    scale = top * (sums(shape)[0] / r) ** (1 / shape)
    return {"shape": shape, "shape_low": shape_low, "shape_high": shape_high,
            "range_open": open_low or open_high, "scale": scale,
            "b10": scale * (-math.log(0.9)) ** (1 / shape),
            "mean_life": scale * math.gamma(1 + 1 / shape)}


def pattern(result):
    """early, wear or random: named only when the whole likely range agrees."""
    if result["shape_high"] < 1:
        return "early"
    if result["shape_low"] > 1:
        return "wear"
    return "random"


PATTERN_TEXT = {
    "early": ("failures are most likely soon after installation or repair, so replacing "
              "on a schedule would add failures; installation and repair quality are "
              "the place to look",
              "الأعطال أرجح بعد التركيب أو الإصلاح مباشرة، فالاستبدال المجدول يزيدها؛ "
              "ويُنظر في جودة التركيب والإصلاح"),
    "wear": ("failures become more likely with age, so service or replacement on a "
             "schedule can prevent some of them",
             "الأعطال تزداد احتمالًا مع العمر، فالصيانة أو الاستبدال المجدول قد يمنع بعضها"),
    "random": ("this data cannot tell the pattern apart from failures at random, so it "
               "does not support replacing by age",
               "لا تميّز هذه البيانات النمط عن الأعطال العشوائية، فلا تدعم الاستبدال حسب العمر"),
}


class ReliabilityModel:
    """Time between failures per asset class, against the random pattern."""

    role = "reliability_model"
    title = "Reliability Agent — how do failures behave over time?"
    title_ar = "وكيل الموثوقية: كيف تتوزع الأعطال عبر الزمن؟"
    after = "sensitivity"
    question = "Do failures come early, at random, or with wear, and by when do 10% fail?"
    can_fail_run = False

    def _unavailable(self, en, ar):
        return {"status": "succeeded", "summary": en, "claims": [], "calculations": [],
                "quality_checks": [{"name": "field_contract", "passed": False, "detail": en}],
                "output": {"applicable": False, "reason": en, "reason_ar": ar,
                           "remaining_useful_life_estimated": False}}

    def run(self, ctx):
        rows = analytics._rows(ctx)
        columns = list(analytics._columns(ctx))
        asset = _column(columns, "Asset_ID")
        date = _column(columns, "Record_Date")
        count = _column(columns, "Failure_Count")
        if not (asset and date and count):
            return self._unavailable(
                "Reliability model unavailable: it needs Asset_ID, Record_Date and "
                "Failure_Count. No failure pattern was claimed.",
                "نموذج الموثوقية غير متاح: يحتاج Asset_ID وRecord_Date وFailure_Count. "
                "لم يُستنتج أي نمط للأعطال.")
        group_col = next((c for c in columns if c.strip().lower() == "asset_class"), None)
        records, skipped = {}, 0
        for row in rows:
            day, failures, unit = _day(row.get(date)), _failures(row.get(count)), row.get(asset)
            if day is None or failures is None or unit in (None, ""):
                skipped += 1
                continue
            group = str(row.get(group_col) or "").strip() if group_col else "all assets"
            records.setdefault(group or "unclassified", []).append((str(unit), day, failures))
        used = sum(len(v) for v in records.values())
        if not rows or used < MIN_DATED_SHARE * len(rows):
            return self._unavailable(
                "Reliability model unavailable: fewer than 90% of records carry a date to "
                "the day, an asset and a whole failure count. No failure pattern was claimed.",
                "نموذج الموثوقية غير متاح: أقل من 90% من السجلات فيها تاريخ باليوم وأصل "
                "وعدد أعطال صحيح. لم يُستنتج أي نمط للأعطال.")
        return self._fitted(ctx, records, skipped, group_col)

    def _fitted(self, ctx, records, skipped, group_col):
        p = self.role + "."
        calcs = [{"id": p + "c_skipped", "name": "records_without_date_asset_or_count",
                  "value": skipped,
                  "method": "count records without a day-level date, an asset or a whole "
                            "non-negative failure count"}]
        claims, groups, too_few = [], [], []
        prepared = []
        for name, items in records.items():
            failed, running, notes = intervals(items)
            prepared.append((len(failed), name, failed, running, notes))
        prepared.sort(key=lambda item: (-item[0], item[1]))
        no_interval = several = 0
        for index, (_, name, failed, running, notes) in enumerate(prepared):
            no_interval += notes["no_interval"]
            several += notes["several_on_one_record"]
            result = (fit(failed, running)
                      if len(failed) >= MIN_FAILURES and index < MAX_GROUPS else None)
            if result is None:
                too_few.append(name)
                continue
            i = len(groups)
            kind = pattern(result)
            values = {"group": name, "failures": len(failed), "running": len(running),
                      "shape": round(result["shape"], 2),
                      "shape_range": f"{result['shape_low']:.2f} to {result['shape_high']:.2f}",
                      "scale_days": round(result["scale"]),
                      "b10_days": round(result["b10"]),
                      "mean_life_days": round(result["mean_life"]),
                      "pattern": kind, "range_open": result["range_open"],
                      "as_of": notes["as_of"], "assets": notes["assets"]}
            groups.append(values)
            ids = [f"{p}c_group_{i}", f"{p}c_failures_{i}", f"{p}c_running_{i}",
                   f"{p}c_shape_{i}", f"{p}c_shape_range_{i}", f"{p}c_b10_{i}",
                   f"{p}c_mean_life_{i}"]
            calcs += [
                {"id": ids[0], "name": "asset_class", "value": name,
                 "method": f"records grouped by {group_col}" if group_col else "all records"},
                {"id": ids[1], "name": "failure_intervals", "value": len(failed),
                 "method": "days between records with a failure, per asset; the first "
                           "interval starts when the asset is first seen"},
                {"id": ids[2], "name": "running_intervals", "value": len(running),
                 "method": f"days from each asset's last failure, or first record, to "
                           f"{notes['as_of']}, counted as still running"},
                {"id": ids[3], "name": "failure_pattern_shape", "value": values["shape"],
                 "method": "Weibull shape by maximum likelihood, running times censored"},
                {"id": ids[4], "name": "failure_pattern_shape_range",
                 "value": values["shape_range"],
                 "method": "profile likelihood at 95% for one parameter"},
                {"id": ids[5], "name": "days_until_10pct_fail", "value": values["b10_days"],
                 "method": "Weibull B10 life: scale x (-ln 0.9)^(1/shape)"},
                {"id": ids[6], "name": "average_life_days", "value": values["mean_life_days"],
                 "method": "Weibull mean: scale x Gamma(1 + 1/shape)"},
            ]
            en, ar = PATTERN_TEXT[kind]
            low, high = values["shape_range"].split(" to ")
            claims.append(analytics._claim(
                ctx, f"{p}cl_pattern_{i}", "calculation",
                f"{name}: from {len(failed)} failure intervals and {len(running)} still "
                f"running, the failure pattern scores {values['shape']} (likely {low} to "
                f"{high}; below 1 is early-life, above 1 is wear): {en}. About 10% fail "
                f"within {values['b10_days']:,} days; the average life is "
                f"{values['mean_life_days']:,} days.",
                f"{name}: من {len(failed)} فترة بين أعطال و{len(running)} فترة ما زالت "
                f"قائمة، درجة نمط الأعطال {values['shape']} (المرجح {low} إلى {high}؛ أقل "
                f"من 1 أعطال مبكرة وأكثر من 1 تآكل): {ar}. يتعطل نحو 10% خلال "
                f"{values['b10_days']:,} يومًا، ومتوسط العمر {values['mean_life_days']:,} يومًا.",
                ids))
            if values["range_open"] or kind == "random":
                claims[-1]["status"] = "unverified"
        calcs += [
            {"id": p + "c_no_interval", "name": "failures_without_interval",
             "value": no_interval,
             "method": "failures on an asset's first record or on the same day as the "
                       "previous failure"},
            {"id": p + "c_several", "name": "records_with_several_failures",
             "value": several, "method": "records whose failure count is above one, "
                                         "each read as one failure"},
            {"id": p + "c_too_few", "name": "classes_not_fitted", "value": len(too_few),
             "method": f"asset classes with fewer than {MIN_FAILURES} failure intervals, "
                       f"or beyond the {MAX_GROUPS} with the most"},
        ]
        claims.append(analytics._claim(
            ctx, p + "cl_assumptions", "assumption",
            "Times are calendar days, not operating hours. Each repair is taken to return "
            "the asset to as good as new, a record with several failures counts as one, "
            "and assets still running at the latest date count as surviving to it. "
            f"{no_interval} failures gave no interval and {several} records held several "
            "failures. This is a pattern for the class, not one asset's remaining life.",
            "الأزمنة أيام تقويمية وليست ساعات تشغيل. يُفترض أن كل إصلاح يعيد الأصل كالجديد، "
            "ويُعد السجل الذي فيه عدة أعطال عطلًا واحدًا، وتُحسب الأصول التي ما زالت تعمل "
            f"في آخر تاريخ باقية حتى ذلك التاريخ. {no_interval} عطلًا لم يعطِ فترة، و{several} "
            "سجلًا فيه عدة أعطال. هذا نمط للفئة، لا العمر المتبقي لأصل بعينه.",
            [p + "c_no_interval", p + "c_several"]))
        if too_few:
            claims.append(analytics._claim(
                ctx, p + "cl_too_few", "limitation",
                f"{len(too_few)} asset classes were not fitted: fewer than {MIN_FAILURES} "
                f"failure intervals each, or beyond the {MAX_GROUPS} with the most. No "
                "pattern is claimed for them.",
                f"لم تُقدَّر {len(too_few)} فئة أصول: أقل من {MIN_FAILURES} فترات أعطال لكل "
                f"منها، أو بعد أكبر {MAX_GROUPS} فئات. لا يُستنتج لها أي نمط.",
                [p + "c_too_few"]))
        fitted = len(groups)
        summary = analytics._say(
            ctx, f"Fitted the failure pattern for {fitted} asset classes; "
                 f"{len(too_few)} had too few failures.",
            f"قُدّر نمط الأعطال لـ{fitted} من فئات الأصول؛ و{len(too_few)} أعطالها قليلة.")
        lines = ["## Reliability: failure pattern by asset class", "", summary, ""]
        for g in groups:
            lines.append(f"- {g['group']}: shape {g['shape']} (likely {g['shape_range']}), "
                         f"{g['pattern']}; 10% fail within {g['b10_days']:,} days; "
                         f"average life {g['mean_life_days']:,} days.")
        lines += ["", "A shape below 1 means early-life failures, about 1 random, above 1 "
                  "wear. The model reads calendar days and needs human review before any "
                  "maintenance interval changes."]
        return {"status": "succeeded", "summary": summary, "claims": claims,
                "calculations": calcs,
                "quality_checks": [
                    {"name": "field_contract", "passed": True,
                     "detail": "Asset_ID, Record_Date and Failure_Count available"},
                    {"name": "enough_failures", "passed": fitted > 0,
                     "detail": f"{fitted} classes with at least {MIN_FAILURES} failure intervals"}],
                "output": {"applicable": fitted > 0, "groups": groups,
                           "not_fitted": too_few, "skipped_records": skipped,
                           "time_unit": "calendar days",
                           "remaining_useful_life_estimated": False,
                           "human_approval_required": True,
                           "question": self.question,
                           "report_markdown": "\n".join(lines)}}
