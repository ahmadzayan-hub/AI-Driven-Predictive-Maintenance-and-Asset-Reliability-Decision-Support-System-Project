#!/usr/bin/env python3
"""Check every figure in a deliverable against the register it came from.

    python scripts/figures_check.py --register kpis.csv --value-column Expected \\
        --doc report.pdf --doc deck.pptx [--reference report.pdf] [--json out.json]

Tier 0 of docs/AGENT_TEAM.md: no model, no tokens. Three checks:

1. Coverage: every value in the register appears in the documents, written
   exactly or in a recognised shorter form ($50,430,446 as $50.4 million or
   $50.4M; 219.0 as 219; 26,501 as 26.5k).
2. Sourcing, with --reference: every number in a --doc appears in the
   register or in a reference document, in a compatible unit (a percentage
   is not sourced by a dollar amount). Bare small counts (up to 31) and
   years are ignored, because they are labels far more often than figures;
   "12%" and "$12" are figures. A figure run into a word ("Reactive7988.1",
   from glued table cells) counts. A figure that follows from the sourced
   figures its sentence names (610 staff across 48 stores, 12.7 each) is
   derived; one presented as following from them that does not is wrong.
3. Arithmetic: a calculation written out ("24.4 h − 16.9 h = 7.5 h") must
   hold. A result that holds is a derived figure, sourced by its inputs.

Counts written in English or Arabic words ("five", "twenty-four", "two
hundred and fifty", "خمسة وعشرون", "ثلاثة آلاف") are read like digits. Ratios
("one in five"), fractions, ordinals and a pronoun "one" are not: the
figures-auditor reads the text for those.

Reads .md, .txt, .html, .json, .csv and .tsv (cell by cell), .pdf (with pdftotext) and .pptx (slide
text, alt text and speaker notes). Exits 0 when everything is found, 1
otherwise. Standard library only.
"""

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import zipfile
from html import unescape
from pathlib import Path

# "06:00" is a time of day, not two figures.
CLOCK = re.compile(r"(?<![\d.,:])\d{1,2}:\d{2}(?![\d:])")
NUMBER = re.compile(r"(?<![\w.])[-+−]?\$?\d[\d,]*(?:\.\d+)?%?(?:\s?(?:thousand|million|billion|bn|[MBk]))?(?![\w])")
# A figure run into the word before it, as text extraction does to table
# cells ("Reactive7988.1 y"). Only forms that cannot be part of a name count:
# a decimal or a thousands separator, so "rev37" and "sha256" are left alone,
# and a version such as "v1.0" is not a figure.
GLUED = re.compile(r"(?<=[^\W\d_])(?<!\b[vV])\$?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+)%?(?![\w])")
# A worked calculation written out: "24.4 h − 16.9 h = 7.5 h per record ×
# 862 records × about $2,500 per hour ≈ $16M". Up to three words of unit
# or label may sit between a figure and the next sign.
CALC_TOKEN = re.compile(rf"(?P<num>{NUMBER.pattern})|(?P<rel>[=≈])|(?P<op>[×÷*/+]|(?<=\s)[-x](?=\s))"
                        r"|(?P<word>[^\W\d_][\w'’-]*)|(?P<space>\s+)|(?P<other>.)")


