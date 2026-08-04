"""The rights stance, as code rather than a paragraph (docs/rights.md, spec.md §6).

Three rules have to hold mechanically, because a rule that only lives in prose
is a rule the build can talk itself past: DRM is refused, paywalled stubs are
quarantined instead of ingested, and every chunk carries its source.

The fourth rule is about tone, and it shows up as an absence: none of these
messages asks the member to confirm anything, and none of them lectures.
"""
import os
import unittest
import zipfile

from brainkit import BrainOnDisk

import rights


class DRM(BrainOnDisk):
    """Circumventing DRM has no personal-use safe harbour. The kit does not try."""

    def file(self, name, payload=b"x"):
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as handle:
            handle.write(payload)
        return path

    def test_kindle_and_audible_formats_are_refused_by_extension(self):
        for name in ("book.azw3", "book.azw", "book.kfx", "audiobook.aax", "book.acsm"):
            with self.subTest(name=name):
                reason = rights.refusal_for_file(self.file(name))
                self.assertTrue(reason)
                self.assertIn("drm", reason.lower())

    def test_a_plain_epub_or_pdf_is_not_refused(self):
        epub = os.path.join(self.tmp, "plain.epub")
        with zipfile.ZipFile(epub, "w") as archive:
            archive.writestr("META-INF/container.xml", "<container/>")
        self.assertIsNone(rights.refusal_for_file(epub))
        self.assertIsNone(rights.refusal_for_file(self.file("plain.pdf", b"%PDF-1.7\ntrailer\n")))

    def test_an_encrypted_epub_is_refused_on_its_encryption_manifest(self):
        path = os.path.join(self.tmp, "locked.epub")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("META-INF/encryption.xml", "<encryption/>")
        reason = rights.refusal_for_file(path)
        self.assertTrue(reason)
        self.assertIn("drm", reason.lower())

    def test_an_encrypted_pdf_is_refused_on_its_encrypt_dictionary(self):
        path = self.file("locked.pdf", b"%PDF-1.7\n1 0 obj\ntrailer\n<< /Encrypt 9 0 R >>\n")
        self.assertTrue(rights.refusal_for_file(path))

    def test_the_spotify_player_is_refused_and_the_rss_route_is_offered(self):
        reason = rights.refusal_for_url("https://open.spotify.com/episode/abc123")
        self.assertTrue(reason)
        self.assertIn("rss", reason.lower())

    def test_the_refusal_covers_the_domain_not_one_spelling_of_the_host(self):
        """`www.audible.com` refused and `audible.co.uk` waved through is no stance."""
        for url in ("https://audible.com/pd/x",
                    "https://www.audible.co.uk/pd/x",
                    "https://www.audible.com.au/pd/x",
                    "https://podcasters.spotify.com/pod/show/x",
                    "https://spotify.link/abc",
                    "https://read.amazon.com/kindle-library"):
            with self.subTest(url=url):
                self.assertTrue(rights.refusal_for_url(url), url)

    def test_a_host_that_merely_ends_in_the_same_letters_is_not_refused(self):
        """Suffix matching is on label boundaries, not string endings."""
        self.assertIsNone(rights.refusal_for_url("https://notspotify.com/x"))
        self.assertIsNone(rights.refusal_for_url("https://myaudible.com/x"))

    def test_an_ordinary_feed_or_article_url_is_not_refused(self):
        for url in ("https://feeds.example.com/show.xml",
                    "https://example.com/articles/hydration",
                    "https://www.youtube.com/watch?v=abc"):
            with self.subTest(url=url):
                self.assertIsNone(rights.refusal_for_url(url))

    def test_a_refusal_never_asks_the_member_to_confirm_anything(self):
        """The stance is enforced silently — the model does not nag mid-run."""
        reason = rights.refusal_for_url("https://open.spotify.com/episode/abc123")
        for nag in ("confirm", "are you sure", "policy", "agree"):
            with self.subTest(nag=nag):
                self.assertNotIn(nag, reason.lower())


class Paywalls(unittest.TestCase):
    """A silent 200-word teaser is the nastiest thing that can enter a wiki."""

    ARTICLE = ("Hydration is the ratio of water to flour by weight. " * 40)

    def test_a_full_article_passes(self):
        self.assertIsNone(rights.paywall_reason(self.ARTICLE))

    def test_an_explicit_subscriber_wall_is_caught_at_any_length(self):
        text = self.ARTICLE + " Subscribe to continue reading this article."
        reason = rights.paywall_reason(text)
        self.assertTrue(reason)
        self.assertIn("paywall", reason.lower())

    def test_a_short_teaser_carrying_a_subscription_prompt_is_caught(self):
        reason = rights.paywall_reason(
            "Hydration matters more than flour choice, the bakers say. Sign in to read more.")
        self.assertTrue(reason)

    def test_a_short_extraction_with_no_wall_language_is_not_a_paywall(self):
        """Short is not the same as walled — a stub note is a thin source, not a stub wall."""
        self.assertIsNone(rights.paywall_reason("A short but complete note about starters."))

    def test_an_empty_extraction_is_not_reported_as_a_paywall(self):
        self.assertIsNone(rights.paywall_reason(""))


class Attribution(unittest.TestCase):
    """Every chunk says where it came from — checked, not trusted."""

    def test_provenance_without_a_source_is_a_gap(self):
        self.assertTrue(rights.attribution_gap({"source_format": "web"}))
        self.assertTrue(rights.attribution_gap({"source": "  ", "source_format": "web"}))

    def test_provenance_without_a_format_is_a_gap(self):
        self.assertTrue(rights.attribution_gap({"source": "https://example.com/a"}))

    def test_a_source_and_a_format_are_enough(self):
        self.assertIsNone(rights.attribution_gap(
            {"source": "https://example.com/a", "source_format": "web"}))

    def test_requiring_attribution_raises_rather_than_writing_a_bare_page(self):
        with self.assertRaises(rights.RightsError):
            rights.require_attribution({"source_format": "web"})


if __name__ == "__main__":
    unittest.main()
