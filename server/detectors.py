"""Governance detectors: the checks that find what a dataset's own
documentation does not admit.

A profiler reports what a dataset *contains* - row counts, types, missing
cells. These detectors report what it **cannot support**: a key that does
not identify anything, a rate whose denominator changes under it, an
input that already contains the answer. Those are the findings that
change a conclusion, and they are exactly the ones a supplied data
dictionary tends to omit, because a dictionary documents intent and
these measure behaviour.

Every detector is a pure function of (columns, rows) returning findings
in one shape, so a stage can turn them into claims with calculations
attached and the validator can audit them like any other claim. None of
them knows anything about maintenance, or about any particular dataset:
each looks for a *structural* property, which is why they transfer to a
file nobody has seen.

Each is deliberately conservative. A detector that cries wolf on a sound
dataset is worse than one that stays quiet, because the whole value here
is that a finding means something. Thresholds are named constants and
every finding carries the numbers it fired on, so a reader can disagree
with the threshold rather than with the verdict.
"""

from collections import Counter, defaultdict

# A candidate entity key repeats, but not endlessly: one value per row is
# a row id, and a handful of values is a dimension, not an entity.
KEY_MIN_DISTINCT, KEY_MAX_DISTINCT_SHARE = 10, 0.5
# Names that assert the column identifies something. The detector tests
# whether a column lives up to the claim its own name makes, so the name
# is the thing under test rather than a shortcut around the analysis.
IDENTIFIER_SUFFIXES = ("_id", "_key", "_code", "_no", "_num", "_number", "_ref", "_serial")
IDENTIFIER_NAMES = ("id", "key", "code", "identifier")
# Leakage: a predictor that separates an outcome this well is not a
# predictor, it is the outcome under another name.
LEAKAGE_PURITY = 0.999
# A rate column is a placeholder for a subgroup when it never varies
# there, and that subgroup is a real share of the data.
PLACEHOLDER_MIN_SHARE = 0.05
# A weighted KPI and a row average this far apart tell different stories.
RATE_GAP_POINTS = 2.0
# Period buckets differing by more than this are not comparable as totals.
PERIOD_IMBALANCE = 0.25
# A derived total must reconcile within this to count as an identity.
IDENTITY_TOLERANCE = 0.01
# ... and the sums must differ by at least this share to be worth saying,
# but not by so much that the columns were never a total and its parts.
IDENTITY_MIN_SHARE, IDENTITY_MAX_SHARE = 0.02, 0.5
# Rows sampled to rule a candidate pair out before the full pass.
SAMPLE_ROWS = 25
# A split whose smaller side is this thin proves nothing: with a handful
# of rows on one side, almost any column looks pure by accident.
SPLIT_MIN_MINORITY_SHARE, SPLIT_MIN_MINORITY_ROWS = 0.02, 30
# Distinct values listed when showing a column's shape.
MAX_SHAPE_VALUES = 6


# Units and currencies say how a quantity is measured, not what it is.
# Two columns sharing only "hours" or "usd" are not a total and its
# parts; two sharing "cost" may be.
UNIT_TOKENS = {"hours", "hrs", "hour", "days", "day", "years", "year", "usd", "eur", "gbp",
               "aed", "kwh", "kw", "mwh", "pct", "percent", "rate", "ratio", "score",
               "index", "count", "num", "number", "total", "avg", "mean", "per", "c", "s",
               "mm", "bar", "kg", "km", "m", "min", "sec", "qty"}


def _tokens(name):
    """A column name's subject words, for judging whether two names are
    about the same thing. Units are dropped: they describe measurement,
    not subject, so sharing one proves nothing."""
    parts = {t for t in name.lower().replace("-", "_").split("_") if t}
    return parts - UNIT_TOKENS


def _num(value):
    """The value as a float, or None when it is not a number."""
    try:
        return float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError, AttributeError):
        return None


def _numeric_columns(columns, rows, share=0.9):
    """Columns where at least `share` of the values parse as numbers."""
    out = []
    for c in columns:
        parsed = sum(1 for r in rows if _num(r.get(c)) is not None)
        if rows and parsed >= len(rows) * share:
            out.append(c)
    return out


def _categorical_columns(columns, rows, max_distinct=40):
    """Columns with few enough distinct values to group by."""
    return [c for c in columns
            if 2 <= len({str(r.get(c)) for r in rows}) <= max_distinct]


