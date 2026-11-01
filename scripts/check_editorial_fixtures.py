"""Check teaching fixture tokens only; NOT model quality or semantic validation."""
import re
from collections import Counter
EXAMPLES = [
("It is worth noting that the estimated repair time is 4.5 h for 12 units [S1]. The estimate is preliminary and has not been approved.", "The estimated repair time is 4.5 h for 12 units [S1]. The estimate is preliminary and has not been approved.", ["4.5 h", "12 units", "[S1]", "preliminary", "has not been approved"]),
("من الجدير بالذكر أن معدل الأعطال المسجّل بلغ 2.4% خلال سبتمبر 2026 [S2]. هذه قراءة أولية، ولا تثبت أن الإجراء المقترح خفّض الأعطال.", "بلغ معدل الأعطال المسجّل 2.4% خلال سبتمبر 2026 [S2]. هذه قراءة أولية، ولا تثبت أن الإجراء المقترح خفّض الأعطال.", ["2.4%", "سبتمبر 2026", "[S2]", "قراءة أولية", "ولا تثبت"]),
("Here’s the thing: this example shows how to compare two drafts. It does not tell you whether AI wrote either draft.", "This example shows how to compare two drafts. It does not tell you whether AI wrote either draft.", ["It does not tell you whether AI wrote either draft."]),
]
def preserves(before, after, protected):
    numbers = lambda s: Counter(re.findall(r"\d+(?:\.\d+)?%?", s))
    refs = lambda s: Counter(re.findall(r"\[S\d+\]", s))
    return numbers(before) == numbers(after) and refs(before) == refs(after) and all(before.count(p) == after.count(p) and p in after for p in protected)
if __name__ == "__main__":
    for before, after, protected in EXAMPLES:
        assert preserves(before, after, protected)
    mutations = [(0, "4.5 h", "5 h"), (0, "12 units", "12 h"), (0, "[S1]", "[S3]"), (0, "has not been approved", "has been approved"), (1, "قراءة أولية", "قراءة مؤكدة"), (1, "ولا تثبت", "وتثبت"), (2, "It does not tell you whether AI wrote either draft.", "")]
    for index, old, new in mutations:
        before, after, protected = EXAMPLES[index]
        assert not preserves(before, after.replace(old, new), protected)
    print("PASS: 3 synthetic pairs preserve protected tokens; 7 altered fixtures rejected.")
    print("Scope: deterministic fixture checks only; no LLM, semantic, application or runtime quality test.")
