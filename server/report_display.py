"""Deterministic Arabic presentation of built-in evidence; never edit evidence.

Only registered calculation ids and complete, recognised templates translate.
Captured column/group names are source text, not a translation vocabulary.
Unknown or plugin metadata is explicitly shown in its original form.
"""

import re


# id: (original name, Arabic display name)
LABELS = {
    "c_rows": ("row_count", "عدد الصفوف"),
    "c_mapped_columns": ("mapped_columns", "الأعمدة المحددة أدوارها"),
    "c_contract_fields": ("columns_under_contract", "الأعمدة المشمولة بعقد البيانات"),
    "c_completeness": ("completeness", "اكتمال البيانات"),
    "c_dupes": ("duplicate_rows", "الصفوف المكررة"),
    "c_dq_completeness": ("completeness_ratio", "نسبة الاكتمال"),
    "c_dq_uniqueness": ("uniqueness_ratio", "نسبة عدم التكرار"),
    "c_dq_validity": ("validity_ratio", "نسبة الصلاحية"),
    "c_dq_consistency": ("consistency_ratio", "نسبة الاتساق"),
    "c_dq_score": ("quality_score", "درجة جودة البيانات"),
    "c_pii_columns": ("columns_with_personal_data", "الأعمدة التي تتضمن بيانات شخصية"),
    "c_merge_pii": ("joined_columns_with_personal_data", "أعمدة الدمج التي تتضمن بيانات شخصية"),
    "c_rows_before": ("rows_before", "الصفوف قبل التنظيف"),
    "c_rows_after": ("rows_after", "الصفوف بعد التنظيف"),
    "c_dropped": ("rows_dropped", "الصفوف المستبعدة"),
    "c_dates_unread": ("dates_not_read", "التواريخ التي تعذرت قراءتها"),
    "c_gov_defined": ("metrics_in_glossary", "المؤشرات المسجلة في القاموس"),
    "c_gov_certified": ("measure_is_certified", "اعتماد المقياس"),
    "c_gov_conformance": ("definition_conformance", "مطابقة تعريف المقياس"),
    "c_gov_candidates": ("columns_matching_a_metric", "الأعمدة المطابقة لمؤشر مسجل"),
    "c_breakdown_candidates": ("columns_that_could_group", "الأعمدة المتاحة لتجميع البيانات"),
    "c_seg_count": ("segments", "عدد الفئات"),
    "c_seg_none": ("segments", "عدد الفئات"),
    "c_seg_hhi": ("concentration_index", "مؤشر التركّز"),
    "c_seg_pareto": ("segments_for_80_percent", "الفئات اللازمة لبلوغ 80 بالمئة"),
    "c_mean": ("mean", "المتوسط الحسابي"),
    "c_median": ("median", "الوسيط"),
    "c_spread": ("spread", "التشتت"),
    "c_unusual": ("unusual_rows", "الصفوف غير المعتادة"),
    "c_change": ("period_change", "التغير بين أول فترة وآخر فترة"),
    "c_period_records_min": ("fewest_records_in_a_period", "أقل عدد من السجلات في فترة"),
    "c_period_records_max": ("most_records_in_a_period", "أكبر عدد من السجلات في فترة"),
    "c_change_per_record": ("period_change_per_record", "التغير بين الفترات لكل سجل"),
    "c_incomplete_period": ("incomplete_last_period_records", "سجلات الفترة الأخيرة غير المكتملة"),
    "c_topshare": ("top_group_share", "حصة أكبر فئة"),
    "c_totalchange": ("total_change", "التغير الإجمالي"),
    "c_nodiag": ("diagnosable_structure", "توافر بنية للتحليل التشخيصي"),
    "c_exp_rows": ("rows_with_a_measure", "الصفوف التي تتضمن قيمة للمقياس"),
    "c_exp_mde": ("smallest_detectable_change", "أصغر تغير يمكن رصده"),
    "c_exp_arms": ("groups_compared", "عدد مجموعات المقارنة"),
    "c_exp_split": ("largest_split_deviation", "أكبر انحراف في توزيع المجموعات"),
    "c_slope": ("per_period_change", "التغير لكل فترة"),
    "c_explained": ("movement_explained_by_trend", "الحركة التي يفسرها الاتجاه"),
    "c_backtest": ("backtest_error", "خطأ الاختبار على بيانات سابقة"),
    "c_naive": ("naive_baseline_error", "خطأ خط الأساس الساذج (تكرار الفترة الأخيرة)"),
    "c_band_low": ("band_low", "الحد الأدنى لنطاق التوقع"),
    "c_band_high": ("band_high", "الحد الأعلى لنطاق التوقع"),
    "c_rate": ("measure_is_rate", "المقياس معدل أو نسبة"),
    "c_records": ("records_with_a_value", "السجلات التي تتضمن قيمة"),
    "c_margin": ("margin_over_next_option", "الفارق عن الخيار التالي"),
    "c_sens_uniform": ("winner_unchanged_uniform_uplift", "ثبات الخيار الأول عند تحسن موحد"),
    "c_periods": ("periods_available", "الفترات المتاحة"),
    "c_anom_periods": ("periods_available", "الفترات المتاحة"),
    "c_anom_spread": ("typical_gap_from_trend", "الفجوة المعتادة عن الاتجاه"),
    "c_direction": ("measure_direction_declared", "تحديد اتجاه تحسن المقياس"),
    "c_nooptions": ("options_available", "الخيارات المتاحة"),
    "c_sens_none": ("options_tested", "الخيارات المختبرة"),
    "c_sens_stable": ("winner_unchanged_within_ranges", "ثبات الخيار الأول ضمن نطاقات التحسن"),
    "c_sens_breakeven": ("break_even_ratio", "نسبة التعادل"),
    "c_lin_calcs": ("calculations_produced", "العمليات الحسابية المنتجة"),
    "c_lin_claims": ("claims_made", "الاستنتاجات المسجلة"),
    "c_lin_dangling": ("claims_citing_missing_evidence", "الاستنتاجات التي تستشهد بأدلة مفقودة"),
}