def read_text(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        if not shutil.which("pdftotext"):
            raise RuntimeError("pdftotext is needed to read PDF (install poppler-utils).")
        done = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
        if done.returncode:
            raise RuntimeError(f"pdftotext could not read {path.name}: {done.stderr.strip()}")
        text = done.stdout
    elif suffix == ".pptx":
        parts = []
        with zipfile.ZipFile(path) as archive:
            names = sorted(n for n in archive.namelist()
                           if re.match(r"ppt/(slides|notesSlides)/\w+\d+\.xml$", n))
            for name in names:
                xml = archive.read(name).decode("utf-8", "replace")
                parts += re.findall(r"<a:t>([^<]*)</a:t>", xml)
                parts += re.findall(r'\bdescr="([^"]*)"', xml)
        text = "\n".join(unescape(p) for p in parts)
    elif suffix in (".html", ".htm"):
        raw = path.read_text(encoding="utf-8", errors="replace")
        # Chart drawings are skipped: axis ticks are not figures, and a
        # chart's values are checked in the table that carries them.
        raw = re.sub(r"(?is)<(script|style|svg)[^>]*>.*?</\1>", " ", raw)
        text = unescape(re.sub(r"<[^>]+>", " ", raw))
    elif suffix in (".csv", ".tsv"):
        # Cell by cell: the commas between cells would otherwise run
        # neighbouring numbers together ("862,61014.76").
        with open(path, encoding="utf-8-sig", newline="") as handle:
            rows = csv.reader(handle, delimiter="\t" if suffix == ".tsv" else ",")
            text = "\n".join(" ; ".join(cell for cell in row) for row in rows)
    elif suffix == ".json":
        def strings(node):
            if isinstance(node, str):
                yield node
            elif isinstance(node, (int, float)) and not isinstance(node, bool):
                yield str(node)
            elif isinstance(node, dict):
                for value in node.values():
                    yield from strings(value)
            elif isinstance(node, list):
                for value in node:
                    yield from strings(value)
        text = "\n".join(strings(json.loads(path.read_text(encoding="utf-8"))))
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
    return normalise(text)


# Arabic-Indic and Persian digits, and the Arabic separators, read as figures (ADR 0027).
ARABIC_FIGURES = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٬٫٪", "01234567890123456789,.%")
# An amount in brackets is a negative, as accounts write it: "(1,200)" is -1,200.
ACCOUNTING_NEGATIVE = re.compile(r"\((\$?\d{1,3}(?:,\d{3})+(?:\.\d+)?|\$\d+(?:\.\d+)?)\)")
# Money in any currency is read the way "$" is: "€1,150", "£2,750", "AED 96,000",
# "48,500 AED" and "د.إ 380" all become "$…". Only "$" was read before benchmark E.
CURRENCY_BEFORE = re.compile(r"(?:€|£|\bAED\s?|د\.إ\s?)(?=\d)")
CURRENCY_AFTER = re.compile(r"(?<![\w.$])(\d[\d,]*(?:\.\d+)?)\s?(?:AED\b|د\.إ)")


def money(text):
    """Every currency written as "$", so amounts compare by value and unit."""
    return CURRENCY_BEFORE.sub("$", CURRENCY_AFTER.sub(r"$\1", text))


# A figure the text calls approximate may be rounded further than its digits show.
APPROXIMATE = re.compile(r"(?:\b(?:about|around|roughly|approximately|nearly|almost|some|close to)|~|≈|"
                         r"حوالي|حوالى|نحو|قرابة)\s*(\$?\d[\d,]*(?:\.\d+)?%?(?:\s?(?:thousand|million|billion|bn|[MBk]))?)(?![\w])",
                         re.I)


def normalise(text):
    """One line of text with plain spaces, minus signs and Western digits, as the checks read it."""
    # Time stamps such as "[10.0–15.5 s]" in a clip transcript are not figures.
    text = re.sub(r"\[\d+(?:\.\d+)?\s?[–-]\s?\d+(?:\.\d+)?\s?s\]", " ", text)
    text = money(text.translate(ARABIC_FIGURES))
    text = ACCOUNTING_NEGATIVE.sub(r"-\1", text)
    return " ".join(text.replace("\u00a0", " ").replace("−", "-").split())


# Figures written in words (ADR 2026-10-23-number-words-and-run-to-failure):
# "five", "twenty-four", "two hundred and fifty", "a thousand", "خمسة وعشرون",
# "ثلاثمئة", "ثلاثة آلاف". Ordinals ("second", "third") are not read: they rank
# rather than count, and "second" is also a unit of time. Fractions ("a third",
# "two-thirds", "خمس السكان") and vague plurals ("hundreds of") are not figures.
EN_UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen".split())}
EN_TENS = {w: 10 * i for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split(), 2)}
EN_SCALES = {"thousand": 1e3, "million": 1e6, "billion": 1e9}
# "one" is a pronoun or an idiom far more often than a count.
ONE_BEFORE = {"no", "any", "every", "some", "each", "the", "this", "that", "which", "a", "an", "anyone", "everyone"}
# "the new one is fitted": a pronoun before a verb or a relative.
ONE_AFTER = {"of", "another", "other", "off", "way", "hand", "by", "is", "was", "has", "had", "that", "which",
             "who", "will", "can", "would", "should", "must"}
# "three-phase" keeps its count; "one-off" and "two-thirds" are not counts.
HYPHEN_NOT_COUNT = {"off", "half", "halves", "third", "thirds", "quarter", "quarters", "fifth", "fifths",
                    "sixth", "sixths", "tenth", "tenths", "fold", "way", "on", "to"}


def _ar(word):
    """An Arabic word in one spelling: hamza forms of alef, final yaa and taa marbuta unified."""
    return word.translate(str.maketrans("أإآىة", "ااايه"))


