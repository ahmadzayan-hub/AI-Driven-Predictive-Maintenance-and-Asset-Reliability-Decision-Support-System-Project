"""Bounded evidence projection, not a new analysis, forecast or approval."""
import math

MAX_ITEMS = 32
MAX_TEXT = 1000


def numeric(value):
    return type(value) in (int, float) and -1e300 <= value <= 1e300 and math.isfinite(value)


def scalar(value):
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value if len(value) <= MAX_TEXT else None
    if numeric(value):
        return value
    return None


def model_audit(card):
    """Known persisted card schema only; no arbitrary dictionaries or rows."""
    result = []
    def row(en, ar, value):
        result.append({'label_en': en, 'label_ar': ar, 'value': scalar(value)})
    for key, en, ar in (
        ('version', 'Model card version', 'إصدار بطاقة النموذج'),
        ('fitted_at', 'Fitted at (not data period)', 'وقت التدريب (ليس فترة البيانات)'),
        ('snapshot', 'Training source fingerprint', 'بصمة مصدر التدريب')):
        item = card.get(key)
        row(en, ar, item if (isinstance(item, str) or (key == 'version' and type(item) is int and item >= 1)) else None)
    window = card.get('training_window')
    window = window if isinstance(window, dict) else {}
    row('Training period start', 'بداية فترة التدريب', window.get('first') if isinstance(window.get('first'), str) else None)
    row('Training period end', 'نهاية فترة التدريب', window.get('last') if isinstance(window.get('last'), str) else None)
    excluded = card.get('excluded_inputs')
    if isinstance(excluded, dict):
        entries = [(key, value) for key, value in excluded.items()
                   if isinstance(key, str) and len(key) <= 160 and isinstance(value, str) and len(value) <= MAX_TEXT]
        for key, value in sorted(entries)[:MAX_ITEMS]:
            row('Excluded input: ' + key, 'مدخل مستبعد: ' + key, value)
        if len(entries) != len(excluded) or len(entries) > MAX_ITEMS:
            row('Excluded-input details omitted by export bounds', 'تفاصيل استبعاد لم تُعرض بسبب حدود التصدير', True)
    else:
        row('Excluded-input reasons', 'أسباب استبعاد المدخلات', None)
    details = card.get('details')
    details = details if isinstance(details, dict) else {}
    for key, en, ar in (
        ('balanced_accuracy_lower_bound', 'Mean per-class one-sided 95% Wilson lower bound', 'متوسط الحد الأدنى لويلسون أحادي الجانب بنسبة 95% لكل فئة'),
        ('held_out_records', 'Held-out records', 'سجلات الاختبار المحجوزة'),
        ('held_out_positives', 'Held-out positive outcomes', 'النتائج الإيجابية المحجوزة'),
        ('train_records_unmeasured', 'Unmeasured training records', 'سجلات التدريب غير المقاسة'),
        ('test_records_unmeasured', 'Unmeasured test records', 'سجلات الاختبار غير المقاسة'),
        ('accuracy', 'Recorded classification accuracy', 'دقة التصنيف المسجلة')):
        if key in details:
            item = details[key]
            is_rate = key in {'balanced_accuracy_lower_bound', 'accuracy'}
            valid = (numeric(item) and 0 <= item <= 1) if is_rate else (type(item) is int and item >= 0)
            row(en, ar, item if valid else None)
    probabilities = details.get('probabilities')
    if isinstance(probabilities, dict):
        event = probabilities.get('positive_class')
        row('Calibration event (positive class)', 'حدث المعايرة (الفئة الإيجابية)',
            event if isinstance(event, str) and len(event) <= 160 else None)
        for key, en, ar in (
            ('brier', 'Calibration Brier score', 'درجة براير للمعايرة'),
            ('baseline_brier', 'Baseline Brier score', 'درجة براير للخط المرجعي'),
            ('base_rate', 'Training base rate', 'المعدل الأساسي للتدريب'),
            ('better_than_base_rate', 'Calibration beats base rate', 'المعايرة أفضل من المعدل الأساسي')):
            item = probabilities.get(key)
            valid = type(item) is bool if key == 'better_than_base_rate' else (numeric(item) and 0 <= item <= 1)
            row(en, ar, item if valid else None)
    classes = details.get('classes')
    if isinstance(classes, list):
        safe_classes = [label for label in classes[:6] if isinstance(label, str) and len(label) <= 160]
        hit_rates = details.get('hit_rates') if isinstance(details.get('hit_rates'), dict) else {}
        confusion = details.get('confusion') if isinstance(details.get('confusion'), dict) else {}
        for label in safe_classes:
            rate = hit_rates.get(label)
            valid = numeric(rate) and 0 <= rate <= 1
            row('Class hit rate: ' + label, 'معدل إصابة الفئة: ' + label, rate if valid else None)
            counts = confusion.get(label) if isinstance(confusion.get(label), dict) else {}
            for predicted in safe_classes:
                if predicted in counts:
                    count = counts[predicted]
                    row('Confusion actual ' + label + ' → predicted ' + predicted,
                        'الالتباس الفعلي ' + label + ' ← المتوقع ' + predicted,
                        count if type(count) is int and count >= 0 else None)
        if len(classes) > 6 or len(safe_classes) != len(classes):
            row('Class evidence omitted by export bounds', 'أدلة فئات لم تُعرض بسبب حدود التصدير', True)
    if isinstance(probabilities, dict) and isinstance(probabilities.get('bins'), list):
        for index, item in enumerate(probabilities['bins'][:5]):
            if not isinstance(item, dict):
                continue
            limits = item.get('range')
            if isinstance(limits, list) and len(limits) == 2 and all(numeric(v) and 0 <= v <= 1 for v in limits) and limits[0] <= limits[1]:
                row(f'Calibration bin {index + 1} range', f'نطاق شريحة المعايرة {index + 1}', f'{limits[0]}–{limits[1]}')
            for key, en, ar in (('records', 'records', 'السجلات'), ('mean_predicted', 'mean predicted', 'متوسط المتوقع'), ('observed', 'observed share', 'الحصة المرصودة')):
                value = item.get(key)
                valid = (type(value) is int and value >= 0) if key == 'records' else (numeric(value) and 0 <= value <= 1)
                row(f'Calibration bin {index + 1}: {en}', f'شريحة المعايرة {index + 1}: {ar}', value if valid else None)
        if len(probabilities['bins']) > 5:
            row('Calibration bins omitted by export bounds', 'شرائح معايرة لم تُعرض بسبب حدود التصدير', True)
    return result