LABEL_RULES = [
    (r"c_total", r"total_(.+)", "إجمالي {0}"),
    (r"c_contrib_\d+", r"change_from_(.+)", "التغير من {0}"),
    (r"c_share_\d+", r"share_of_change_(.+)", "حصة {0} من التغير"),
    (r"c_flip_.+", r"flip_uplift_(.+)", "نسبة التحسن التي يتغير عندها الترتيب لصالح خيار {0}"),
    (r"c_cost_.+", r"cost_(.+)", "تكلفة خيار {0}"),
    (r"c_pii_rows_\d+_\d+", r"(.+)_rows", "صفوف {0}"),
    (r".*c_.+_held_out", r"(.+)_held_out_records", "السجلات المحجوزة لهدف {0}"),
    (r".*c_.+_lower_bound", r"(.+)_balanced_accuracy_lower_bound", "الحد الأدنى للدقة المتوازنة لهدف {0}"),
    (r".*\.c_f\d+_.+", r"(.+):(.+)", "{1} من كاشف {0}"),
    (r"c_assoc_\d+", r"association_(.+)", "الارتباط مع {0}"),
    (r"c_exp_spread", r"typical_spread_of_(.+)", "التشتت المعتاد في {0}"),
    (r"c_exp_n_\d+", r"rows_per_group_for_(\d+)pct", "الصفوف لكل مجموعة لرصد تغير {0} بالمئة"),
    (r"c_exp_base", r"average_(.+)_in_(.+)", "متوسط {0} في {1}"),
    (r"c_exp_diff_\d+", r"difference_(.+)_vs_(.+)", "الفرق بين {0} و{1}"),
    (r"c_exp_range_\d+", r"range_(.+)_vs_(.+)", "نطاق الفرق بين {0} و{1}"),
    (r"c_exp_fixed_\d+", r"fixed_size_range_(.+)_vs_(.+)", "نطاق الفرق بحجم ثابت بين {0} و{1}"),
    (r"c_forecast_\d+", r"forecast_next period (.+)", "توقع الفترة التالية {0}"),
    (r"c_forecast_\d+", r"forecast_(.+)", "التوقع للفترة {0}"),
    (r"c_anom_\d+", r"gap_(.+)", "الفجوة في {0}"),
    (r"c_merge_\d+_rows_in", r"rows_before_joining_(.+)", "الصفوف قبل الدمج مع {0}"),
    (r"c_merge_\d+_matched", r"rows_matched_in_(.+)", "الصفوف المطابقة في {0}"),
    (r"c_merge_\d+_rows_out", r"rows_after_joining_(.+)", "الصفوف بعد الدمج مع {0}"),
    (r"c_merge_\d+_coverage", r"key_coverage_(.+)", "تغطية مفاتيح الربط مع {0}"),
]

