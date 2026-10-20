"""Validated maintenance risk models (milestone S3).

ADR 0033 ships four general model stages and states their own limit
plainly: "A model cannot know which columns were recorded after the
outcome, so every model says so." The maintenance contract now does know
(`contract.model_inputs`), so this stage closes that gap for this domain
rather than restating the caveat.

Four things separate it from a generic classifier.

**The target is a decision, not a column.** Each `Target` names the
question, the population it is answered on, the operational decision it
supports and the horizon. A model whose target nobody can act on is a
number, not evidence.

**Inputs are curated by timing.** Only columns knowable before the
decision are offered. On a typical maintenance export that removes most
of the table, and the stage reports how many and why - because a model
scoring beautifully on outcome columns is the failure this product
exists to catch.

**The baseline is informative, not flattering.** Beating "always guess
the common class" proves little when one class is 80% of the data. The
baseline here is the *strongest* of the majority class and the best
single known-before grouping rule, so the model has to earn its place
against the obvious thing a person would do without it.

**A weak model is reported as weak.** The 5% margin is ADR 0033's and is
not re-opened here; choosing a threshold after seeing a holdout result is
how an honest evaluation becomes a flattering one.
"""

import statistics
from collections import Counter, defaultdict

from .. import analytics, modelling
from . import contract

# Fewest labelled records, per side of the split, before a target is
# worth fitting at all. The held-out floor is not cosmetic: balanced
# accuracy on a few dozen records swings by several points on noise
# alone, so a small holdout can read as signal where there is none. A
# signal-free fixture scored 0.62 on ~80 held-out rows while this was 10.
MIN_TRAIN, MIN_TEST = modelling.MIN_ROWS, 50
# Known-before categorical columns considered as baseline rules.
MAX_BASELINE_RULES = 8
# A grouping rule needs groups, not near-unique values: grouping by a date
# or an identifier memorises the training set instead of describing it.
MAX_BASELINE_GROUPS = 12
# Balanced accuracy of a coin flip, and of always guessing one class -
# which is 0.5 *by construction*, since one class scores 1.0 and the
# other 0.0. That makes a majority-class baseline degenerate under this
# metric, so a relative margin over it means little on its own and the
# verdict carries an absolute floor as well. This is a property of the
# metric, not a threshold chosen after seeing a result.
CHANCE = 0.5
CHANCE_MARGIN = 0.05


def _corrective(row):
    return str(row.get("Work_Order_Type", "")).strip().lower() == "corrective"


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class Target:
    """One decision a model could support, stated before anything is fitted."""

    def __init__(self, key, question, question_ar, decision, decision_ar,
                 population, label, needs, horizon, defines_label=()):
        self.key = key
        self.question = question
        self.question_ar = question_ar
        self.decision = decision
        self.decision_ar = decision_ar
        self.population = population
        self.label = label
        # Columns without which the target cannot be formed at all.
        self.needs = tuple(needs)
        self.horizon = horizon
        # Columns the label is computed from. One of these surviving as
        # an input is legitimate when it was knowable before the work,
        # but the reader must be told the model partly reconstructs the
        # comparison that defines the target.
        self.defines_label = tuple(defines_label)

    def labelled(self, rows):
        """(row, label) for rows in the population that can be labelled."""
        out = []
        for row in rows:
            if not self.population(row):
                continue
            label = self.label(row)
            if label is not None:
                out.append((row, label))
        return out


def _repeat_failure(row):
    count = _num(row.get("Failure_Count"))
    return None if count is None else count > 1


def _sla_breach(row):
    target, actual = _num(row.get("SLA_Target_Hours")), _num(row.get("SLA_Actual_Hours"))
    if target is None or actual is None:
        return None
    return actual > target


