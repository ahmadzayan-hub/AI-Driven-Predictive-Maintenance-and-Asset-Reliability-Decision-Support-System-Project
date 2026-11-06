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

Two stage options let the owner declare those numbers (owner slice R6,
2 November 2026): `horizon_days` (default 90) and `criticality_weights`, a
mapping from criticality label to a positive multiplier. Weights apply only
when they cover every criticality label in the data, and no asset lacks one;
otherwise nothing is weighted and the claim names what is missing.

A backtest asks whether the chances came true (6 November 2026 review,
Phase 4): the class fits are made again from records up to a cutoff one
horizon before the latest date, each asset still observed at the end is
given its chance from its age at the cutoff, and the chances are scored
against the failures that followed (Brier score, five calibration bands,
hits among the top ten) beside a constant-rate baseline fitted on the same
records. It is retrospective and one window wide: a check that the method
is not worse than a flat rate on this data, not a prospective validation,
which is the shadow ledger's job (server/reliability_validation.py).

Advisory only: a proposal for engineering review, never a work order.
Standard library only; the fit is the reliability model's own.
"""
import datetime
import math

from server import analytics
from server.maintenance import reliability as R

HORIZON_DAYS = 90
MAX_HORIZON_DAYS = 3650
MAX_WEIGHTS = 12
TOP = 10
CLAIMED = 3
MIN_BACKTEST_ASSETS = 20   # fewer assets scored than this: no backtest result
MIN_BACKTEST_FAILURES = 5  # fewer failures in the window than this: no result
DAYS_PER_MONTH = 365.25 / 12


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


def _ages_at(items, cutoff):
    """Days each asset had run at `cutoff` since its last failure or first record."""
    start = {}
    for asset, day, count in sorted(items, key=lambda item: item[1]):
        if day > cutoff:
            break
        if asset not in start or count > 0:
            start[asset] = day
    return {asset: (cutoff - day).days for asset, day in start.items()}


def backtest(records, horizon):
    """Score the ranking's chances on the window after a cutoff.

    `records` maps a class to (asset, date, failures) tuples. The cutoff is
    one horizon before the latest date. Only records up to the cutoff fit the
    class (Weibull, and a constant failure rate as the baseline); an asset is
    scored when it was seen by the cutoff and is either recorded failing in
    the window or recorded at its end. Returns a dict with "applicable".
    """
    days = [day for items in records.values() for _, day, _ in items]
    if not days:
        return {"applicable": False, "reason": "no_records"}
    as_of = max(days)
    cutoff = as_of - datetime.timedelta(days=horizon)
    if min(days) >= cutoff:
        return {"applicable": False, "reason": "history_shorter_than_horizon",
                "cutoff": cutoff.isoformat()}
    scored, unobserved, classes = [], 0, 0
    prepared = []
    for group, items in records.items():
        before = [item for item in items if item[1] <= cutoff]
        if before:
            prepared.append((R.intervals(before), group, items))
    prepared.sort(key=lambda item: (-len(item[0][0]), item[1]))
    for index, ((failed, running, _), group, items) in enumerate(prepared):
        if len(failed) < R.MIN_FAILURES or index >= R.MAX_GROUPS:
            continue
        result = R.fit(failed, running)
        if result is None:
            continue
        classes += 1
        exposure = sum(failed) + sum(running)
        base = 1 - math.exp(-len(failed) / exposure * horizon) if exposure else 0.0
        last, hit = {}, set()
        for asset, day, count in items:
            last[asset] = max(last.get(asset, day), day)
            if cutoff < day <= as_of and count > 0:
                hit.add(asset)
        for asset, age in _ages_at(items, cutoff).items():
            if asset not in hit and last[asset] < as_of:
                unobserved += 1
                continue
            scored.append((chance_within(age, horizon, result["shape"], result["scale"]),
                           base, asset in hit, asset))
    failures = sum(1 for item in scored if item[2])
    out = {"cutoff": cutoff.isoformat(), "window_end": as_of.isoformat(),
           "horizon_days": horizon, "classes": classes, "assets_scored": len(scored),
           "assets_unobserved": unobserved, "failures": failures}
    if len(scored) < MIN_BACKTEST_ASSETS or failures < MIN_BACKTEST_FAILURES:
        out.update(applicable=False, reason="too_few_assets_or_failures")
        return out
    n = len(scored)
    brier = sum((c - f) ** 2 for c, _, f, _ in scored) / n
    brier_base = sum((b - f) ** 2 for _, b, f, _ in scored) / n
    bands = []
    for low, high in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.0001)):
        cohort = [item for item in scored if low <= item[0] < high]
        bands.append({"lower": low, "upper": min(high, 1), "assets": len(cohort),
                      "mean_chance": (round(sum(i[0] for i in cohort) / len(cohort), 3)
                                      if cohort else None),
                      "observed_rate": (round(sum(i[2] for i in cohort) / len(cohort), 3)
                                        if cohort else None)})
    top = sorted(scored, key=lambda item: (-item[0], item[3]))[:TOP]
    hits = sum(1 for item in top if item[2])
    out.update(applicable=True, brier=round(brier, 3), brier_baseline=round(brier_base, 3),
               better_than_baseline=brier < brier_base,
               expected_failures=round(sum(item[0] for item in scored), 1),
               calibration=bands, top=len(top), top_hits=hits,
               top_hits_at_base_rate=round(len(top) * failures / n, 1),
               false_alerts_per_asset_month=round(
                   (len(top) - hits) / (len(top) * horizon / DAYS_PER_MONTH), 3))
    return out


def _positive(value, upper=None):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value > 0 and (upper is None or value <= upper))


def _g(value):
    return f"{value:g}"


class RiskRanking:
    """Assets ranked by expected failure cost over the next 90 days (or a declared horizon)."""

    role = "risk_ranking"
    title = "Risk Ranking Agent — which assets first?"
    title_ar = "وكيل ترتيب المخاطر: بأي الأصول نبدأ؟"
    after = "sensitivity"
    question = "Which assets carry the highest expected failure cost in the next 90 days?"
    can_fail_run = False

    def __init__(self, horizon_days=None, criticality_weights=None):
        if horizon_days is not None and not (_positive(horizon_days, MAX_HORIZON_DAYS)
                                             and float(horizon_days).is_integer()):
            raise ValueError(f"horizon_days must be a whole number of days, 1 to {MAX_HORIZON_DAYS}")
        weights = dict(criticality_weights or {})
        if len(weights) > MAX_WEIGHTS or not all(
                isinstance(k, str) and k.strip() and _positive(v) for k, v in weights.items()):
            raise ValueError(f"criticality_weights must map up to {MAX_WEIGHTS} labels "
                             "to positive numbers")
        keys = [k.strip().lower() for k in weights]
        if len(set(keys)) != len(keys):
            raise ValueError("criticality_weights repeats a label")
        self.horizon = int(horizon_days) if horizon_days is not None else HORIZON_DAYS
        self.declared_horizon = horizon_days is not None
        self.weights = {k.strip(): float(v) for k, v in weights.items()}

    def _weighting(self, ranked):
        """The weight per asset, or the reason weights cannot apply."""
        if not self.weights:
            return None, None
        lookup = {k.lower(): v for k, v in self.weights.items()}
        unrecorded = sum(1 for item in ranked if not item["criticality"])
        missing = sorted({item["criticality"] for item in ranked
                          if item["criticality"] and item["criticality"].lower() not in lookup})
        if unrecorded or missing:
            return None, {"missing_labels": missing, "unrecorded_assets": unrecorded}
        return {item["asset"]: lookup[item["criticality"].lower()] for item in ranked}, None

    def _unavailable(self, en, ar):
        return {"status": "succeeded", "summary": en, "claims": [], "calculations": [],
                "quality_checks": [{"name": "field_contract", "passed": False, "detail": en}],
                "output": {"applicable": False, "reason": en, "reason_ar": ar,
                           "ranked": [], "human_approval_required": True}}

    def _backtest_claim(self, ctx, calcs, checked):
        """One claim stating how the chances did on the window after the cutoff."""
        p = self.role + "."
        if not checked["applicable"]:
            calcs.append({"id": p + "c_backtest", "name": "backtest", "value": "not run",
                          "method": "needs history longer than the horizon, at least "
                                    f"{MIN_BACKTEST_ASSETS} assets scored and "
                                    f"{MIN_BACKTEST_FAILURES} failures in the window"})
            return analytics._claim(
                ctx, p + "cl_backtest", "limitation",
                "The chances above are not backtested: the history is too short, or too few "
                "assets or failures fall in a window one horizon long, to check them against "
                "what happened.",
                "الاحتمالات أعلاه غير مختبرة على الماضي: السجل أقصر من اللازم، أو الأصول أو "
                "الأعطال في نافذة بطول الأفق قليلة، فلا يمكن مقارنتها بما حدث.",
                [p + "c_backtest"])
        c = checked
        calcs += [
            {"id": p + "c_bt_window", "name": "backtest_window",
             "value": f"{c['cutoff']} to {c['window_end']}",
             "method": "cutoff one horizon before the latest record; classes refitted "
                       "on records up to the cutoff only"},
            {"id": p + "c_bt_scored", "name": "backtest_assets_scored", "value": c["assets_scored"],
             "method": "assets seen by the cutoff and recorded failing in the window or "
                       "at its end; " + f"{c['assets_unobserved']} not observed to the end left out"},
            {"id": p + "c_bt_failures", "name": "backtest_failures", "value": c["failures"],
             "method": "scored assets with a failure recorded in the window"},
            {"id": p + "c_bt_brier", "name": "backtest_brier", "value": f"{c['brier']:.3f}",
             "method": "mean squared gap between each asset's chance and 1 or 0"},
            {"id": p + "c_bt_brier_base", "name": "backtest_brier_baseline",
             "value": f"{c['brier_baseline']:.3f}",
             "method": "the same score for a constant failure rate per class, fitted on the "
                       "same records (no ageing)"},
            {"id": p + "c_bt_top", "name": "backtest_top_hits",
             "value": f"{c['top_hits']} of {c['top']}",
             "method": f"failures among the {c['top']} highest chances at the cutoff; "
                       f"{c['top_hits_at_base_rate']} expected at the window's failure rate; "
                       f"{c['false_alerts_per_asset_month']} false alerts per asset-month"},
        ]
        better = c["better_than_baseline"]
        en = (f"Backtest, {c['cutoff']} to {c['window_end']}: {c['failures']} of "
              f"{c['assets_scored']} assets failed in the window. The chances scored "
              f"{c['brier']:.3f} (Brier, lower is better) against {c['brier_baseline']:.3f} "
              f"for a constant rate, so they did "
              + ("better than" if better else "no better than")
              + f" a flat rate here; {c['top_hits']} of the top {c['top']} failed. "
              "One past window, not a prospective validation.")
        ar = (f"اختبار على الماضي، من {c['cutoff']} إلى {c['window_end']}: تعطّل "
              f"{c['failures']} من {c['assets_scored']} أصلًا في النافذة. سجّلت الاحتمالات "
              f"{c['brier']:.3f} (مقياس براير، الأقل أفضل) مقابل {c['brier_baseline']:.3f} "
              "لمعدل ثابت، فكانت "
              + ("أفضل من" if better else "ليست أفضل من")
              + f" المعدل الثابت هنا؛ وتعطّل {c['top_hits']} من أعلى {c['top']}. "
              "نافذة واحدة من الماضي، لا تحقق مستقبلي.")
        claim = analytics._claim(
            ctx, p + "cl_backtest", "calculation" if better else "limitation", en, ar,
            [p + "c_bt_window", p + "c_bt_scored", p + "c_bt_failures", p + "c_bt_brier",
             p + "c_bt_brier_base", p + "c_bt_top"], labels=(c["cutoff"], c["window_end"]))
        return claim

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
                chance = chance_within(age, self.horizon, result["shape"], result["scale"])
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
        weight_of, unweighted = self._weighting(ranked)
        for item in ranked:
            base = item["expected_cost"] if by_cost else item["chance"]
            item["weight"] = weight_of[item["asset"]] if weight_of else None
            item["score"] = base * item["weight"] if weight_of else base
        ranked.sort(key=lambda item: (-item["score"], -item["chance"], item["asset"]))
        return self._result(ctx, ranked, not_fitted, by_cost, bool(cost_cols),
                            bool(weight_of), unweighted, backtest(records, self.horizon))

    def _result(self, ctx, ranked, not_fitted, by_cost, has_cost_columns,
                weighted=False, unweighted=None, checked=None):
        p = self.role + "."
        h = self.horizon
        top = ranked[:TOP]
        calcs = [
            {"id": p + "c_assets", "name": "assets_ranked", "value": len(ranked),
             "method": "assets in asset classes the reliability model fitted"},
            {"id": p + "c_not_fitted", "name": "assets_not_ranked", "value": not_fitted,
             "method": "assets in classes with too few failures for a fit"},
            {"id": p + "c_horizon", "name": "horizon_days", "value": h,
             "method": "planning horizon declared by the owner (stage option horizon_days)"
                       if self.declared_horizon else "default planning horizon"},
        ]
        if self.weights:
            calcs.append({"id": p + "c_weights", "name": "criticality_weights",
                          "value": ", ".join(f"{k} x{_g(v)}" for k, v in self.weights.items()),
                          "method": "declared by the owner (stage option criticality_weights); "
                                    + ("applied as a multiplier on the ranking value"
                                       if weighted else "not applied, see the basis claim")})
        claims = []
        for i, item in enumerate(top):
            pct = round(item["chance"] * 100)
            cost = (f", expected cost {item['expected_cost']:,} USD"
                    if item["expected_cost"] is not None else "")
            calcs.append({
                "id": f"{p}c_rank_{i}", "name": f"rank_{i + 1}",
                "value": f"{item['asset']} ({item['group']}): {pct}% within "
                         f"{h} days after {item['days_running']:,} days running{cost}; "
                         f"longest failure interval seen in the class {item['longest_seen']:,} days",
                "method": (f"1 - R(t + {h}) / R(t) from the class's Weibull fit, times the "
                           "class's average cost per failure (maintenance plus production "
                           "loss on records with a failure)" if by_cost else
                           f"1 - R(t + {h}) / R(t) from the class's Weibull fit")
                          + (f"; ranked after weighting by criticality x{_g(item['weight'])}"
                             if weighted else "")})
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
                f"about {pct}% chance of failing within {h} days{en_cost}."
                + (f" That is longer than any failure interval seen in the class "
                   f"({item['longest_seen']:,} days), so the figure is an extrapolation."
                   if item["beyond_data"] else ""),
                f"يُقترح مراجعة {item['asset']} ({item['group']}، الأهمية {label_ar}) "
                f"لعمل مخطط: بعد {item['days_running']:,} يومًا من التشغيل، احتمال تعطله "
                f"خلال {h} يومًا نحو {pct}%{ar_cost}."
                + (f" وهذه مدة أطول من أي فترة بين أعطال في الفئة ({item['longest_seen']:,} "
                   f"يومًا)، فالرقم استقراء خارج البيانات."
                   if item["beyond_data"] else ""),
                [f"{p}c_rank_{i}", p + "c_horizon"] + ([p + "c_weights"] if weighted else []))
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
        if weighted:
            weight_en = ("Criticality weights declared by the owner multiply the ranking "
                         "value: " + ", ".join(f"{k} x{_g(v)}" for k, v in self.weights.items())
                         + ".")
            weight_ar = ("أوزان الأهمية التي حددها المالك تضرب قيمة الترتيب: "
                         + "، ".join(f"{k} x{_g(v)}" for k, v in self.weights.items()) + ".")
        elif unweighted:
            gaps_en = ([f"no weight is declared for {', '.join(unweighted['missing_labels'])}"]
                       if unweighted["missing_labels"] else []) + \
                      ([f"{unweighted['unrecorded_assets']} assets have no criticality recorded"]
                       if unweighted["unrecorded_assets"] else [])
            gaps_ar = ([f"لا وزن محددًا لـ {'، '.join(unweighted['missing_labels'])}"]
                       if unweighted["missing_labels"] else []) + \
                      ([f"{unweighted['unrecorded_assets']} أصلًا بلا أهمية مسجلة"]
                       if unweighted["unrecorded_assets"] else [])
            weight_en = ("Criticality is shown, not weighted: the declared weights were not "
                         "applied because " + " and ".join(gaps_en) + ".")
            weight_ar = ("تُعرض الأهمية دون ترجيح: لم تُطبَّق الأوزان المحددة لأن "
                         + " و".join(gaps_ar) + ".")
        else:
            weight_en, weight_ar = "Criticality is shown, not weighted.", "تُعرض الأهمية دون ترجيح."
        claims.append(analytics._claim(
            ctx, p + "cl_basis", "assumption",
            f"{len(ranked)} assets are ranked by {basis_en}. The chance comes from the "
            f"class's failure pattern and the days since each asset's last failure, so it "
            f"carries the reliability model's assumptions. {weight_en} {not_fitted} assets in classes with too few failures are not ranked. "
            f"This is a proposal for engineering review, not a work order.",
            f"رُتِّب {len(ranked)} أصلًا حسب {basis_ar}. يأتي الاحتمال من نمط أعطال الفئة "
            f"والأيام منذ آخر عطل لكل أصل، فيحمل افتراضات نموذج الموثوقية. {weight_ar} "
            f"لم يُرتَّب {not_fitted} أصلًا في فئات أعطالها قليلة. هذا مقترح "
            f"للمراجعة الهندسية، لا أمر عمل.",
            [p + "c_assets", p + "c_not_fitted"] + ([p + "c_weights"] if self.weights else [])))
        checked = checked or {"applicable": False, "reason": "not_run"}
        claims.append(self._backtest_claim(ctx, calcs, checked))
        lines = [f"## Risk ranking: next {h} days", "",
                 f"Ranked {len(ranked)} assets by "
                 + ("expected failure cost." if by_cost else "chance of failure."), "",
                 "| Rank | Asset | Class | Criticality | Days running | Chance | Expected cost (USD) |",
                 "| --- | --- | --- | --- | --- | --- | --- |"]
        for i, item in enumerate(top, start=1):
            cost = f"{item['expected_cost']:,}" if item["expected_cost"] is not None else "n/a"
            lines.append(f"| {i} | {item['asset']} | {item['group']} | "
                         f"{item['criticality'] or 'n/a'} | {item['days_running']:,} | "
                         f"{round(item['chance'] * 100)}% | {cost} |")
        if checked["applicable"]:
            lines += ["", f"Backtest from {checked['cutoff']} to {checked['window_end']}: "
                      f"{checked['failures']} of {checked['assets_scored']} assets failed; "
                      f"Brier score {checked['brier']:.3f} against {checked['brier_baseline']:.3f} "
                      f"for a constant rate; {checked['top_hits']} of the top {checked['top']} failed."]
        lines += ["", "A proposal for engineering review; it issues no work order."]
        summary = analytics._say(
            ctx, f"Ranked {len(ranked)} assets by "
                 + ("expected failure cost" if by_cost else "chance of failure")
                 + f" over {h} days.",
            f"رُتِّب {len(ranked)} أصلًا حسب "
            + ("التكلفة المتوقعة للأعطال" if by_cost else "احتمال العطل")
            + f" خلال {h} يومًا.")
        return {"status": "succeeded", "summary": summary, "claims": claims,
                "calculations": calcs,
                "quality_checks": [
                    {"name": "field_contract", "passed": True,
                     "detail": "Asset_ID, Record_Date and Failure_Count available"},
                    {"name": "cost_basis", "passed": by_cost,
                     "detail": "ranked by expected cost" if by_cost else "ranked by chance only"}],
                "output": {"applicable": True, "horizon_days": h,
                           "ranked_by": "expected_cost" if by_cost else "chance",
                           "ranked": top, "assets_ranked": len(ranked),
                           "assets_not_ranked": not_fitted,
                           "criticality_weighted": weighted,
                           "criticality_weights": self.weights or None,
                           "weights_not_applied": unweighted,
                           "human_approval_required": True,
                           "work_orders_issued": False,
                           "backtest": checked,
                           "question": self.question,
                           "report_markdown": "\n".join(lines)}}
