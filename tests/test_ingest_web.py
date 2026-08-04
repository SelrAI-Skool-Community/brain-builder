"""The web-article arm: a URL becomes an attributed `raw/` page, or a loud record.

trafilatura does the extraction (spec.md §6) and is imported inside the arm, so
the suite runs without it. What the tests hold is everything around it: the
rights refusals, the paywall quarantine that keeps a 200-word teaser out of the
wiki, and the rate limit the rights stance promises.
"""
import contextlib
import io
import json
import os
import unittest

from brainkit import BrainOnDisk

import fetching
import ingest_web
from brain_contract import parse_frontmatter
from scaffold import scaffold_brain

ARTICLE = ("Hydration is the ratio of water to flour by weight, and it decides "
           "the crumb. " * 30)


class WebArm(BrainOnDisk):
    """A brain, a stub fetcher and a stub extractor — no network anywhere."""

    def setUp(self):
        super(WebArm, self).setUp()
        self.brain = scaffold_brain(title="Test Brain", at=self.tmp)
        self.pages = {}
        self.fetched = []

    def fetcher(self, url):
        self.fetched.append(url)
        if url not in self.pages:
            raise fetching.FetchError("could not fetch {}: 404".format(url))
        return fetching.Response(self.pages[url].encode("utf-8"), "text/html", url)

    def extractor(self, html, url):
        return html, {"title": "Hydration explained", "author": "A Baker"}

    def ingest(self, *urls, **kwargs):
        kwargs.setdefault("fetcher", self.fetcher)
        kwargs.setdefault("extractor", self.extractor)
        return ingest_web.ingest(list(urls), self.brain, **kwargs)

    def raw_pages(self):
        return sorted(name for name in os.listdir(os.path.join(self.brain, "raw"))
                      if name.endswith(".md"))

    def raw_text(self, name):
        with open(os.path.join(self.brain, "raw", name), encoding="utf-8") as handle:
            return handle.read()


class Articles(WebArm):
    """The happy path, and what the page has to carry when it lands."""

    def test_an_article_lands_as_one_attributed_page(self):
        self.pages["https://example.com/hydration"] = ARTICLE
        manifest = self.ingest("https://example.com/hydration")
        self.assertEqual(1, len(manifest.ok))
        self.assertEqual(1, len(self.raw_pages()))

    def test_the_page_carries_the_url_title_and_author_it_came_from(self):
        self.pages["https://example.com/hydration"] = ARTICLE
        self.ingest("https://example.com/hydration")
        front, body, _ = parse_frontmatter(self.raw_text(self.raw_pages()[0]))
        self.assertEqual("https://example.com/hydration", front["source"])
        self.assertEqual("web", front["source_format"])
        self.assertEqual("Hydration explained", front["title"])
        self.assertEqual("A Baker", front["author"])
        self.assertIn("Hydration is the ratio", body)

    def test_the_same_article_at_two_urls_is_ingested_once(self):
        self.pages["https://example.com/a"] = ARTICLE
        self.pages["https://mirror.example.com/a"] = ARTICLE
        manifest = self.ingest("https://example.com/a", "https://mirror.example.com/a")
        self.assertEqual(1, len(manifest.ok))
        self.assertEqual(1, len(manifest.duplicate))

    def test_a_dead_url_is_a_record_not_an_exception(self):
        self.pages["https://example.com/a"] = ARTICLE
        manifest = self.ingest("https://example.com/a", "https://example.com/gone")
        self.assertEqual(1, len(manifest.ok))
        self.assertEqual(1, len(manifest.failed))
        self.assertIn("gone", manifest.failed[0].source)

    def test_an_extraction_with_no_text_is_empty_not_silently_dropped(self):
        self.pages["https://example.com/empty"] = "   "
        manifest = self.ingest("https://example.com/empty")
        self.assertEqual(1, len(manifest.empty))
        self.assertTrue(manifest.whole_corpus_failed)

    def test_every_non_landing_url_is_named_in_the_build_log(self):
        self.pages["https://example.com/a"] = ARTICLE
        self.ingest("https://example.com/a", "https://example.com/gone")
        with open(os.path.join(self.brain, "log.md"), encoding="utf-8") as handle:
            log = handle.read()
        self.assertIn("https://example.com/gone", log)
        self.assertIn("1 sources ingested", log)