def _finding(detector, severity, headline, detail, columns, numbers):
    return {"detector": detector, "severity": severity, "headline": headline,
            "detail": detail, "columns": list(columns), "numbers": dict(numbers)}


def identity_collapse(columns, rows):
    """A column named like an entity key that does not identify an entity.

    The test is not "are there duplicates" - a panel repeats its keys by
    design. It is whether the attributes belonging to the entity stay
    still inside one key. A real asset keeps its class and its site; if
    every value of the key mixes several, the key is a bucket label and
    any per-entity history built on it is fiction.
    """
    findings = []
    if not rows:
        return findings
    numeric = set(_numeric_columns(columns, rows))
    for key in columns:
        low = key.lower()
        if not (low.endswith(IDENTIFIER_SUFFIXES) or low in IDENTIFIER_NAMES):
            continue
        values = [str(r.get(key)) for r in rows]
        distinct = set(values)
        # Below the band it is a dimension; at one value per row it is a
        # row id, which identifies the row and claims nothing more.
        if not (KEY_MIN_DISTINCT <= len(distinct) <= len(rows) * KEY_MAX_DISTINCT_SHARE):
            continue
        grouped = defaultdict(list)
        for row, value in zip(rows, values):
            grouped[value].append(row)

        attributes = [c for c in columns
                      if c != key and c not in numeric
                      and 2 <= len({str(r.get(c)) for r in rows}) <= 40]
        if not attributes:
            continue
        unstable = [c for c in attributes
                    if all(len({str(r.get(c)) for r in g}) > 1 for g in grouped.values())]
        if len(unstable) < 2:
            continue

        # What the key *does* line up with one to one, which is what it
        # really labels.
        aligned = [c for c in columns
                   if c != key
                   and all(len({str(r.get(c)) for r in g}) == 1 for g in grouped.values())]
        detail = (f"Each of the {len(distinct)} values of {key} mixes more than one value of "
                  + ", ".join(unstable[:4])
                  + (f" and {len(unstable) - 4} more" if len(unstable) > 4 else "") + ".")
        if aligned:
            detail += (f" It lines up one to one with {', '.join(aligned[:3])}, so it labels "
                       f"that, not an entity.")
        findings.append(_finding(
            "identity_collapse", "high",
            f"{key} does not identify an entity",
            detail + " Per-entity history, trends and drill-through built on it are not "
                     "supported by this data.",
            [key] + unstable[:4],
            {"distinct_keys": len(distinct), "unstable_attributes": len(unstable),
             "rows": len(rows)}))
    return findings


def target_leakage(columns, rows):
    """Columns that all encode one split of the data.

    When a set of columns is driven by a single underlying switch - here
    a record either had a failure or did not - every one of them predicts
    every other perfectly. Reported pair by pair that is dozens of
    findings saying one thing, so the split is the unit of reporting, not
    the pair: one finding naming the columns that share it and the
    cleanest column to explain it by.

    A model handed any member of the set to predict another scores
    beautifully and has learned nothing, so this finding is worth more
    than the model it invalidates.
    """
    if not rows:
        return []
    # Group numeric columns by the exact split their sign makes, so
    # columns driven by one switch collapse into one entry.
    splits = defaultdict(list)
    for column in _numeric_columns(columns, rows):
        signs = tuple((_num(r.get(column)) or 0) > 0 for r in rows)
        if len(set(signs)) > 1:
            splits[signs].append(column)

    findings = []
    floor = max(SPLIT_MIN_MINORITY_ROWS, len(rows) * SPLIT_MIN_MINORITY_SHARE)
    for signs, outcomes in splits.items():
        if min(sum(signs), len(signs) - sum(signs)) < floor:
            continue
        predictors = []
        for predictor in _categorical_columns(columns, rows):
            if predictor in outcomes:
                continue
            groups = defaultdict(list)
            for row, sign in zip(rows, signs):
                groups[str(row.get(predictor))].append(sign)
            if len(groups) < 2:
                continue
            pure = sum(len(g) for g in groups.values()
                       if sum(g) / len(g) >= LEAKAGE_PURITY
                       or sum(g) / len(g) <= 1 - LEAKAGE_PURITY)
            if pure / len(rows) >= LEAKAGE_PURITY:
                predictors.append((len(groups), predictor))
        if not predictors or len(outcomes) + len(predictors) < 2:
            continue

        # The fewest groups explains the split most plainly on a slide.
        predictors.sort()
        best = predictors[0][1]
        counts = sorted(Counter(str(r.get(best)) for r in rows).items())
        shape = ", ".join(f"{k}: {v}" for k, v in counts[:MAX_SHAPE_VALUES])
        if len(counts) > MAX_SHAPE_VALUES:
            shape += f" and {len(counts) - MAX_SHAPE_VALUES} more values"
        positive = sum(signs)
        involved = [best] + [p for _, p in predictors[1:]] + outcomes
        findings.append(_finding(
            "target_leakage", "high",
            f"{len(involved)} columns encode one split of the data",
            f"{positive:,} of {len(rows):,} rows fall one side of a single split, and "
            f"{len(involved)} columns record it: {', '.join(involved[:6])}"
            + (f" and {len(involved) - 6} more" if len(involved) > 6 else "")
            + f". {best} states it most plainly ({shape}). Predicting any of these from "
              f"another restates the split rather than learning anything, so a model built "
              f"across it will look near-perfect and mean nothing. Model inside one side of "
              f"the split, and report the base rate there.",
            involved[:8],
            {"columns_involved": len(involved), "positive_rows": positive,
             "rows": len(rows), "explained_by": best}))
    return findings