_AR_UNIT_STEMS = [("واحد", "واحده", 1), ("اثنان", "اثنين", 2), ("اثنتان", "اثنتين", 2), ("ثلاثه", "ثلاث", 3),
                  ("اربعه", "اربع", 4), ("خمسه", "خمس", 5), ("سته", "ست", 6), ("سبعه", "سبع", 7),
                  ("ثمانيه", "ثماني", 8), ("ثمان", "ثمان", 8), ("تسعه", "تسع", 9), ("عشره", "عشر", 10)]
AR_WORDS = {"صفر": ("unit", 0)}
for _masc, _fem, _v in _AR_UNIT_STEMS:
    AR_WORDS[_masc] = AR_WORDS[_fem] = ("unit", _v)
for _w in ("احد", "احدي", "اثنا", "اثني", "اثنتا", "اثنتي"):  # only before عشر / عشرة
    AR_WORDS[_w] = ("teen_unit", 1 if _w.startswith("اح") else 2)
for _stem, _v in (("عشر", 20), ("ثلاث", 30), ("اربع", 40), ("خمس", 50), ("ست", 60), ("سبع", 70), ("ثمان", 80),
                  ("تسع", 90)):
    AR_WORDS[_stem + "ون"] = AR_WORDS[_stem + "ين"] = ("ten", _v)
for _w, _v in (("مئه", 100), ("مائه", 100), ("مئتان", 200), ("مئتين", 200), ("مائتان", 200), ("مائتين", 200),
                ("مئتا", 200), ("مائتا", 200)):
    AR_WORDS[_w] = ("hundred", _v)
for _stem, _v in (("ثلاث", 3), ("اربع", 4), ("خمس", 5), ("ست", 6), ("سبع", 7), ("ثمان", 8), ("ثماني", 8), ("تسع", 9)):
    AR_WORDS[_stem + "مئه"] = AR_WORDS[_stem + "مائه"] = ("hundred", _v * 100)
AR_WORDS.update({"الف": ("scale", 1e3), "الفا": ("scale", 1e3), "مليونا": ("scale", 1e6), "الفان": ("scale_n", 2e3), "الفين": ("scale_n", 2e3),
                 "الاف": ("scales", 1e3), "مليون": ("scale", 1e6), "مليونان": ("scale_n", 2e6),
                 "مليونين": ("scale_n", 2e6), "ملايين": ("scales", 1e6)})
# Short feminine forms are also fractions before a definite noun: "خمس السكان" is a fifth.
AR_FRACTION_FORMS = {"ثلاث", "اربع", "خمس", "ست", "سبع", "ثمان", "تسع", "عشر"}
WORD = re.compile(r"[^\W\d_]+")


def _english(atoms):
    """(words used, value, scale) of the longest English number at the start of `atoms`."""
    total = current = 0
    last, best = None, (0, None, None)
    for k, word in enumerate(atoms):
        nxt = atoms[k + 1] if k + 1 < len(atoms) else ""
        if word == "a" and k == 0 and nxt in ("hundred", *EN_SCALES):
            current, last = 1, "unit"
            continue
        if word in EN_UNITS:
            v = EN_UNITS[word]
            if last in (None, "hundred", "scale", "and") or (last == "ten" and 0 < v < 10):
                current += v
                last = "unit"
            else:
                break
        elif word in EN_TENS:
            if last not in (None, "hundred", "scale", "and"):
                break
            current += EN_TENS[word]
            last = "ten"
        elif word == "hundred" and last == "unit" and 0 < current % 100 < 20:
            current = current - current % 100 + current % 100 * 100
            last = "hundred"
        elif word in EN_SCALES and last in ("unit", "ten", "hundred") and current:
            total, current, last = total + current * EN_SCALES[word], 0, "scale"
        elif word == "and" and last in ("hundred", "scale") and (nxt in EN_UNITS or nxt in EN_TENS):
            last = "and"
            continue
        else:
            break
        value = total + current
        scale = EN_SCALES.get(word) if word in ("million", "billion") else None
        best = (k + 1, value / scale if scale else value, scale)
    return best