def build_contract(brief):
    """Versioned unapproved view, included in the brief's snapshot digest."""
    en = brief['language'] != 'ar'
    say = lambda a, b: a if en else b
    evidence = {item['id']: item for item in brief['evidence']}
    controls = {'executive.kpi.' + item['key']: item for item in brief['kpis']['measures']}
    decisions = []
    for item in (brief.get('advisory') or {}).get('decisions', [])[:MAX_ITEMS]:
        refs = [ref for ref in item.get('evidence_refs', []) if ref in evidence][:MAX_ITEMS]
        decisions.append({
            'id': item['id'], 'problem': item['title'], 'review_rationale': item['action'],
            'demonstrated_finding': [{'id': ref, 'label': evidence[ref]['label'], 'value': evidence[ref]['value'], 'scope': evidence[ref]['scope']} for ref in refs],
            'proposed_action': say('Review the cited evidence before selecting an intervention.', 'راجع الأدلة المشار إليها قبل اختيار تدخل.'),
            'proposed_owner': item['owner'], 'assignment_status': 'unassigned',
            'next_step': item['gate'], 'schedule': None,
            'evidence_refs': refs,
            'controlled_kpis': [ref for ref in refs if ref in controls],
            'evidence_limits': list(brief['readiness']['limitations']),
            'operational_constraints': None, 'impact_estimate': None,
            'impact_status': 'not_evaluated_in_this_brief', 'approval': None})
    return {'version': 1, 'status': 'unapproved_evidence_projection',
            'analytical_claims_added': False, 'generation': 'deterministic_existing_evidence',
            'questions': [dict(item) for item in brief['questions']],
            'dataset': {'records': brief['scope']['records'], 'total_records': brief['scope']['total_records'],
                        'grain': None, 'period': None, 'source_fingerprint': None},
            'coverage': [
                {'section': 'business_context', 'status': 'questions_only'},
                {'section': 'dataset_scope', 'status': 'scope_available_grain_period_not_recorded'},
                {'section': 'methodology', 'status': 'kpi_definitions_only_quality_checks_not_projected'},
                {'section': 'analytical_findings', 'status': 'verified_findings_available' if brief['findings'] else 'not_available'},
                {'section': 'model_evaluation', 'status': 'recorded_cards_available' if brief['models'] else 'not_available'},
                {'section': 'executive_actions', 'status': 'review_proposals_only'},
                {'section': 'financial_scenarios', 'status': 'not_evaluated_in_this_brief'},
                {'section': 'implementation_plan', 'status': 'not_recorded'},
                {'section': 'ai_participation', 'status': 'expert_review_not_demonstrated_by_this_view'}],
            'decisions': decisions}