TARGETS = (
    Target(
        "repeat_failure",
        "Will this corrective job involve more than one failure?",
        "هل يتضمن أمر العمل التصحيحي أكثر من عطل واحد؟",
        "Send a senior technician and pre-stage parts for the jobs most likely "
        "to turn into several failures.",
        "إرسال فني أول وتجهيز قطع الغيار مسبقاً للأعمال الأكثر احتمالاً أن تتحول "
        "إلى أعطال متعددة.",
        _corrective, _repeat_failure,
        needs=("Failure_Count", "Work_Order_Type"),
        horizon="the same maintenance record",
        defines_label=("Failure_Count",)),
    Target(
        "sla_breach",
        "Will this job miss its response target?",
        "هل سيتجاوز هذا العمل زمن الاستجابة المستهدف؟",
        "Escalate the jobs most likely to miss their target before the clock "
        "starts, rather than after it has run out.",
        "تصعيد الأعمال الأكثر احتمالاً لتجاوز المستهدف قبل بدء المهلة لا بعد انتهائها.",
        lambda row: True, _sla_breach,
        needs=("SLA_Target_Hours", "SLA_Actual_Hours"),
        horizon="the same maintenance record",
        defines_label=("SLA_Target_Hours", "SLA_Actual_Hours")),
)


def _balanced_accuracy(truth, predicted):
    """Average of each class's hit rate, so a common class cannot carry it."""
    per_class = defaultdict(lambda: [0, 0])
    for actual, guess in zip(truth, predicted):
        per_class[actual][1] += 1
        if actual == guess:
            per_class[actual][0] += 1
    rates = [hits / total for hits, total in per_class.values() if total]
    return statistics.fmean(rates) if rates else 0.0


def _grouping_rules(train_rows, train_labels, test_rows, test_labels, candidates):
    """The best "guess the commonest label in this group" rule, and its score.

    This is the informative baseline: the obvious thing a person would do
    with a table and no model. A model that cannot beat it has not earned
    the complexity it costs.
    """
    best = (None, 0.0)
    for column in candidates[:MAX_BASELINE_RULES]:
        by_group = defaultdict(Counter)
        for row, label in zip(train_rows, train_labels):
            by_group[str(row.get(column))][label] += 1
        if not 2 <= len(by_group) <= MAX_BASELINE_GROUPS:
            continue
        overall = Counter(train_labels).most_common(1)[0][0]
        guesses = [by_group[str(r.get(column))].most_common(1)[0][0]
                   if by_group.get(str(r.get(column))) else overall
                   for r in test_rows]
        score = _balanced_accuracy(test_labels, guesses)
        if score > best[1]:
            best = (column, score)
    return best


