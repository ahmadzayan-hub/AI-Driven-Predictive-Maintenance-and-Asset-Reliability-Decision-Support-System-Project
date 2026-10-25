"""Session-localized selector text; avoids shipping both languages in initial JS."""


def labels(language):
    values = {
        "title": ("Data for this chat", "بيانات هذه المحادثة"),
        "none": ("No report selected", "لم يُحدد تقرير"),
        "choose": ("Choose a completed analysis", "اختر تحليلاً مكتملاً"),
        "load": ("Show my reports", "عرض تقاريري"),
        "use": ("Use this report", "استخدام هذا التقرير"),
        "clear": ("Clear selection", "إلغاء التحديد"),
        "empty": ("No completed analyses available. Analyze a dataset first.", "لا توجد تحليلات مكتملة متاحة. حلل مجموعة بيانات أولاً."),
        "help": ("Selection is saved for this conversation. Ask total maintenance cost, availability, recorded failures, or railway signaling age. Answers are calculated from selected data with formulas and source references; unsupported questions ask for clarification.",
                 "يُحفظ اختيارك لهذه المحادثة. اسأل عن إجمالي تكلفة الصيانة أو الإتاحة أو عدد الأعطال المسجلة أو عمر إشارات السكك الحديدية. تُحسب الإجابات من البيانات المحددة مع الصيغ ومراجع المصدر؛ والأسئلة غير المدعومة تحتاج إلى توضيح."),
        "scope": ("Selected / total records", "السجلات المحددة / الإجمالية"),
        "error": ("Could not confirm the data selection. Reload reports and try again.", "تعذر تأكيد اختيار البيانات. أعد تحميل التقارير وحاول مجدداً."),
        "busy": ("Checking data selection…", "جارٍ التحقق من اختيار البيانات…"),
        "filters": ("Filters", "المرشحات"),
        "limit": ("Up to 25 completed reports are listed. Choosing a report here selects all its records.", "تُعرض حتى 25 تقريراً مكتملاً. اختيار تقرير هنا يحدد جميع سجلاته."),
    }
    return {key: value[language == "ar"] for key, value in values.items()}