def _arabic(words):
    """(words used, value, scale) of the longest Arabic number at the start of `words`."""
    total = current = unit = 0
    last, best = None, (0, None, None)
    for k, raw in enumerate(words):
        w, joined = _ar(raw), False
        if w not in AR_WORDS:
            prefixes = r"(?:[وبف]?(?:ال)?)" if k == 0 else r"و"
            m = re.fullmatch(prefixes + r"(.+)", w)
            if not m or m.group(1) not in AR_WORDS:
                break
            joined, w = k > 0, m.group(1)
        kind, v = AR_WORDS[w]
        if kind == "unit" and (k == 0 or (joined and last in ("hundred", "scale"))):
            current, unit, last = current + v, v, "unit"
        elif kind == "teen_unit" and not joined and k == 0:
            current, unit, last = current + v, v, "teen_unit"
            continue
        elif w in ("عشر", "عشره") and not joined and last in ("unit", "teen_unit") and 1 <= unit <= 9:
            current, last = current + 10, "teen"
        elif kind == "ten" and (k == 0 or (joined and (last in ("hundred", "scale") or (last == "unit" and unit < 10)))):
            current, last = current + v, "ten"
        elif kind == "hundred" and not joined and w in ("مئه", "مائه") and last == "unit" and 3 <= unit <= 9:
            current, last = current - unit + unit * 100, "hundred"
        elif kind == "hundred" and (k == 0 or (joined and last == "scale")):
            current, last = current + v, "hundred"
        elif kind == "scale" and k == 0:
            total, last = total + v, "scale"
        elif kind == "scale" and not joined and current and last in ("teen", "ten", "hundred", "unit"):
            total, current, last = total + current * v, 0, "scale"
        elif kind == "scales" and not joined and last == "unit" and 3 <= unit <= 10:
            total, current, last = total + current * v, 0, "scale"
        elif kind == "scale_n" and (k == 0 or joined):
            total, last = total + v, "scale"
        else:
            break
        best = (k + 1, total + current, None)
    return best


def word_figures(text, context=True):
    """[(phrase, value, scale)] for each figure the text writes in words.

    With `context`, a lone "one" that is a pronoun or an idiom ("one of the",
    "a one-off", "no one", "the new one."), a ratio such as "one in five",
    and a short Arabic feminine form that is a fraction ("خمس السكان") are left out.
    """
    words = list(WORD.finditer(text))
    out, i = [], 0
    while i < len(words):
        start = words[i].start()
        english = bool(re.match(r"[a-z]", words[i].group(0), re.I))
        # A run of words joined by spaces (or, in English, hyphens): "two hundred
        # and fifty", "twenty-four", "خمسة وعشرون".
        gap = r"\s+|-" if english else r"\s+"
        run = [words[i]]
        while (i + len(run) < len(words) and len(run) < 12
               and re.fullmatch(gap, text[run[-1].end():words[i + len(run)].start()])):
            run.append(words[i + len(run)])
        if english:
            used, value, scale = _english([w.group(0).lower() for w in run])
        else:
            used, value, scale = _arabic([w.group(0) for w in run])
        if not used:
            i += 1
            continue
        end = run[used - 1].end()
        phrase = text[start:end]
        keep = True
        if context:
            before = text[max(0, start - 30):start]
            after = text[end:end + 40]
            prev = re.findall(r"[^\W\d_]+", before)
            prev = prev[-1].lower() if prev else ""
            nxt = re.match(r"(-|\s+)?([^\W\d_]+)", after)
            joiner, follower = (nxt.group(1) or "", nxt.group(2).lower()) if nxt else ("", "")
            if joiner == "-" and follower in HYPHEN_NOT_COUNT:
                keep = False
            if phrase.lower() == "one" and (prev in ONE_BEFORE or follower in ONE_AFTER
                                            or re.match(r"\s*(?:[.,;:!?)]|$)", after)):
                keep = False
            if (re.match(r"\s+in\s+(?:\d|" + "|".join(EN_UNITS) + "|" + "|".join(EN_TENS) + r")\b", after, re.I)
                    or re.search(r"(?:\d|\b(?:" + "|".join(EN_UNITS) + "|" + "|".join(EN_TENS) + r"))\s+in\s+$",
                                 before, re.I)):
                keep = False  # "one in five" is a ratio, read by the auditor
            if used == 1 and _ar(phrase) in AR_FRACTION_FORMS and re.match(r"\s+ال", _ar(after)):
                keep = False
            if used == 1 and _ar(phrase) in ("واحد", "واحده") and re.fullmatch(r"و?(كل|اي)", _ar(prev)):
                keep = False
        if keep:
            out.append((phrase, value, scale))
        i += used
    return out


def _word_value(token):
    """parse() for a figure written in words: the whole token must be one number."""
    found = word_figures(token, context=False)
    if len(found) == 1 and found[0][0] == token:
        value, scale = found[0][1], found[0][2]
        return (float(value), 0, scale)
    return None


def rounding_unit(token):
    """How far a written figure can be from the value it rounds: half of its
    last significant place. 6,400 is within 50 of its value; 26.5k within 50."""
    parsed = parse(token)
    if parsed is None:
        return 0.0
    number, decimals, scale = parsed
    if decimals:
        unit = 10 ** -decimals
    else:
        digits = str(int(abs(number)))
        unit = 10 ** (len(digits) - len(digits.rstrip("0"))) if digits.strip("0") else 1
    return unit * (scale or 1) / 2


