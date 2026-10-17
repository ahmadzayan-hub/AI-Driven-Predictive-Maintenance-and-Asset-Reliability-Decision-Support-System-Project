"""The maintenance domain.

Agentic OS is the engine: it ingests, cleans, joins, models, validates
and publishes, and it knows nothing about assets. This package is the
product's knowledge of maintenance, kept in one place so the engine stays
reusable and the domain stays reviewable.

    contract.py   what a row is, what each column measures, on what scale,
                  and which columns were knowable before the decision
    kpis.py       one controlled definition per measure, as a ratio of
                  sums over a stated population

Both are descriptions, not transformations: nothing here rewrites a
source value. A column that does not meet the contract is reported as not
meeting it.

The split from `server/detectors.py` is deliberate. The detectors ask
whether *any* dataset is internally coherent, which is why they transfer
to data nobody has seen. This package asks whether a dataset is a
maintenance dataset and which parts of it the product may speak about.
"""

from . import contract, kpis

__all__ = ["contract", "kpis"]