def placeholder_rates(columns, rows):
    """A rate column that is a constant filler for a whole subgroup.

    When a share of the rows carry a fixed rate because the measure does
    not apply to them, the column's row average is not the population's
    rate - it is diluted by rows that were never measured. This is the
    commonest way a correct-looking KPI misleads.
    """
    findings = []
    if not rows:
        return findings
    rate_columns = [c for c in _numeric_columns(columns, rows)
                    if all(0 <= (_num(r.get(c)) or 0) <= 1 for r in rows)
                    and len({_num(r.get(c)) for r in rows}) > 2]
    categorical = _categorical_columns(columns, rows, max_distinct=12)
    for rate in rate_columns:
        for group_col in categorical:
            # Grouping a column by itself makes every group constant by
            # construction, which would fire on any rate at all.
            if group_col == rate:
                continue
            groups = defaultdict(list)
            for row in rows:
                groups[str(row.get(group_col))].append(_num(row.get(rate)) or 0)
            constant = {k: v for k, v in groups.items()
                        if len(set(v)) == 1 and len(v) >= len(rows) * PLACEHOLDER_MIN_SHARE}
            if not constant or len(constant) == len(groups):
                continue
            measured = [v for k, g in groups.items() if k not in constant for v in g]
            if not measured:
                continue
            mean_all = sum((_num(r.get(rate)) or 0) for r in rows) / len(rows) * 100
            mean_measured = sum(measured) / len(measured) * 100
            gap = abs(mean_all - mean_measured)
            if gap < RATE_GAP_POINTS:
                continue
            filled = sum(len(v) for v in constant.values())
            names = ", ".join(f"{k} ({len(groups[k])} rows, all {constant[k][0]:g})"
                              for k in list(constant)[:3])
            findings.append(_finding(
                "placeholder_rates", "high",
                f"{rate} is a placeholder for part of the data",
                f"{filled} of {len(rows)} rows hold one fixed value of {rate}, grouped by "
                f"{group_col}: {names}. Averaging the column over every row gives "
                f"{mean_all:.1f}%, against {mean_measured:.1f}% over the rows where it varies, "
                f"a gap of {gap:.1f} points. Report the rate over the population it was "
                f"measured on, and say which that is.",
                [rate, group_col],
                {"placeholder_rows": filled, "rows": len(rows),
                 "mean_all_pct": round(mean_all, 2),
                 "mean_measured_pct": round(mean_measured, 2),
                 "gap_points": round(gap, 2)}))
            break
    return findings


def scale_mislabelled(columns, rows):
    """A column whose name promises a scale its values do not use."""
    findings = []
    for column in columns:
        low = column.lower()
        if not (low.endswith("_pct") or "percent" in low):
            continue
        values = [v for v in (_num(r.get(column)) for r in rows) if v is not None]
        if not values or max(values) > 1.0 or min(values) < 0.0:
            continue
        findings.append(_finding(
            "scale_mislabelled", "medium",
            f"{column} is a 0 to 1 fraction, not a percentage",
            f"Values run {min(values):.3f} to {max(values):.3f}. The name says percent; the "
            f"column is a fraction. Multiplying by 100 twice, or not at all, is the usual "
            f"consequence.",
            [column], {"min": round(min(values), 4), "max": round(max(values), 4)}))
    return findings