SCALES = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "bn": 1e9, "billion": 1e9, "b": 1e9}


def parse(token):
    """(number as written, decimals shown, scale or None) for a figure such
    as '$50.4 million', '26.5k', '14.1%' or '1,200'. None if not a number."""
    token = token.strip().rstrip(",.")
    match = re.fullmatch(r"[-+−]?\$?(\d[\d,]*(?:\.(\d+))?)%?\s?(thousand|million|billion|bn|[MBkmb])?", token)
    if not match:
        return _word_value(token)
    number = float(match.group(1).replace(",", ""))
    if token.lstrip().startswith(("-", "−")):
        number = -number
    decimals = len(match.group(2) or "")
    scale = SCALES.get((match.group(3) or "").lower()) if match.group(3) else None
    return number, decimals, scale


def same_figure(written, value):
    """True when `written` is `value` as a report may show it: exact,
    rounded to fewer decimals, or abbreviated in thousands or millions."""
    shown = parse(written)
    if shown is None:
        return False
    number, decimals, scale = shown
    # A scale applies only when the text says so ("26.5k", "$50.4 million"):
    # without one, "0" would match anything in thousands. A percentage may
    # be stored as a fraction: 45% is 0.45.
    candidates = [value / (scale or 1)]
    if written.strip().endswith("%"):
        candidates.append(value * 100)
    return any(abs(round(c, decimals) - number) < 1e-9 for c in candidates)


def value_of(text):
    parsed = parse(text)
    if parsed is None:
        return None
    number, _, scale = parsed
    return number * (scale or 1)


def variants(value):
    """Exact forms of a register value, tried before numeric matching."""
    v = str(value).strip()
    out = {v}
    parsed = parse(v)
    if parsed and float(parsed[0]).is_integer() and parsed[1]:
        whole = f"{int(parsed[0]):,}"
        out.add(("$" + whole) if v.startswith("$") else whole + ("%" if v.endswith("%") else ""))
    return out


def found_in(text, value, numbers=None):
    """How a register value appears in a text: an exact form, or a written
    figure that is the same number rounded or abbreviated."""
    text = CLOCK.sub(" ", text)
    for form in variants(value):
        # Not "5" inside "5.2", nor "1,656" inside "1,656.2".
        if re.search(r"(?<![\d.,])" + re.escape(form) + r"(?![\d]|[.,]\d)", text):
            return form
    target = value_of(value)
    if target is None:
        return None
    percent = str(value).strip().endswith("%")
    for token in (numbers if numbers is not None else numbers_in(text, keep_small=True)):
        if percent != token.endswith("%"):
            continue
        if not re.search(r"\d", token):
            # A count in words is a whole number: "five" is 5, never a rounded 4.9.
            shown = parse(token)
            if shown and (abs(value_of(token) - target) < 1e-9 or (shown[2] and same_figure(token, target))):
                return f"{token} (in words)"
            continue
        if same_figure(token, target):
            return f"{token} (rounded or abbreviated)"
    return None


def _evaluate(terms, ops):
    """terms[0] ops[0] terms[1] …, with × and ÷ before + and −."""
    values, pending = [terms[0]], []
    for op, term in zip(ops, terms[1:]):
        if op in "×x*":
            values[-1] *= term
        elif op in "÷/":
            values[-1] = values[-1] / term if term else float("nan")
        else:
            pending.append(op)
            values.append(term)
    total = values[0]
    for op, value in zip(pending, values[1:]):
        total = total + value if op == "+" else total - value
    return total