class MaintenanceRisk:
    """Decision-linked risk models, each against an informative baseline."""

    role = "maintenance_risk"
    title = "Maintenance Risk Agent — which jobs need intervention?"
    title_ar = "وكيل مخاطر الصيانة: أي الأعمال تحتاج تدخلاً؟"
    after = "sensitivity"
    question = "Which jobs are most likely to go wrong, and can we predict it?"
    can_fail_run = False

    def __init__(self, targets=None):
        self.targets = tuple(targets) if targets else TARGETS

    def run(self, ctx):
        rows = analytics._rows(ctx)
        columns = analytics._columns(ctx)
        date = (ctx.get("preparer") or {}).get("date_col") \
            or (ctx.get("cleaner") or {}).get("date_col")
        usable, excluded = contract.model_inputs(columns)

        calculations = [
            modelling._calc(self.role, "c_inputs_usable", "model_inputs_usable",
                            len(usable),
                            "columns knowable before the decision, from the "
                            "maintenance contract's timing field"),
            modelling._calc(self.role, "c_inputs_excluded", "model_inputs_excluded",
                            len(excluded),
                            "columns excluded as outcomes, derived from outcomes, "
                            "identifiers, or of unestablished timing"),
        ]
        claims = [modelling._claim(
            ctx, self.role, "cl_inputs", "assumption",
            f"Only the {len(usable)} columns knowable before the work are offered "
            f"to these models; {len(excluded)} are withheld as outcomes, "
            f"derivations of outcomes, identifiers or of unestablished timing. "
            f"This is what keeps a score honest rather than flattering.",
            f"تُعرض على هذه النماذج الأعمدة الـ{len(usable)} المعروفة قبل تنفيذ "
            f"العمل فقط، ويُحجب {len(excluded)} عموداً لأنها نتائج أو مشتقات منها "
            f"أو مُعرِّفات أو غير محددة التوقيت. هذا ما يجعل النتيجة صادقة لا مُجمِّلة.",
            ["c_inputs_usable", "c_inputs_excluded"])]

        cards, checks, verdicts = [], [], []
        for target in self.targets:
            card, target_claims, target_calcs, check = self._evaluate(
                ctx, target, rows, columns, usable, date)
            cards.append(card)
            claims += target_claims
            calculations += target_calcs
            checks.append(check)
            verdicts.append((target, card))

        summary = self._summary(verdicts)
        return {
            "status": "succeeded",
            "summary": summary[:490],
            "claims": claims[:modelling.MAX_CLASSES * 10],
            "calculations": calculations,
            "quality_checks": checks,
            "output": {
                "models": cards,
                "model_inputs_usable": usable,
                "headline": summary,
                "question": self.question,
                "report_markdown": self._report(ctx, verdicts, usable, excluded),
            },
        }

    # -- one target -----------------------------------------------------
    def _evaluate(self, ctx, target, rows, columns, usable, date):
        prefix, key = self.role, target.key
        missing = [c for c in target.needs if c not in columns]
        if missing:
            return self._unsupported(
                ctx, target,
                f"the dataset has no {', '.join(missing)}, so the target cannot "
                f"be formed", f"c_{key}")

        pairs = target.labelled(rows)
        if len(pairs) < MIN_TRAIN + MIN_TEST:
            return self._unsupported(
                ctx, target,
                f"only {len(pairs)} records can be labelled; at least "
                f"{MIN_TRAIN + MIN_TEST} are needed", f"c_{key}")

        population_rows = [row for row, _ in pairs]
        labels_by_id = {id(row): label for row, label in pairs}
        train_idx, test_idx, split = modelling._split(population_rows, date)
        train_rows = [population_rows[i] for i in train_idx]
        test_rows = [population_rows[i] for i in test_idx]
        train_labels = [labels_by_id[id(r)] for r in train_rows]
        test_labels = [labels_by_id[id(r)] for r in test_rows]

        if (len(train_rows) < MIN_TRAIN or len(test_rows) < MIN_TEST
                or len(set(train_labels)) < 2 or len(set(test_labels)) < 2):
            return self._unsupported(
                ctx, target,
                f"the chronological split leaves {len(train_rows)} training and "
                f"{len(test_rows)} held-out records, or a single class on one "
                f"side, so the result would not be measurable", f"c_{key}")

        numeric = set(analytics._numeric(ctx))
        numbers = [c for c in usable if c in numeric]
        texts = []
        for column in usable:
            if column in numeric:
                continue
            # The held-out records must not decide which inputs are admitted
            # or which categorical levels the model learns.
            levels = Counter(str(r.get(column) or "") for r in train_rows)
            if 2 <= len(levels) <= modelling.MAX_LEVELS:
                texts.append((column, [l for l, _ in levels.most_common()]))
            if len(texts) == modelling.MAX_TEXT_INPUTS:
                break
        if not numbers and not texts:
            return self._unsupported(
                ctx, target,
                "no column knowable before the decision survives the contract, "
                "so there is nothing honest to predict from", f"c_{key}")

        names, vector = modelling._vectoriser(numbers, texts)
        train_cohort = [(r, label, vector(r))
                        for r, label in zip(train_rows, train_labels)]
        test_cohort = [(r, label, vector(r))
                       for r, label in zip(test_rows, test_labels)]
        train_cohort = [(r, label, v) for r, label, v in train_cohort if v is not None]
        test_cohort = [(r, label, v) for r, label, v in test_cohort if v is not None]
        if len(train_cohort) < MIN_TRAIN or len(test_cohort) < MIN_TEST:
            return self._unsupported(
                ctx, target, "too few records carry every input to fit", f"c_{key}")
        train_vectors = [v for _, _, v in train_cohort]
        kept_labels = [label for _, label, _ in train_cohort]
        truth = [label for _, label, _ in test_cohort]
        if len(set(kept_labels)) < 2 or len(set(truth)) < 2:
            return self._unsupported(
                ctx, target,
                "records carrying every input have only one class on the "
                "training or held-out side, so balanced accuracy cannot "
                "evaluate both outcomes", f"c_{key}")

        scale = modelling._scaler(train_vectors)
        model = modelling.fit_naive_bayes([scale(v) for v in train_vectors], kept_labels)
        predicted = [modelling.predict_naive_bayes(model, scale(v))
                     for _, _, v in test_cohort]
        model_score = _balanced_accuracy(truth, predicted)

        common = Counter(kept_labels).most_common(1)[0][0]
        majority_score = _balanced_accuracy(truth, [common] * len(truth))
        rule_column, rule_score = _grouping_rules(
            [r for r, _, _ in train_cohort], kept_labels,
            [r for r, _, _ in test_cohort], truth,
            [c for c in usable if c not in numeric])
        baseline_score = max(majority_score, rule_score)
        baseline_name = (f"commonest label by {rule_column}"
                         if rule_score >= majority_score and rule_column
                         else "always the commonest label")

        improvement = modelling._improvement(model_score, baseline_score, False)
        beats = improvement >= modelling.BEATS
        # Two tests, not one. ADR 0033's 5% margin is kept as-is, but a
        # majority-class baseline scores exactly 0.5 under balanced
        # accuracy, so clearing it by 5% can still mean a near coin flip.
        # A model is only called useful when it is also clearly better
        # than chance in absolute terms.
        above_chance = model_score >= CHANCE + CHANCE_MARGIN
        verdict = "useful" if (beats and above_chance) else "weak"

        card = modelling._card(
            "maintenance_risk", f"{key}: {target.question}", names,
            len(train_vectors), len(test_cohort), split, "balanced accuracy",
            round(model_score, 4), round(baseline_score, 4), baseline_name,
            round(improvement, 4), beats,
            {"verdict": verdict, "decision": target.decision,
             "beats_baseline_margin": beats, "clearly_above_chance": above_chance,
             "horizon": target.horizon,
             "positive_rate_held_out": round(
                 sum(1 for t in truth if t) / len(truth), 4),
             "baseline_majority": round(majority_score, 4),
             "baseline_best_rule": round(rule_score, 4),
             "baseline_rule_column": rule_column,
             "train_records_unmeasured": len(train_rows) - len(train_cohort),
             "test_records_unmeasured": len(test_rows) - len(test_cohort)})

        defining = [c for c in target.defines_label
                    if any(c == name or name.startswith(f"{c} =") for name in names)]
        calcs = [
            modelling._calc(prefix, f"c_{key}_model", f"{key}_balanced_accuracy",
                            round(model_score, 4),
                            f"average of each class's hit rate on the held-out "
                            f"records ({len(test_cohort)} of them)"),
            modelling._calc(prefix, f"c_{key}_baseline", f"{key}_baseline",
                            round(baseline_score, 4),
                            f"strongest of the majority class "
                            f"({majority_score:.3f}) and the best known-before "
                            f"grouping rule ({rule_score:.3f}"
                            + (f", by {rule_column}" if rule_column else "") + ")"),
            modelling._calc(prefix, f"c_{key}_improvement", f"{key}_improvement",
                            round(improvement, 4),
                            "(model - baseline) / baseline on the same held-out "
                            "records"),
        ]
        if verdict == "useful":
            claim = modelling._claim(
                ctx, prefix, f"cl_{key}", "calculation",
                f"{target.question} Balanced accuracy {model_score:.0%} against "
                f"{baseline_score:.0%} for the {baseline_name}, an improvement of "
                f"{improvement:.0%} on {len(test_cohort)} held-out records. "
                f"{target.decision}",
                f"{target.question_ar} دقة متوازنة {model_score:.0%} مقابل "
                f"{baseline_score:.0%} لخط الأساس، بتحسن {improvement:.0%} على "
                f"{len(test_cohort)} سجلات محجوزة. {target.decision_ar}",
                [f"c_{key}_model", f"c_{key}_baseline", f"c_{key}_improvement"])
        else:
            claim = modelling._claim(
                ctx, prefix, f"cl_{key}", "limitation",
                f"{target.question} The model reaches {model_score:.0%} balanced "
                f"accuracy against {baseline_score:.0%} for the {baseline_name} "
                f"on {len(test_cohort)} held-out records — an improvement of "
                f"{improvement:.0%}. "
                f"It should not be used to decide."
                + ("" if beats else " The margin over the baseline is short of 5%.")
                + ("" if above_chance else
                   f" It is also within {CHANCE_MARGIN:.0%} of a coin flip in "
                   f"absolute terms, and a majority-class baseline scores "
                   f"{CHANCE:.0%} under this metric by construction."),
                f"{target.question_ar} يبلغ النموذج {model_score:.0%} دقة متوازنة "
                f"مقابل {baseline_score:.0%} لخط الأساس على {len(test_cohort)} "
                f"سجلات محجوزة، بتحسن {improvement:.0%}. فلا ينبغي استخدامه في القرار."
                + ("" if beats else " هامش التحسن على خط الأساس أقل من 5%.")
                + ("" if above_chance else
                   f" كما يقع ضمن {CHANCE_MARGIN:.0%} من التخمين العشوائي بالقيمة "
                   f"المطلقة، ويسجل خط أساس الفئة الأكثر شيوعاً {CHANCE:.0%} "
                   f"بحكم تعريف هذا المقياس."),
                [f"c_{key}_model", f"c_{key}_baseline", f"c_{key}_improvement"])
        claims = [claim]
        if defining:
            claims.append(modelling._claim(
                ctx, prefix, f"cl_{key}_defining", "assumption",
                f"{', '.join(defining)} is both an input and part of how "
                f"{key} is defined. It was knowable before the work, so using it "
                f"is legitimate, but the model partly reconstructs the comparison "
                f"that sets the target rather than predicting it from independent "
                f"evidence.",
                f"يُستخدم {', '.join(defining)} مدخلاً وهو في الوقت نفسه جزء من "
                f"تعريف {key}. كان معروفاً قبل تنفيذ العمل فاستخدامه مشروع، لكن "
                f"النموذج يعيد تكوين المقارنة التي تحدد الهدف جزئياً بدل التنبؤ بها "
                f"من أدلة مستقلة.",
                [f"c_{key}_model"]))
        check = {"name": f"{key}_beats_baseline", "passed": beats and above_chance,
                 "detail": f"{model_score:.3f} against {baseline_score:.3f} "
                           f"({baseline_name}); improvement {improvement:+.1%}; "
                           f"{'above' if above_chance else 'within ' + format(CHANCE_MARGIN, '.0%') + ' of'} chance"}
        return card, claims, calcs, check

    def _unsupported(self, ctx, target, reason, calc_id):
        """A target the data cannot answer, said plainly."""
        card = {"kind": "maintenance_risk", "target": f"{target.key}: {target.question}",
                "fitted": False, "details": {"verdict": "not_supported",
                                             "reason": reason,
                                             "decision": target.decision}}
        calc = modelling._calc(self.role, calc_id, f"{target.key}_not_fitted", 0,
                               f"not fitted: {reason}")
        claim = modelling._claim(
            ctx, self.role, f"cl_{target.key}", "limitation",
            f"{target.question} Not answered: {reason}. No score is reported, "
            f"because an unfitted model has none.",
            f"{target.question_ar} لم يُجَب: {reason}. لا تُذكر أي نتيجة لأن "
            f"النموذج لم يُبنَ.",
            [calc_id])
        check = {"name": f"{target.key}_fitted", "passed": False, "detail": reason}
        return card, [claim], [calc], check

    # -- presentation ---------------------------------------------------
    def _summary(self, verdicts):
        useful = [t for t, c in verdicts
                  if c.get("details", {}).get("verdict") == "useful"]
        weak = [t for t, c in verdicts
                if c.get("details", {}).get("verdict") == "weak"]
        missing = [t for t, c in verdicts
                   if c.get("details", {}).get("verdict") == "not_supported"]
        def scored(targets):
            # Carry the absolute figure: "beat its baseline" says nothing
            # about whether the model is any good.
            out = []
            for target, card in verdicts:
                if target not in targets:
                    continue
                metric = card.get("metric") or {}
                value = metric.get("model")
                out.append(f"{target.key} {value:.0%}" if value is not None
                           else target.key)
            return ", ".join(out)

        parts = []
        if useful:
            parts.append(f"useful: {scored(useful)}")
        if weak:
            parts.append(f"weak, not for decisions: {scored(weak)}")
        if missing:
            parts.append(f"not fitted: {scored(missing)}")
        return ("; ".join(parts) + " (balanced accuracy on held-out records)."
                if parts else "No targets were evaluated.")

    def _report(self, ctx, verdicts, usable, excluded):
        def say(en, ar):
            return modelling._say(ctx, en, ar)

        lines = [say(f"# {self.title.split(' — ')[0]} — {self.question}",
                     f"# {self.title_ar}"), "",
                 say(f"**Inputs:** {len(usable)} columns knowable before the decision; "
                     f"{len(excluded)} withheld by the maintenance contract.",
                     f"**المدخلات:** {len(usable)} أعمدة معروفة قبل القرار؛ "
                     f"حُجب {len(excluded)} بموجب عقد الصيانة."), "",
                 say("| Target | Decision supported by this result | Verdict | Model | Baseline |",
                     "| الهدف | القرار المدعوم بهذه النتيجة | التقييم | النموذج | خط الأساس |"),
                 "| --- | --- | --- | --- | --- |"]
        for target, card in verdicts:
            details = card.get("details", {})
            verdict = details.get("verdict", "not_supported")
            metric = card.get("metric") or {}
            model = f"{metric.get('model'):.3f}" if metric.get("model") is not None else "—"
            baseline = (f"{metric.get('baseline'):.3f} ({metric.get('baseline_name')})"
                        if metric.get("baseline") is not None else "—")
            decision = (say(target.decision, target.decision_ar) if verdict == "useful"
                        else say("No decision is supported by this model.",
                                 "لا يدعم هذا النموذج اتخاذ قرار."))
            verdict_text = say(verdict, {
                "useful": "يجتاز حدود التقييم", "weak": "ضعيف",
                "not_supported": "غير مدعوم",
            }.get(verdict, verdict))
            lines.append(f"| {say(target.question, target.question_ar)} | "
                         f"{decision} | {verdict_text} | "
                         f"{model} | {baseline} |")
        lines += ["", say(
            "A model counts as useful only when it improves on the stronger of "
            "the majority class and the best known-before grouping rule by at "
            "least 5% and reaches at least 55% balanced accuracy (ADR 0040). "
            "The model and baselines use the same measured training and held-out "
            "records. A weak model supports no intervention decision.",
            "يُعد النموذج مفيداً فقط إذا تحسن بنسبة 5% على الأقل على الأقوى من "
            "خط أساس الفئة الأكثر شيوعاً وأفضل قاعدة تجميع معروفة قبل القرار، "
            "وبلغ دقة متوازنة قدرها 55% على الأقل (ADR 0040). يستخدم النموذج "
            "وخطوط الأساس سجلات التدريب والاختبار المقاسة نفسها. ولا يدعم "
            "النموذج الضعيف قرار التدخل.")]
        return "\n".join(lines)