OPTION_LABELS = {
    "largest_source": "تغيير أكبر مصدر", "smallest_source": "تغيير أصغر مصدر",
    "largest_movement": "تغيير أكبر حركة", "hold_course": "الاستمرار دون تغيير",
    "reduce_leader": "تقليل أكبر مصدر", "curb_increase": "كبح الزيادة",
    "protect_leader": "حماية الفئة الرائدة", "grow_laggard": "تنمية الفئة الأصغر",
    "recover_decline": "عكس التراجع",
}

# Complete exact methods; neither free-form metadata nor source values are replaced.
METHODS = {
    "len(csv rows)": "عدد صفوف ملف CSV",
    "columns given a role in the dataset's saved mapping": "الأعمدة ذات الأدوار المحددة في تعيين البيانات المحفوظ",
    "one contract row per column": "بند واحد في عقد البيانات لكل عمود",
    "1 - missing_cells/total_cells": "1 - الخلايا المفقودة/إجمالي الخلايا",
    "exact row comparison": "مقارنة الصفوف تطابقاً كاملاً",
    "filled cells / total cells": "الخلايا المعبأة / إجمالي الخلايا",
    "1 − duplicate rows / total rows": "1 − الصفوف المكررة / إجمالي الصفوف",
    "numeric cells that parse / numeric cells present": "الخلايا الرقمية القابلة للقراءة / الخلايا الرقمية الموجودة",
    "rows with every column present / total rows": "الصفوف التي تتضمن جميع الأعمدة / إجمالي الصفوف",
    "mean of the four dimension ratios × 100": "متوسط نسب أبعاد الجودة الأربعة × 100",
    "columns matching a personal-data name or value pattern": "الأعمدة المطابقة لنمط أسماء البيانات الشخصية أو قيمها",
    "joined columns matching a personal-data name or value pattern": "أعمدة الدمج المطابقة لنمط أسماء البيانات الشخصية أو قيمها",
    "count": "عدّ الصفوف",
    "empty + exact-duplicate removal": "استبعاد الصفوف الفارغة والمكررة تماماً",
    "entries accepted from metrics.json": "التعريفات المقبولة من ملف metrics.json",
    "numeric columns named by a glossary metric": "الأعمدة الرقمية المسماة في تعريف مؤشر بالقاموس",
    "repeated non-numeric columns within the display limit, excluding identifier-like, date-like and personal columns": "الأعمدة غير الرقمية ذات القيم المتكررة ضمن حد العرض، مع استبعاد المعرّفات والتواريخ والبيانات الشخصية",
    "no non-numeric column to group by": "لا يوجد عمود غير رقمي صالح للتجميع",
    "sum of squared shares (1.0 = one segment holds everything)": "مجموع مربعات الحصص (1.0 = فئة واحدة تستحوذ على الإجمالي)",
    "segments needed, largest first, to reach 80% of the total": "عدد الفئات اللازمة لبلوغ 80% من الإجمالي، بدءاً بالأكبر",
    "fmean": "المتوسط الحسابي للقيم",
    "median": "القيمة الوسطى بعد ترتيب القيم",
    "sample standard deviation": "الجذر التربيعي لتباين العينة",
    "count(|x - mean| > 2 × spread)": "عدد القيم التي تحقق |القيمة - المتوسط| > 2 × التشتت",
    "(last period − first period) / first period": "(آخر فترة − أول فترة) / أول فترة",
    "min(records with a value, per period)": "أقل عدد من السجلات ذات القيمة بين الفترات",
    "max(records with a value, per period)": "أكبر عدد من السجلات ذات القيمة بين الفترات",
    "(last period total ÷ its records − first period total ÷ its records) / (first period total ÷ its records)": "(إجمالي آخر فترة ÷ سجلاتها − إجمالي أول فترة ÷ سجلاتها) / (إجمالي أول فترة ÷ سجلاتها)",
    "largest group total / overall total": "إجمالي أكبر فئة / الإجمالي العام",
    "no period column, group column, or second numeric column was available": "لم يتوفر عمود للفترات أو للتجميع أو عمود رقمي آخر",
    "1 − (unexplained variation / total variation) for the fitted line": "1 − (التباين غير المفسر / التباين الإجمالي) لخط الاتجاه الملائم",
    "distinct periods": "عدد الفترات المختلفة",
    "standard deviation of the gaps between actual and trend": "الجذر التربيعي لتباين الفجوات بين القيم الفعلية وخط الاتجاه",
    "baseline: no change means no gain beyond the forecast": "خط الأساس: لا تغيير يعني لا مكسب إضافي فوق التوقع",
    "the same backtest for repeating the previous period's value": "الاختبار نفسه على بيانات سابقة لتكرار قيمة الفترة السابقة",
    "first forecast × (1 − backtest error)": "التوقع الأول × (1 − خطأ الاختبار على بيانات سابقة)",
    "first forecast × (1 + backtest error)": "التوقع الأول × (1 + خطأ الاختبار على بيانات سابقة)",
    "best option's expected gain minus the next option's": "المكسب المتوقع لأفضل خيار ناقص مكسب الخيار التالي",
    "change from the group / total change; may exceed 1 when other groups moved the other way": "التغير من الفئة / التغير الإجمالي؛ وقد يتجاوز 1 عندما تتحرك فئات أخرى في الاتجاه المعاكس",
    "rate, fraction or percentage by contract, glossary unit or name": "معدل أو كسر أو نسبة مئوية بحسب عقد البيانات أو وحدة القاموس أو الاسم",
    "held-out records with a formed label, scored by the model and the baseline alike": "السجلات المحجوزة ذات التصنيف المكتمل، المقيّمة بالنموذج وخط الأساس معاً",
    "no group column and no forecast": "لا يوجد عمود للتجميع ولا توقع",
    "options from the prescriptive stage": "الخيارات الناتجة عن التحليل التوجيهي",
    "recommended option compared at 5%, 10% and 20% uplift": "مقارنة الخيار الموصى به عند تحسن بنسبة 5% و10% و20%",
    "calculations emitted across every evidence-producing stage": "العمليات الحسابية الصادرة عن جميع المراحل المنتجة للأدلة",
    "claims emitted across every evidence-producing stage": "الاستنتاجات الصادرة عن جميع المراحل المنتجة للأدلة",
    "evidence ids cited by a claim but produced by no stage": "معرّفات الأدلة المستشهد بها دون أن تنتجها أي مرحلة",
    "rows of the table before this join": "صفوف الجدول قبل هذا الدمج",
    "every row kept (left join)": "الاحتفاظ بكل صف (دمج أيسر)",
    "only matched rows kept (inner join)": "الاحتفاظ بالصفوف المتطابقة فقط (دمج داخلي)",
    "rows matched / rows before this join": "الصفوف المتطابقة / الصفوف قبل هذا الدمج",
}

