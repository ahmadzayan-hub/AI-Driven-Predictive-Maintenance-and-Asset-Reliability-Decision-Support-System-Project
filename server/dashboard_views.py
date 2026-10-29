"""A saved dashboard view per owner and dataset (ADR 2026-10-27-interactive-dashboard).

The dashboard keeps everything a reader chose in the address (ADR 0032):
filters, a period, a measure range, the breakdown, the second measure, the
order and the page. Saving a view stores that address and page on the
server, keyed by the dataset the run analysed, so the next run over the
same dataset opens the way the reader left it. The address is validated
against the dashboard's own keys and bounded; nothing in it is a row of
the data.
"""
from urllib.parse import parse_qsl, urlencode

PAGES = ("overview", "breakdown", "trend", "distribution", "relationship", "records")
PLAIN_KEYS = {"from", "to", "lo", "hi", "hiop", "by", "per", "vs", "sort", "desc", "o"}
MAX_QUERY_CHARS = 2000
MAX_PAIRS = 60
MAX_VALUE_CHARS = 200


class ViewError(ValueError):
    def __init__(self, en, ar):
        super().__init__(en)
        self.en, self.ar = en, ar

    def detail(self, language):
        return self.ar if language == "ar" else self.en


def dataset_key(run):
    """The dataset a run reads: its stored dataset, else its name."""
    if run.get("dataset_id"):
        return "dataset:" + str(run["dataset_id"])
    return "name:" + str(run.get("dataset_name") or "")


def validate(page, query):
    """The page and the address query in their canonical form, or a ViewError."""
    if page not in PAGES:
        raise ViewError("The page is not one of the dashboard's pages.",
                        "الصفحة ليست من صفحات لوحة المعلومات.")
    query = str(query or "")
    if len(query) > MAX_QUERY_CHARS:
        raise ViewError(f"The view is longer than {MAX_QUERY_CHARS} characters.",
                        f"العرض أطول من {MAX_QUERY_CHARS} حرفاً.")
    pairs = parse_qsl(query, keep_blank_values=True)
    if len(pairs) > MAX_PAIRS:
        raise ViewError(f"The view has more than {MAX_PAIRS} settings.",
                        f"يحتوي العرض على أكثر من {MAX_PAIRS} إعداداً.")
    for key, value in pairs:
        if not (key in PLAIN_KEYS or (key.startswith("f.") and len(key) > 2)):
            raise ViewError(f"“{key}” is not a dashboard setting.",
                            f"«{key}» ليس إعداداً في لوحة المعلومات.")
        if len(value) > MAX_VALUE_CHARS:
            raise ViewError(f"The value of “{key}” is longer than {MAX_VALUE_CHARS} characters.",
                            f"قيمة «{key}» أطول من {MAX_VALUE_CHARS} حرفاً.")
    return page, urlencode(pairs)


def present(row):
    """What the API returns for a stored view."""
    if row is None:
        return None
    return {"page": row["page"], "query": row["query"], "run_id": row["run_id"],
            "updated_at": row["updated_at"]}