def broken_identity(columns, rows):
    """A total that does not equal the parts it appears to be made of.

    Reports the first pair it finds, because one worked example makes the
    point and a list of near-misses does not.
    """
    numeric = _numeric_columns(columns, rows)
    for total in numeric:
        # Only columns whose names say they measure the same thing are
        # candidate parts. Without this the search pairs quantities that
        # were never meant to add up, and reports that they do not.
        parts = [c for c in numeric if c != total and _tokens(total) & _tokens(c)]
        for i, first in enumerate(parts):
            for second in parts[i + 1:]:
                # Every row must be off for this to be a finding, so a
                # single reconciling row in a small sample rules the pair
                # out. Without this the search is quadratic in the
                # numeric columns times the row count.
                if any(abs((_num(r.get(total)) or 0)
                           - ((_num(r.get(first)) or 0) + (_num(r.get(second)) or 0)))
                       <= IDENTITY_TOLERANCE for r in rows[:SAMPLE_ROWS]):
                    continue
                residuals, off = [], 0
                for row in rows:
                    t = _num(row.get(total))
                    a, b = _num(row.get(first)), _num(row.get(second))
                    if None in (t, a, b):
                        continue
                    residual = t - (a + b)
                    residuals.append(residual)
                    if abs(residual) > IDENTITY_TOLERANCE:
                        off += 1
                if not residuals or off < len(residuals):
                    continue
                total_sum = sum(_num(r.get(total)) or 0 for r in rows)
                part_sum = sum((_num(r.get(first)) or 0) + (_num(r.get(second)) or 0)
                               for r in rows)
                # A total exceeds the parts it is made of. Where it does
                # not, the columns were related by something other than
                # addition and "it is not a + b" says nothing.
                if total_sum <= 0 or part_sum > total_sum:
                    continue
                share = (total_sum - part_sum) / total_sum
                # Too close and the gap is rounding; too far and these
                # were never a total and its components.
                if not IDENTITY_MIN_SHARE <= share <= IDENTITY_MAX_SHARE:
                    continue
                return [_finding(
                    "broken_identity", "medium",
                    f"{total} is not {first} plus {second}",
                    f"All {off} rows carry a residual, {sum(residuals):,.0f} in total, which is "
                    f"{share:.1%} of {total}. The columns do not form an accounting identity, "
                    f"so do not present them as one.",
                    [total, first, second],
                    {"rows_off": off, "residual_total": round(sum(residuals), 2),
                     "share_of_total": round(share, 4)})]
    return []


def uneven_periods(columns, rows, date_column=None):
    """Period buckets holding materially different numbers of records.

    A total over such periods moves with the record count, so a falling
    total can mean nothing at all. The per-record figure is the one that
    compares.
    """
    findings = []
    candidates = ([date_column] if date_column else
                  [c for c in columns if "date" in c.lower() or "period" in c.lower()])
    for column in [c for c in candidates if c in columns]:
        buckets = Counter(str(r.get(column))[:4] for r in rows)
        if len(buckets) < 2:
            continue
        counts = sorted(buckets.values())
        if counts[-1] == 0:
            continue
        imbalance = (counts[-1] - counts[0]) / counts[-1]
        if imbalance < PERIOD_IMBALANCE:
            continue
        shape = ", ".join(f"{k}: {v:,}" for k, v in sorted(buckets.items()))
        findings.append(_finding(
            "uneven_periods", "medium",
            f"Periods in {column} hold unequal numbers of records",
            f"{shape}. The smallest holds {imbalance:.0%} fewer records than the largest, so a "
            f"total by period moves with the record count. Compare per record.",
            [column], {"periods": len(buckets), "imbalance": round(imbalance, 4),
                       "smallest": counts[0], "largest": counts[-1]}))
    return findings


DETECTORS = (identity_collapse, target_leakage, placeholder_rates,
             scale_mislabelled, broken_identity, uneven_periods)
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def run_all(columns, rows, date_column=None):
    """Every detector, most severe first. The Governance agent's body."""
    findings = []
    for detector in DETECTORS:
        if detector is uneven_periods:
            findings += detector(columns, rows, date_column)
        else:
            findings += detector(columns, rows)
    findings.sort(key=lambda f: SEVERITY_ORDER.get(f["severity"], 3))
    return findings