class Rights(WebArm):
    """DRM is refused and paywalls are quarantined — in code, not in prose."""

    def test_the_spotify_player_is_never_fetched(self):
        manifest = self.ingest("https://open.spotify.com/episode/abc")
        self.assertEqual(1, len(manifest.failed))
        self.assertEqual([], self.fetched)
        self.assertIn("RSS", manifest.failed[0].reason)

    def test_a_paywalled_teaser_is_quarantined_rather_than_ingested(self):
        self.pages["https://paper.example.com/a"] = (
            "Hydration decides the crumb, bakers say. Subscribe to continue reading.")
        manifest = self.ingest("https://paper.example.com/a")
        self.assertEqual([], self.raw_pages())
        self.assertEqual(1, len(manifest.failed))
        self.assertIn("paywall", manifest.failed[0].reason.lower())

    def test_the_quarantined_text_is_kept_where_the_member_can_see_it(self):
        self.pages["https://paper.example.com/a"] = (
            "Hydration decides the crumb, bakers say. Subscribe to continue reading.")
        self.ingest("https://paper.example.com/a")
        quarantined = os.listdir(os.path.join(self.brain, "quarantine"))
        self.assertEqual(1, len(quarantined))

    def test_quarantine_lives_outside_raw_so_nothing_distils_from_it(self):
        self.pages["https://paper.example.com/a"] = (
            "Hydration decides the crumb, bakers say. Subscribe to continue reading.")
        self.ingest("https://paper.example.com/a")
        self.assertFalse(os.path.isdir(os.path.join(self.brain, "raw", "quarantine")))


class MissingLibrary(WebArm):
    """No trafilatura on the machine is a named failure, never a traceback."""

    def test_the_pip_line_is_the_reason_on_the_record(self):
        def extractor(html, url):
            raise ImportError("No module named 'trafilatura'")

        self.pages["https://example.com/a"] = ARTICLE
        manifest = self.ingest("https://example.com/a", extractor=extractor)
        self.assertEqual(1, len(manifest.failed))
        self.assertIn("pip install trafilatura", manifest.failed[0].reason)


class RateLimit(unittest.TestCase):
    """The rights stance promises visible, conservative limits on fetching."""

    def test_the_fetcher_sleeps_between_requests_but_not_before_the_first(self):
        slept = []
        opener = lambda request, timeout=None: _FakeResponse()
        fetcher = fetching.Fetcher(delay=2, opener=opener, sleeper=slept.append)
        fetcher("https://example.com/a")
        self.assertEqual([], slept)
        fetcher("https://example.com/b")
        self.assertEqual([2], slept)

    def test_a_network_failure_becomes_a_fetch_error_not_a_traceback(self):
        def opener(request, timeout=None):
            raise OSError("connection reset")

        with self.assertRaises(fetching.FetchError):
            fetching.Fetcher(delay=0, opener=opener)("https://example.com/a")


class _FakeResponse(object):
    url = "https://example.com/a"
    headers = {"Content-Type": "text/html"}

    def read(self):
        return b"<html></html>"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class CommandLine(WebArm):
    """`python3 ingest_web.py <url> --into <brain>`."""

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            return ingest_web.main(["ingest_web.py"] + list(args)), out.getvalue()

    def test_a_corpus_that_yielded_nothing_exits_one(self):
        """A refused URL is reached before any fetch, so this stays offline."""
        code, out = self.run_cli("https://open.spotify.com/episode/abc",
                                 "--into", self.brain, "--delay", "0")
        self.assertEqual(1, code)
        self.assertIn("0 sources ingested", out)

    def test_missing_arguments_exit_two(self):
        self.assertEqual(2, self.run_cli("https://example.com/a")[0])
        self.assertEqual(2, self.run_cli("--into", self.brain)[0])

    def test_json_output_gives_the_build_the_counts(self):
        code, out = self.run_cli("https://open.spotify.com/episode/abc",
                                 "--into", self.brain, "--json", "--delay", "0")
        self.assertEqual(1, code)
        self.assertEqual(1, json.loads(out)["counts"]["failed"])


if __name__ == "__main__":
    unittest.main()
