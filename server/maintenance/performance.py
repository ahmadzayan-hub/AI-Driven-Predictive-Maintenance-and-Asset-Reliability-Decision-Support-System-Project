"""Configured display targets, separate from engineering or report approval.

Rules use the controlled KPI scale and unrounded arithmetic. There are no
universal target bands: an absent target is unassessed, never good performance.
"""

import copy
import hashlib
import json
import math
import re

from .kpis import REGISTER

MAX_RULES = len(REGISTER)
MAX_SOURCE = 240
MAX_POLICY_BYTES = 16_384
DIRECTIONS = ("higher", "lower", "range")
BOUNDARIES = {
    "higher": ("good_at", "okay_at"),
    "lower": ("good_at", "okay_at"),
    "range": ("good_min", "good_max", "okay_min", "okay_max"),
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class PolicyError(ValueError):
    def __init__(self, en, ar):
        super().__init__(en)
        self.en, self.ar = en, ar

    def detail(self, language):
        return self.ar if language == "ar" else self.en


def validate_rules(rules):
    """Validate, bound and normalize the complete replacement policy."""
    if not isinstance(rules, dict) or len(rules) > MAX_RULES:
        raise PolicyError(f"Supply at most {MAX_RULES} registered KPI target rules.",
                          f"حدد {MAX_RULES} قاعدة أهداف كحد أقصى لمؤشرات الأداء المسجلة.")
    normalized = {}
    for key, raw in rules.items():
        if key not in REGISTER or not isinstance(raw, dict):
            raise PolicyError("Each rule must name a registered maintenance KPI.",
                              "يجب أن تسمي كل قاعدة مؤشر أداء صيانة مسجلاً.")
        direction = raw.get("direction")
        if direction not in DIRECTIONS:
            raise PolicyError("Target direction must be higher, lower or range.",
                              "يجب أن يكون اتجاه الهدف أعلى أو أقل أو نطاقاً (higher أو lower أو range).")
        fields = BOUNDARIES[direction]
        expected = {"direction", "scale", "source_ref", *fields}
        # A stamp says which definition of the measure the target was set for.
        # Absent means a target saved before stamps existed: definition 1.
        stamped = "definition" in raw
        if stamped:
            expected.add("definition")
            stamp = raw["definition"]
            if (isinstance(stamp, bool) or not isinstance(stamp, int)
                    or not 1 <= stamp <= REGISTER[key].definition):
                raise PolicyError("The definition stamp must name a current or earlier definition of the measure.",
                                  "يجب أن يشير ختم التعريف إلى تعريف حالي أو سابق للمؤشر.")
        if set(raw) != expected:
            raise PolicyError("Provide exactly the boundaries for the selected target direction.",
                              "حدد حدود اتجاه الهدف المختار فقط، مع المقياس ومرجع المصدر.")
        if raw.get("scale") != REGISTER[key].scale:
            raise PolicyError(f"The target scale for {key} must be {REGISTER[key].scale}.",
                              f"يجب أن يكون مقياس هدف {key} هو {REGISTER[key].scale}.")
        source = raw.get("source_ref")
        if (not isinstance(source, str) or not source.strip()
                or len(source) > MAX_SOURCE
                or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in source)):
            raise PolicyError("A single-line source reference of 1–240 characters is required.",
                              "يلزم مرجع مصدر في سطر واحد من 1 إلى 240 حرفاً.")
        limits = {}
        for name in fields:
            number = raw[name]
            if isinstance(number, bool) or not isinstance(number, (int, float)):
                raise PolicyError("Every target boundary must be a finite number, not text or a boolean.",
                                  "يجب أن يكون كل حد للهدف عدداً منتهياً، وليس نصاً أو قيمة منطقية.")
            try:
                number = float(number)
            except (OverflowError, ValueError):
                number = math.inf
            if not math.isfinite(number):
                raise PolicyError("Every target boundary must be a finite number.",
                                  "يجب أن يكون كل حد للهدف عدداً منتهياً.")
            limits[name] = number
        ordered = (limits["good_at"] >= limits["okay_at"] if direction == "higher" else
                   limits["good_at"] <= limits["okay_at"] if direction == "lower" else
                   limits["okay_min"] <= limits["good_min"] <= limits["good_max"] <= limits["okay_max"])
        if not ordered:
            raise PolicyError("Good and okay boundaries must be ordered; the good range must lie inside the okay range.",
                              "يجب ترتيب حدود الجيد والمقبول؛ ويجب أن يقع النطاق الجيد داخل النطاق المقبول.")
        normalized[key] = {"direction": direction, "scale": raw["scale"],
                           **limits, "source_ref": source.strip()}
        if stamped:
            normalized[key]["definition"] = raw["definition"]
    return normalized


