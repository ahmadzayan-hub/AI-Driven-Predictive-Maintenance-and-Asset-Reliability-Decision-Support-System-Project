"""The install surface and project documentation agree on the product name."""

import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class PageMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.apple_title = None

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name") == "apple-mobile-web-app-title":
            self.apple_title = attrs.get("content")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


class ProductIdentityTestCase(unittest.TestCase):
    def test_project_browser_and_installed_app_names_agree(self):
        title = "AI-Driven Predictive Maintenance and Asset Reliability Decision-Support System SaaS Project"
        page = PageMetadata()
        page.feed((ROOT / "frontend/index.html").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "frontend/public/manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(page.title, title)
        self.assertEqual(manifest["name"], title)
        self.assertEqual(page.apple_title, manifest["short_name"])
        # The README opens with a hero image and a short bilingual heading, so the
        # full product name is required in the opening section (everything before
        # the first second-level heading), not on a fixed line.
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        opening = " ".join(readme.split("\n## ", 1)[0].split())
        self.assertIn("\n# ", "\n" + readme)
        self.assertIn(title, opening)
        # Renaming a product must not create a second installed application.
        self.assertEqual(manifest["id"], "/")
        self.assertEqual(manifest["start_url"], "/")


if __name__ == "__main__":
    unittest.main()
