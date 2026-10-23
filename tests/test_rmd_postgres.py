"""Run the evidence contract unchanged against an explicit disposable PostgreSQL."""

import unittest

from tests import test_rmd_service as evidence_tests
from tests.test_runs import PG_TEST_URL, _postgres_available


@unittest.skipUnless(_postgres_available(), "PostgreSQL test database is not configured")
class RmdServicePostgresTests(evidence_tests.RmdServiceTests):
    database_url = PG_TEST_URL


if __name__ == "__main__":
    unittest.main()
