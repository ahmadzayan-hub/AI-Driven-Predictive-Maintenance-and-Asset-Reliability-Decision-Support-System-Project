"""Risk ranking: which assets to look at first (owner slice R2, 31 October 2026).

For every asset in a class the reliability model can fit, the chance that it
fails within the next 90 days is read from its class's Weibull pattern, given
how long it has already run since its last failure:
P = 1 - R(t + h) / R(t), with R(t) = exp(-(t / scale) ^ shape).

That chance is multiplied by the class's observed cost per failure
(maintenance cost plus recorded production loss, on records with a failure)
to give an expected cost over the horizon. Assets are ranked by that
expected cost, or by the chance alone when no cost is recorded. Criticality
is shown beside each asset, never turned into an invented weight: how much
a consequence class is worth is the owner's call.

Advisory only: a proposal for engineering review, never a work order.
Standard library only; the fit is the reliability model's own.
"""
import math

from server import analytics
from server.maintenance import reliability as R

HORIZON_DAYS = 90
TOP = 10
CLAIMED = 3


def _money(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def chance_within(age, horizon, shape, scale):
    """Chance of failing within `horizon` days after surviving `age` days."""
    def cumulative_hazard(t):
        return (t / scale) ** shape
    return 1 - math.exp(cumulative_hazard(age) - cumulative_hazard(age + horizon))


def ages(items):
    """Days each asset has run since its last failure (or since first seen)."""
    as_of = max(day for _, day, _ in items)
    start = {}
    for asset, day, count in sorted(items, key=lambda item: item[1]):
        if asset not in start or count > 0:
            start[asset] = day
    return {asset: (as_of - day).days for asset, day in start.items()}


class RiskRanking:
    """Assets ranked by expected failure cost over the next 90 days."""

    role = "risk_ranking"
    title = "Risk Ranking Agent — which assets first?"
    title_ar = "وكيل ترتيب المخاطر: بأي الأصول نبدأ؟"
    after = "sensitivity"
    question = "Which assets carry the highest expected failure cost in the next 90 days?"
    can_fail_run = False

    def _unavailable(self, en, ar):
        return {"status": "succeeded", "summary": en, "claims": [], "calculations": [],
                "quality_checks": [{"name": "field_contract", "passed": False, "detail": en}],
                "output": {"applicable": False, "reason": en, "reason_ar": ar,
                           "ranked": [], "human_approval_required": True}}

    def run(self, ctx):
        rows = analytics._rows(ctx)
        columns = list(analytics._columns(ctx))
        asset = R._column(columns, "Asset_ID")
        date = R._column(columns, "Record_Date")
        count = R._column(columns, "Failure_Count")
        if not (asset and date and count):
            return self._unavailable(
                "Risk ranking unavailable: it needs Asset_ID, Record_Date and "
                "Failure_Count. No asset was ranked.",
                "ترتيب المخاطر غير متاح: يحتاج Asset_ID وRecord_Date وFailure_Count. "
                "لم يُرتَّب أي أصل.")
        group_col = next((c for c in columns if c.strip().lower() == "asset_class"), None)
        critical_col = R._column(columns, "Criticality")
        cost_cols = [c for c in (R._column(columns, "Maintenance_Cost_USD"),
                                 R._column(columns, "Production_Loss_USD")) if c]
        records, critical, spend = {}, {}, {}
        for row in rows:
            day, failures, unit = R._day(row.get(date)), R._failures(row.get(count)), row.get(asset)
            if day is None or failures is None or unit in (None, ""):
                continue
            group = (str(row.get(group_col) or "").strip() or "unclassified") \
                if group_col else "all assets"
            records.setdefault(group, []).append((str(unit), day, failures))
            if critical_col and row.get(critical_col) not in (None, ""):
                critical[str(unit)] = str(row[critical_col]).strip()
            if failures > 0 and cost_cols:
                amounts = [_money(row.get(c)) for c in cost_cols]
                if all(a is not None for a in amounts):
                    total, n = spend.get(group, (0.0, 0))
                    spend[group] = (total + sum(amounts), n + 1)
        ranked, not_fitted = [], 0
        # The same classes the reliability model fits: the most failures first.
        prepared = sorted(((R.intervals(items), group, items) for group, items in records.items()),
                          key=lambda item: (-len(item[0][0]), item[1]))
        for index, ((failed, running, _), group, items) in enumerate(prepared):
            result = (R.fit(failed, running)
                      if len(failed) >= R.MIN_FAILURES and index < R.MAX_GROUPS else None)
            if result is None:
                not_fitted += len({a for a, _, _ in items})
                continue
            total, n = spend.get(group, (0.0, 0))
            per_failure = total / n if n else None
            for unit, age in ages(items).items():
                chance = chance_within(age, HORIZON_DAYS, result["shape"], result["scale"])
                ranked.append({"asset": unit, "group": group,
                               "criticality": critical.get(unit),
                               "days_running": age, "chance": round(chance, 3),
                               "expected_cost": (round(chance * per_failure)
                                                 if per_failure is not None else None),
                               "cost_per_failure": (round(per_failure)
                                                    if per_failure is not None else None),
                               "range_open": result["range_open"],
                               "longest_seen": max(failed),
                               "beyond_data": age > max(failed)})
        if not ranked:
            return self._unavailable(
                "Risk ranking unavailable: no asset class has enough failures for the "
                "reliability model. No asset was ranked.",
                "ترتيب المخاطر غير متاح: لا توجد فئة أصول فيها أعطال كافية لنموذج "
                "الموثوقية. لم يُرتَّب أي أصل.")
        by_cost = all(item["expected_cost"] is not None for item in ranked)
        ranked.sort(key=lambda item: (-(item["expected_cost"] if by_cost else item["chance"]),
                                      -item["chance"], item["asset"]))
        return self._result(ctx, ranked, not_fitted, by_cost, bool(cost_cols))

    def _result(self, ctx, ranked, not_fitted, by_cost, has_cost_columns):
        p = self.role + "."
        top = ranked[:TOP]
        calcs = [
            {"id": p + "c_assets", "name": "assets_ranked", "value": len(ranked),
             "method": "assets in asset classes the reliability model fitted"},
            {"id": p + "c_not_fitted", "name": "assets_not_ranked", "value": not_fitted,
             "method": "assets in classes with too few failures for a fit"},
            {"id": p + "c_horizon", "name": "horizon_days", "value": HORIZON_DAYS,
             "method": "fixed planning horizon"},
        ]
        claims = []
        for i, item in enumerate(top):
            pct = round(item["chance"] * 100)
            cost = (f", expected cost {item['expected_cost']:,} USD"
                    if item["expected_cost"] is not None else "")
            calcs.append({
                "id": f"{p}c_rank_{i}", "name": f"rank_{i + 1}",
                "value": f"{item['asset']} ({item['group']}): {pct}% within "
                         f"{HORIZON_DAYS} days after {item['days_running']:,} days running{cost}; "
                         f"longest failure interval seen in the class {item['longest_seen']:,} days",
                "method": "1 - R(t + 90) / R(t) from the class's Weibull fit, times the "
                          "class's average cost per failure (maintenance plus production "
                          "loss on records with a failure)" if by_cost else
                          "1 - R(t + 90) / R(t) from the class's Weibull fit"})
        for i, item in enumerate(top[:CLAIMED]):
            pct = round(item["chance"] * 100)
            label = item["criticality"] or "not recorded"
            label_ar = item["criticality"] or "غير مسجلة"
            en_cost = (f", an expected cost of {item['expected_cost']:,} USD"
                       if item["expected_cost"] is not None else "")
            ar_cost = (f"، بتكلفة متوقعة {item['expected_cost']:,} دولار"
                       if item["expected_cost"] is not None else "")
            claim = analytics._claim(
                ctx, f"{p}cl_rank_{i}", "recommendation",
                f"Review {item['asset']} ({item['group']}, criticality {label}) "
                f"for planned work: after {item['days_running']:,} days running it has "
                f"about {pct}% chance of failing within {HORIZON_DAYS} days{en_cost}."
                + (f" That is longer than any failure interval seen in the class "
                   f"({item['longest_seen']:,} days), so the figure is an extrapolation."
                   if item["beyond_data"] else ""),
                f"يُقترح مراجعة {item['asset']} ({item['group']}، الأهمية {label_ar}) "
                f"لعمل مخطط: بعد {item['days_running']:,} يومًا من التشغيل، احتمال تعطله "
                f"خلال {HORIZON_DAYS} يومًا نحو {pct}%{ar_cost}."
                + (f" وهذه مدة أطول من أي فترة بين أعطال في الفئة ({item['longest_seen']:,} "
                   f"يومًا)، فالرقم استقراء خارج البيانات."
                   if item["beyond_data"] else ""),
                [f"{p}c_rank_{i}", p + "c_horizon"])
            if item["range_open"] or item["beyond_data"]:
                claim["status"] = "unverified"
            claims.append(claim)
        basis_en = ("expected cost: the chance times the class's average recorded cost per "
                    "failure, where production loss is the source's own valuation"
                    if by_cost else
                    "chance alone, because " + ("some classes have no complete cost on "
                                                "failure records" if has_cost_columns
                                                else "no cost columns are recorded"))
        basis_ar = ("التكلفة المتوقعة: الاحتمال مضروبًا في متوسط التكلفة المسجلة لكل عطل في "
                    "الفئة، وخسارة الإنتاج تقدير المصدر نفسه"
                    if by_cost else
                    "الاحتمال وحده، لأن " + ("بعض الفئات بلا تكلفة كاملة في سجلات الأعطال"
                                             if has_cost_columns else "البيانات بلا أعمدة تكلفة"))
        claims.append(analytics._claim(
            ctx, p + "cl_basis", "assumption",
            f"{len(ranked)} assets are ranked by {basis_en}. The chance comes from the "
            f"class's failure pattern and the days since each asset's last failure, so it "
            f"carries the reliability model's assumptions. Criticality is shown, not "
            f"weighted. {not_fitted} assets in classes with too few failures are not ranked. "
            f"This is a proposal for engineering review, not a work order.",
            f"رُتِّب {len(ranked)} أصلًا حسب {basis_ar}. يأتي الاحتمال من نمط أعطال الفئة "
            f"والأيام منذ آخر عطل لكل أصل، فيحمل افتراضات نموذج الموثوقية. تُعرض الأهمية "
            f"دون ترجيح. لم يُرتَّب {not_fitted} أصلًا في فئات أعطالها قليلة. هذا مقترح "
            f"للمراجعة الهندسية، لا أمر عمل.",
            [p + "c_assets", p + "c_not_fitted"]))
        lines = [f"## Risk ranking: next {HORIZON_DAYS} days", "",
                 f"Ranked {len(ranked)} assets by "
                 + ("expected failure cost." if by_cost else "chance of failure."), "",
                 "| Rank | Asset | Class | Criticality | Days running | Chance | Expected cost (USD) |",
                 "| --- | --- | --- | --- | --- | --- | --- |"]
        for i, item in enumerate(top, start=1):
            cost = f"{item['expected_cost']:,}" if item["expected_cost"] is not None else "n/a"
            lines.append(f"| {i} | {item['asset']} | {item['group']} | "
                         f"{item['criticality'] or 'n/a'} | {item['days_running']:,} | "
                         f"{round(item['chance'] * 100)}% | {cost} |")
        lines += ["", "A proposal for engineering review; it issues no work order."]
        summary = (f"Ranked {len(ranked)} assets by "
                   + ("expected failure cost" if by_cost else "chance of failure")
                   + f" over {HORIZON_DAYS} days.")
        return {"status": "succeeded", "summary": summary, "claims": claims,
                "calculations": calcs,
                "quality_checks": [
                    {"name": "field_contract", "passed": True,
                     "detail": "Asset_ID, Record_Date and Failure_Count available"},
                    {"name": "cost_basis", "passed": by_cost,
                     "detail": "ranked by expected cost" if by_cost else "ranked by chance only"}],
                "output": {"applicable": True, "horizon_days": HORIZON_DAYS,
                           "ranked_by": "expected_cost" if by_cost else "chance",
                           "ranked": top, "assets_ranked": len(ranked),
                           "assets_not_ranked": not_fitted,
                           "criticality_weighted": False,
                           "human_approval_required": True,
                           "work_orders_issued": False,
                           "question": self.question,
                           "report_markdown": "\n".join(lines)}}
