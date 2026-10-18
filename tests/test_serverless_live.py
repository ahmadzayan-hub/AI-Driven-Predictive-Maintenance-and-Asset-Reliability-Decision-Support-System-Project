import unittest

from server import live


class ServerlessLiveBudgetTests(unittest.TestCase):
    def test_serverless_event_stream_ends_before_function_timeout(self):
        self.assertEqual(live.stream_budget(55, {"VERCEL": "1"}), 20)
        self.assertEqual(live.stream_budget(25, {"VERCEL": "true"}), 20)
        self.assertEqual(live.stream_budget(0, {"VERCEL": "1"}), 0)

    def test_non_serverless_runtime_keeps_existing_budget(self):
        self.assertEqual(live.stream_budget(55, {}), 55)
        self.assertEqual(live.stream_budget(7, {}), 7)


if __name__ == "__main__":
    unittest.main()