METHOD_RULES = [
    (r"sum\((.+)\) over cleaned rows", "مجموع {0} في الصفوف المنظفة"),
    (r"distinct values of “(.+)” with at least two rows", "عدد القيم المختلفة في «{0}» التي تضم صفين على الأقل"),
    (r"distinct values of (.+)", "عدد القيم المختلفة في {0}"),
    (r"(.+) in (.+) − (.+) in (.+)", "{0} في {1} − {2} في {3}"),
    (r"(.+) for “(.+)” in (.+) minus (.+)", "{0} للفئة «{1}» في {2} ناقص القيمة في {3}"),
    (r"Pearson correlation of (.+) and (.+) over (\d+) rows", "ارتباط بيرسون بين {0} و{1} عبر {2} صفاً"),
    (r"rows where (.+) is present", "الصفوف التي تتضمن قيمة في {0}"),
    (r"sample standard deviation of (.+) over (\d+) rows", "الجذر التربيعي لتباين عينة {0} عبر {1} صفاً"),
    (r"2·\(1\.96\+0\.84\)²·variance/\((.+)·mean\)² — two-sided 5%, 80% power", "2·(1.96+0.84)²·التباين/({0}·المتوسط)² — اختبار ثنائي الطرف عند 5% وبقدرة 80%"),
    (r"\(1\.96\+0\.84\)·√\(2·variance/\((\d+)/2\)\) ÷ mean — the existing rows split evenly into two groups", "(1.96+0.84)·√(2·التباين/({0}/2)) ÷ المتوسط — تقسيم الصفوف الموجودة بالتساوي إلى مجموعتين"),
    (r"mean (.+) over (\d+) rows where (.+) = “(.+)”", "متوسط {0} عبر {1} صفاً حيث {2} = «{3}»"),
    (r"mean (.+) in “(.+)” \((\d+) rows\) minus “(.+)” \((\d+) rows\)", "متوسط {0} في «{1}» ({2} صفاً) ناقص متوسط «{3}» ({4} صفاً)"),
    (r"difference ± (.+)·√\(var/n \+ var/n\) — a normal-mixture confidence sequence at n=(\d+), valid at every sample size, 5% split across (\d+) comparison\(s\)", "الفرق ± {0}·√(التباين/العدد + التباين/العدد) — نطاق متسلسل بخليط طبيعي عند عدد={1}، صالح عند كل حجم عينة، مع توزيع 5% على {2} مقارنة"),
    (r"difference ± (.+)·√\(var/n \+ var/n\) — valid only if the sample size was fixed before the data was collected", "الفرق ± {0}·√(التباين/العدد + التباين/العدد) — صالح فقط إذا حُدد حجم العينة قبل جمع البيانات"),
    (r"\|share of “(.+)” − (.+)\| over (\d+) rows; flagged beyond (.+)", "|حصة «{0}» − {1}| عبر {2} صفاً؛ يُعلّم عند تجاوز {3}"),
    (r"least-squares slope of (.+) against period order", "ميل {0} بطريقة المربعات الصغرى مقابل ترتيب الفترات"),
    (r"trend line extended to period (\d+)", "مدّ خط الاتجاه إلى الفترة {0}"),
    (r"average absolute percentage error over the last (\d+) period\(s\), predicted from earlier ones only", "متوسط الخطأ النسبي المطلق خلال آخر {0} فترة، بتوقعات مبنية على الفترات السابقة فقط"),
    (r"average absolute percentage error over the last (\d+) period\(s\), each predicted from earlier ones only", "متوسط الخطأ النسبي المطلق خلال آخر {0} فترة، كل منها متوقعة من الفترات السابقة لها فقط"),
    (r"winner at the low end of the uplift range \((.+)\) against every other option at the high end \((.+)\), costs as stated", "الخيار الأول عند الحد الأدنى لنطاق التحسن ({0}) مقابل كل خيار آخر عند الحد الأعلى ({1})، مع التكاليف كما ذُكرت"),
    (r"recommended option compared at (.+), (.+) and (.+) uplift applied to every option alike", "مقارنة الخيار الموصى به عند تحسن بنسبة {0} و{1} و{2} مطبقاً على كل خيار بالتساوي"),
    (r"\(winner's gain at the low end of its range \+ cost of “(.+)”\) ÷ current value of “(.+)”", "(مكسب الخيار الأول عند الحد الأدنى لنطاقه + تكلفة «{0}») ÷ القيمة الحالية لـ «{1}»"),
    (r"rows of (.+) whose value looks like a (.+)", "صفوف {0} التي تبدو قيمتها مثل {1}"),
    (r"count of rows with a value in (.+)", "عدد الصفوف التي تتضمن قيمة في {0}"),
    (r"cost of (.+) as stated in the run's assumptions", "تكلفة {0} كما ذُكرت في افتراضات التحليل"),
    (r"(.+) values that do not read as dates or month names; periods kept in the order recorded", "قيم {0} التي لا تُقرأ كتواريخ أو أسماء أشهر؛ وأُبقيت الفترات بالترتيب المسجل"),
    (r"(.+%) \((stated|assumed)\) of (.+)'s current (.+) \((.+)\) minus its stated cost (.+)", "{0} ({1}) من القيمة الحالية لـ {3} في {2} ({4}) ناقص تكلفته المذكورة {5}"),
    (r"(.+%) \((stated|assumed)\) of (.+)'s current (.+) \((.+)\)", "{0} ({1}) من القيمة الحالية لـ {3} في {2} ({4})"),
    (r"(.+) from (.+) over (.+)", "{0} من كاشف {1} عبر {2}"),
    (r"(.+) actual minus its trend value", "القيمة الفعلية في {0} ناقص قيمة اتجاهها"),
    (r"glossary entry for (.+) declares better: higher or lower", "تعريف {0} في القاموس يحدد اتجاه التحسن: الأعلى أو الأقل"),
    (r"(.+%) of (.+)'s current (.+) \((.+)\)", "{0} من القيمة الحالية لـ {2} في {1} ({3})"),
    (r"“(.+)” current value ÷ “(.+)” current value", "القيمة الحالية لـ «{0}» ÷ القيمة الحالية لـ «{1}»"),
    (r"rows whose key \((.+)\) is found in (.+)", "الصفوف التي يوجد مفتاحها ({0}) في {1}"),
    (r"“(.+)” resolved to glossary metric “(.+)”", "مطابقة «{0}» مع المؤشر «{1}» في القاموس"),
    (r"rows where (.+) equals (.+) within 0\.5%, over (\d+) checked rows", "الصفوف التي تساوي فيها قيمة {0} الصيغة {1} ضمن 0.5%، عبر {2} صفاً مفحوصاً"),
]