def calculations_in(text):
    """Worked calculations in a text: [{"shown", "result", "written", "holds"}].

    "=" holds when the result is the computed value as written, rounded to the
    decimals shown (or within 0.5%, for inputs that were rounded themselves);
    "≈" holds within 5%. A result that holds is a derived figure: sourced by
    its inputs, which are checked like any other number.
    """
    found, terms, ops, words, start = [], [], [], 0, None

    def reset():
        nonlocal terms, ops, words, start
        terms, ops, words, start = [], [], 0, None

    tokens = list(CALC_TOKEN.finditer(text))
    i = 0
    while i < len(tokens):
        kind, token = tokens[i].lastgroup, tokens[i]
        if kind == "num":
            value = value_of(token.group(0))
            if value is None or (terms and len(ops) < len(terms)):
                reset()
                if value is not None:
                    terms, start = [value], token.start()
            else:
                terms.append(value)
                start = token.start() if start is None else start
            words = 0
        elif kind == "op" and terms and len(ops) == len(terms) - 1:
            ops.append(token.group(0))
            words = 0
        elif kind == "rel" and len(terms) >= 2 and len(ops) == len(terms) - 1:
            nxt = next((t for t in tokens[i + 1:] if t.lastgroup != "space"), None)
            if nxt is not None and nxt.lastgroup == "num" and value_of(nxt.group(0)) is not None:
                computed = _evaluate(terms, ops)
                written = nxt.group(0).strip().rstrip(",.")
                shown = value_of(written)
                tolerance = 0.05 if token.group(0) == "≈" else 0.005
                holds = (same_figure(written, computed)
                         or (computed and abs(shown - computed) <= tolerance * abs(computed)))
                found.append({"shown": text[start:nxt.end()], "result": written,
                              "computed": round(computed, 6), "holds": bool(holds)})
                # The result may start the next step: "… = 7.5 h × 862 …".
                terms, ops, words, start = [shown], [], 0, nxt.start()
                i = tokens.index(nxt) + 1
                continue
            reset()
        elif kind == "word" and terms:
            words += 1
            if words > 3:
                reset()
        elif kind != "space":
            reset()
        i += 1
    return found


def numbers_in(text, keep_small=False):
    """Figures in a text, leaving out small counts and years."""
    seen = set()
    text = CLOCK.sub(" ", text)
    matches = list(NUMBER.finditer(text))
    glued = list(GLUED.finditer(text))
    # A glued figure replaces any shorter number found inside it.
    matches = [m for m in matches if not any(g.start() <= m.start() < g.end() for g in glued)] + glued
    for match in matches:
        token = match.group(0).strip().rstrip(",.")
        parsed = parse(token)
        if parsed is None:
            continue
        # Only a bare number can be a label: "12%" and "$12" are figures (ADR 0027).
        if not keep_small and re.fullmatch(r"\d{1,2}", token) and parsed[0] <= 31:
            continue
        if not keep_small and re.fullmatch(r"(19|20)\d{2}", token):
            continue
        seen.add(token)
    # Figures in words follow the same rules: "five" is a small count, as "5" is.
    for phrase, value, scale in word_figures(text):
        if not keep_small and scale is None and (value <= 31 or 1900 <= value <= 2099):
            continue
        seen.add(phrase)
    return sorted(seen)


def unit_of(token):
    """'%', '$' or '' (a bare number, which may stand for either)."""
    token = token.strip().lstrip("+-−")
    return "%" if token.endswith("%") else "$" if token.startswith("$") else ""


def sourced_by(token, pool):
    """True when a pool entry (value, unit) is this figure, in a compatible unit."""
    unit = unit_of(token)
    return any(same_figure(token, value) for value, other in pool if not (unit and other and unit != other))


# Words that present a figure as computed from others, by the kind of sum.
CUES = {
    "ratio": re.compile(r"\b(each|per|every|average|averages|mean|apiece)\b|لكل|متوسط", re.I),
    "change": re.compile(r"\b(growth|grew|grow|grows|rise|rose|risen|up|down|fell|fall|gain|drop|dropped|change|"
                         r"increase[sd]?|decrease[sd]?|declined?|reduction|reduced|fewer)\b|نمو|ارتفع|انخفض|تراجع|زيادة", re.I),
    "share": re.compile(r"\b(share|of all|proportion|percent of)\b|نسبة|حصة", re.I),
}
# Which way a change went decides its base: a fall is measured against the
# larger, earlier figure and a rise against the smaller. Prose writes the size
# of a fall ("a fall of 12.0%"), so the direction comes from the words.
FALL = re.compile(r"\b(fell|falls?|fallen|drop(s|ped)?|down|declin(e|ed|es|ing)|decreas(e|ed|es|ing)|"
                  r"reduc(tion|ed)|fewer|lower)\b|انخفض|تراجع", re.I)
RISE = re.compile(r"\b(rose|rises?|risen|gr[eo]w(s|th)?|grown|up|gain(s|ed)?|increas(e|ed|es|ing)|more|higher)\b|ارتفع|زيادة|نمو", re.I)
# "That is growth of 13.4%": the figures are in the sentence before.
BACK_REFERENCE = re.compile(r"^(that|this|it|these|those|which)\b|^(هذا|هذه|وهذا|وهذه)", re.I)
SENTENCES = re.compile(r"(?<=[.!?؟])\s+")
# A figure this close to a derivation of its sentence's own inputs is a slip
# in that derivation, not an unrelated number (chosen on benchmark A, ADR 0027).
SLIP_FACTOR = 2.0
# "A decline of 3.4 percentage points": the gap between two percentages,
# never their relative change.
POINTS = r"\s*(?:percentage[ -]points?|points?|pp\b|نقطة مئوية|نقاط مئوية)"
MAX_SENTENCE, MAX_FIGURES = 300, 6