def policy(rules=None):
    rules = validate_rules({} if rules is None else rules)
    return {"revision": digest(rules), "rules": rules}


def load_policy(store, run_id):
    record = store.latest_kpi_policy(run_id)
    if not record:
        return policy()
    current = policy(json.loads(record["rules_json"]))
    if current["revision"] != record["revision"]:
        raise ValueError("Stored KPI policy revision does not match its rules.")
    return current


def parse_update(body):
    if (not isinstance(body, dict) or set(body) != {"expected_revision", "rules"}
            or not isinstance(body.get("expected_revision"), str)
            or re.fullmatch(r"[a-f0-9]{64}", body["expected_revision"]) is None):
        raise PolicyError("Supply the current 64-character revision and a complete rules object.",
                          "حدد المراجعة الحالية المكونة من 64 حرفاً وكائن القواعد الكامل.")
    return body["expected_revision"], policy(body["rules"])


def parse_json(content):
    """Reject excessive nesting before entering the platform JSON decoder.

    A valid policy needs only three object levels. Quoted/escaped brackets in
    a source reference are data and do not contribute to structural depth.
    """
    depth, quoted, escaped = 0, False, False
    for byte in content:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (123, 91):
            depth += 1
            if depth > 16:
                raise PolicyError("The target policy is nested too deeply.",
                                  "تتجاوز سياسة الأهداف عمق التداخل المسموح.")
        elif byte in (125, 93):
            depth -= 1
    return json.loads(content)


def assessment(measure, rules=None, language="en"):
    """A display status for measured records, never an engineering approval."""
    rule = (rules or {}).get(measure["key"])
    ar = language == "ar"

    def say(en, arabic):
        return arabic if ar else en

    out = {"status": "unassessed", "reason_code": "no_target",
           "reason": say("No display target is configured; no performance verdict is assigned.",
                         "لم يُحدد هدف للعرض؛ ولم يُمنح تقييم للأداء."),
           "direction": rule["direction"] if rule else None,
           "source_ref": rule["source_ref"] if rule else None,
           "rule_id": digest({"key": measure["key"], "rule": rule}) if rule else None,
           "thresholds": ({name: rule[name] for name in BOUNDARIES[rule["direction"]]} if rule else None)}
    number = measure.get("value")
    if (isinstance(number, bool) or not isinstance(number, (int, float))
            or not math.isfinite(number) or measure.get("records", 0) <= 0):
        out.update(status="unavailable", reason_code="unmeasured",
                   reason=say("No finite measured value is available; absence is not poor or zero performance.",
                              "لا تتوفر قيمة مقاسة منتهية؛ ولا يعني غياب القياس أداءً ضعيفاً أو صفرياً."))
        return out
    if not rule:
        return out
    if rule.get("definition", 1) < REGISTER[measure["key"]].definition:
        out.update(reason_code="target_outdated",
                   reason=say("This target was set for an earlier definition of the measure; review it before it judges the figure again.",
                              "حُدِّد هذا الهدف لتعريف سابق للمؤشر؛ راجعه قبل أن يُستخدم في الحكم على الرقم مجدداً."))
        return out
    if rule["direction"] == "higher":
        good, okay = number >= rule["good_at"], number >= rule["okay_at"]
    elif rule["direction"] == "lower":
        good, okay = number <= rule["good_at"], number <= rule["okay_at"]
    else:
        good = rule["good_min"] <= number <= rule["good_max"]
        okay = rule["okay_min"] <= number <= rule["okay_max"]
    status = "good" if good else "okay" if okay else "bad"
    reasons = {
        "good": ("The measured value meets the configured good target.",
                 "تستوفي القيمة المقاسة الهدف الجيد المحدد."),
        "okay": ("The measured value meets the configured okay target but not the good target.",
                 "تستوفي القيمة المقاسة الهدف المقبول المحدد، ولا تستوفي الهدف الجيد."),
        "bad": ("The measured value is outside the configured good and okay targets.",
                "تقع القيمة المقاسة خارج الهدفين الجيد والمقبول المحددين."),
    }
    out.update(status=status, reason_code="configured_" + status,
               reason=say(*reasons[status]))
    if measure.get("records_unmeasured", 0):
        out["reason"] += say(" It describes measured records only; missing measurements remain disclosed.",
                             " يصف السجلات المقاسة فقط؛ ويظل الإفصاح عن القياسات المفقودة قائماً.")
    return out


def assess_measures(measures, rules=None, language="en"):
    return [{**copy.deepcopy(measure),
             "assessment": assessment(measure, rules, language)} for measure in measures]