PII_KINDS = {"email address": "عنوان بريد إلكتروني", "phone number": "رقم هاتف",
             "long identifier": "معرّف طويل"}
GRAINS = {"day": "يوم", "month": "شهر", "quarter": "ربع سنة", "year": "سنة"}
DATE_ORDERS = {"auto": "تلقائي", "dmy": "يوم/شهر/سنة", "mdy": "شهر/يوم/سنة", "ymd": "سنة/شهر/يوم"}


def _match(rules, text):
    for pattern, template in rules:
        match = re.fullmatch(pattern, text)
        if match:
            return template.format(*match.groups())
    return None


def calculation(calc, language="en", *, builtin=True):
    """Return display cells. Values/identifiers and the input dict are untouched."""
    name, value, method = calc["name"], calc["value"], calc["method"]
    if language != "ar":
        return name, value, method
    label = None
    if builtin:
        original, translated = LABELS.get(calc["id"], (None, None))
        if name == original:
            label = translated
        for id_pattern, pattern, template in LABEL_RULES:
            if label is None and re.fullmatch(id_pattern, calc["id"]):
                label = _match([(pattern, template)], name)
        key = calc["id"].removeprefix("c_option_")
        if key in OPTION_LABELS and name == f"expected_gain_{key}":
            label = f"المكسب المتوقع لخيار {OPTION_LABELS[key]}"
    if label and re.fullmatch(r"c_pii_rows_\d+_\d+", calc["id"]):
        for kind, kind_ar in PII_KINDS.items():
            label = label.replace(kind, kind_ar)
    translated_method = (METHODS.get(method) or _match(METHOD_RULES, method)) if label else None
    if translated_method:
        for word, word_ar in (("(stated)", "(مُعلن)"), ("(assumed)", "(مفترض)")):
            translated_method = translated_method.replace(word, word_ar)
        for kind, kind_ar in PII_KINDS.items():
            translated_method = translated_method.replace(kind, kind_ar)
    if label and calc["id"] == "c_dates_unread":
        match = re.fullmatch(r"filled (.+) cells that do not read as a date at (.+) grain \((.+)\)", method)
        if match:
            column, grain, order = match.groups()
            if grain in GRAINS and order in DATE_ORDERS:
                translated_method = (f"الخلايا المعبأة في {column} التي تعذرت قراءتها كتاريخ "
                                     f"على مستوى {GRAINS[grain]} ({DATE_ORDERS[order]})")
    if label and re.fullmatch(r"c_exp_(range|fixed)_\d+", calc["id"]):
        match = re.fullmatch(r"([-+\d,.]+) to ([-+\d,.]+)", str(value))
        if match:
            value = " إلى ".join(match.groups())
    return (label or f"الاسم الأصلي: {name}", value,
            translated_method or f"الطريقة الأصلية: {method}")