def _derivations(a, b, direction=None):
    low, high = sorted((a, b))
    if direction == "fall" and high:
        change = [(high - low) / high, (low - high) / high, high - low, low - high]
    elif direction == "rise" and low:
        change = [(high - low) / low, high - low]
    else:
        change = [x for x in (a / b - 1 if b else None, b / a - 1 if a else None, a - b, b - a) if x is not None]
    return {"ratio": [x for x in (a / b if b else None, b / a if a else None) if x is not None],
            "change": change,
            "share": [x for x in (a / b if b else None, b / a if a else None) if x is not None],
            "other": [a * b, a + b]}


def _as_written(token, value):
    """A computed value in the token's terms: a fraction read as a percentage."""
    return value * 100 if unit_of(token) == "%" and abs(value) < 1.5 else value


def _close(token, value):
    """Within the token's own rounding: with no working shown, there is no
    rounded input to allow for."""
    written, unit = value_of(token), rounding_unit(token)
    return any(abs(written - c) <= unit + 1e-9 for c in {value, _as_written(token, value)})


def _distinct(values):
    """One input per quantity: 75.2% and 0.752 are the same figure written twice."""
    out = []
    for v in values:
        if v is not None and not any(abs(v - o) < 1e-9 or abs(v - o * 100) < 1e-6 or abs(v * 100 - o) < 1e-6
                                     for o in out):
            out.append(v)
    return out


def _words(text):
    return {w.rstrip("s") for w in re.findall(r"[^\W\d_]{4,}", text.lower())}


def implied(token, sentence, previous, pool, register):
    """For a figure not in the pool: "derived" when it follows from the
    sourced figures its sentence names (or the register rows it names by
    every word of their label); ("wrong", computed) when the sentence
    presents it as computed from two or more of its figures and it is a
    slip from one of their derivations; None otherwise."""
    # Prose only: a table read as one long "sentence" holds dozens of figures,
    # and any two of them would derive something.
    if len(sentence) > MAX_SENTENCE or len(numbers_in(sentence)) > MAX_FIGURES:
        return None
    body = re.sub(r"^(?:\[\w+\]|[^\w])+", "", sentence)
    explicit = [value_of(t) for t in numbers_in(sentence) if t != token and sourced_by(t, pool)]
    if len(explicit) < 2 and previous and BACK_REFERENCE.match(body):
        explicit += [value_of(t) for t in numbers_in(previous) if sourced_by(t, pool)]
    words = _words(sentence)
    named = [value_of(r["value"]) for r in register
             if _words(re.sub(r"\(.*?\)", " ", r["label"])) and _words(re.sub(r"\(.*?\)", " ", r["label"])) <= words]
    inputs = _distinct(explicit + named)
    pairs = [(a, b) for i, a in enumerate(inputs) for b in inputs[i + 1:]]
    falls, rises = bool(FALL.search(sentence)), bool(RISE.search(sentence))
    direction = "fall" if falls and not rises else "rise" if rises and not falls else None
    percents = _distinct([value_of(t) for t in numbers_in(sentence)
                          if t != token and unit_of(t) == "%" and sourced_by(t, pool)])
    if len(percents) >= 2 and re.search(re.escape(token) + POINTS, sentence, re.I):
        gaps = [abs(a - b) for i, a in enumerate(percents) for b in percents[i + 1:]]
        if any(_close(token, g) for g in gaps):
            return "derived"
        # The relative change written as points is the classic slip.
        relative = [abs(a - b) / base * 100 for i, a in enumerate(percents) for b in percents[i + 1:]
                    for base in (a, b) if base]
        if any(_close(token, r) for r in relative):
            return ("wrong", min(gaps, key=lambda g: abs(g - value_of(token))))
        return None
    if any(_close(token, c) for a, b in pairs for cs in _derivations(a, b, direction).values() for c in cs):
        return "derived"
    explicit = _distinct(explicit)
    families = [name for name, cue in CUES.items() if cue.search(sentence)]
    if len(explicit) < 2 or not families:
        return None
    written = value_of(token)
    candidates = [_as_written(token, c) for i, a in enumerate(explicit) for b in explicit[i + 1:]
                  for f in families for c in _derivations(a, b, direction)[f]]
    candidates = [c for c in candidates if c and (c > 0) == (written > 0)]
    if not candidates or not written:
        return None
    best = min(candidates, key=lambda c: max(written / c, c / written))
    return ("wrong", best) if max(written / best, best / written) <= SLIP_FACTOR else None


def load_register(path, value_column, label_columns):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or value_column not in rows[0]:
        raise ValueError(f"{path} has no column “{value_column}”.")
    labels = [c for c in label_columns if c in rows[0]] or [c for c in rows[0] if c != value_column][:2]
    return [{"label": " · ".join(r[c] for c in labels if r.get(c)), "value": r[value_column]} for r in rows]


def check(register, docs, references=(), sourcing_only=False):
    register = [{**r, "value": money(str(r["value"]).strip())} for r in register]
    texts = {str(d): read_text(d) for d in docs}
    combined = " ".join(texts.values())
    written = numbers_in(combined, keep_small=True)
    coverage = []
    for row in register:
        form = found_in(combined, row["value"], written)
        coverage.append({**row, "found": form is not None, "as": form})
    unsourced, derived, wrong = [], [], []
    for name, text in texts.items():
        for calc in calculations_in(text):
            (derived if calc["holds"] else wrong).append({"doc": Path(name).name, **calc})
    if references or sourcing_only:
        pool_text = " ".join(read_text(r) for r in references)
        pool = {(value_of(t), unit_of(t)) for t in numbers_in(pool_text, keep_small=True)}
        pool |= {(value_of(r["value"]), unit_of(r["value"])) for r in register}
        pool = {(v, u) for v, u in pool if v is not None}
        for name, text in texts.items():
            doc = Path(name).name
            # A result whose working is shown is sourced by its inputs.
            known = pool | {(value_of(d["result"]), unit_of(d["result"])) for d in derived if d["doc"] == doc}
            approximate = {m.group(1).strip().rstrip(",.") for m in APPROXIMATE.finditer(text)}
            sentences = SENTENCES.split(text)
            for token in numbers_in(text):
                if sourced_by(token, known):
                    continue
                if token in approximate:
                    written, unit = value_of(token), rounding_unit(token)
                    if any(abs(written - v) <= unit + 1e-9 for v, _ in pool):
                        continue
                where = next((i for i, s in enumerate(sentences) if token in numbers_in(s)), None)
                verdict = (implied(token, sentences[where], sentences[where - 1] if where else "", pool, register)
                           if where is not None else None)
                if verdict == "derived":
                    continue
                if verdict:
                    wrong.append({"doc": doc, "shown": sentences[where][:160], "result": token,
                                  "computed": round(verdict[1], 6), "holds": False, "implied": True})
                    continue
                unsourced.append({"doc": doc, "number": token})
    missing = [c for c in coverage if not c["found"]]
    return {"register_values": len(register), "found": len(register) - len(missing),
            "missing": [] if sourcing_only else missing, "unsourced": unsourced, "coverage": coverage,
            "derived": derived, "wrong_arithmetic": wrong,
            "passed": (sourcing_only or not missing) and not unsourced and not wrong}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--register", required=True, help="CSV of figures the deliverable must carry")
    parser.add_argument("--value-column", default="Expected")
    parser.add_argument("--label-columns", default="Check,Filter")
    parser.add_argument("--doc", action="append", required=True, help="a document to check (repeatable)")
    parser.add_argument("--reference", action="append", default=[],
                        help="a document whose numbers count as sourced (repeatable)")
    parser.add_argument("--sourcing-only", action="store_true",
                        help="check only that every number in the documents is sourced; a dashboard or "
                             "a deck shows a chosen subset, so missing register values are not failures")
    parser.add_argument("--json", help="also write the full result here")
    args = parser.parse_args(argv)
    try:
        register = load_register(args.register, args.value_column, args.label_columns.split(","))
        result = check(register, args.doc, args.reference, args.sourcing_only)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"figures_check: {error}", file=sys.stderr)
        return 2
    if args.json:
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{result['found']}/{result['register_values']} register values found")
    for item in result["missing"]:
        print(f"  MISSING  {item['label']}: {item['value']}")
    if args.reference or args.sourcing_only:
        print(f"{len(result['unsourced'])} number(s) in the documents not found in the register or references")
        for item in result["unsourced"][:50]:
            print(f"  UNSOURCED  {item['doc']}: {item['number']}")
    if result["derived"] or result["wrong_arithmetic"]:
        print(f"{len(result['derived'])} worked calculation(s) hold, {len(result['wrong_arithmetic'])} do not")
        for item in result["wrong_arithmetic"][:20]:
            print(f"  ARITHMETIC  {item['doc']}: “{item['shown']}” computes to {item['computed']:,}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