def calculation_row(calc, language="en", *, builtin=True):
    name, value, method = calculation(calc, language, builtin=builtin)
    if language == "ar":
        # Arithmetic absolute-value bars are cell text, not table separators.
        name, value, method = (str(cell).replace("\\", "\\\\").replace("|", "\\|")
                               for cell in (name, value, method))
    return f"| {name} | {value} | {method} |"


CHECK_NAMES = {
    "group_totals_reconcile": "تطابق مجاميع الفئات",
    "row_accounting": "اكتمال حساب الصفوف",
    "joins_keep_the_row_count": "سلامة أعداد الصفوف بعد الدمج",
    "every_claim_has_evidence": "وجود دليل لكل استنتاج",
    "every_analytics_type_reported": "اكتمال تقارير أنواع التحليل",
    "change_decomposition_reconciles": "تطابق أجزاء التغير مع إجماليه",
    "forecast_accuracy_is_measured_or_declared": "قياس دقة التوقع أو التصريح بحدودها",
    "measure_is_certified_or_declared_uncertified": "اعتماد المقياس أو التصريح بعدم اعتماده",
    "recommendations_state_their_assumptions": "التصريح بافتراضات التوصيات",
    "personal_data_reaches_the_approver": "إبلاغ صاحب الموافقة بالبيانات الشخصية",
    "provenance_chain_is_complete": "اكتمال سلسلة إثبات المصادر",
    "claims_avoid_statistical_jargon": "وضوح لغة الاستنتاجات",
    "both_languages_cite_the_same_figures": "تطابق الأرقام بين اللغتين",
    "claim_figures_match_evidence": "تطابق أرقام الاستنتاجات مع أدلتها",
    "every_builtin_claim_is_in_the_report_language": "عرض جميع الاستنتاجات المدمجة بلغة التقرير",
}

CHECK_DETAILS = {
    "group_totals_reconcile": (
        r"Σ\(groups\)=(.+) vs total=(.+); recomputed (\d+) group total\(s\), largest difference from the published figure (.+)",
        "مجموع الفئات={0} مقابل الإجمالي={1}؛ أُعيد حساب {2} من مجاميع الفئات، وأكبر فرق عن الرقم المنشور {3}"),
    "change_decomposition_reconciles": (
        r"Σ\(segment changes\)=(.+) vs total change=(.+)",
        "مجموع تغيرات الفئات={0} مقابل التغير الإجمالي={1}"),
}


def check(check, language="en"):
    if language != "ar":
        return check["name"], check["detail"]
    name = CHECK_NAMES.get(check["name"], f"اسم الفحص الأصلي: {check['name']}")
    rule = CHECK_DETAILS.get(check["name"])
    detail = _match([rule], check["detail"]) if rule else None
    return name, detail or check["detail"]


def chart_type(kind, language="en"):
    if language != "ar":
        return kind
    return {"bar": "مخطط أعمدة", "line": "مخطط خطي"}.get(kind, f"نوع المخطط الأصلي: {kind}")
