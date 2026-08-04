"""The podcast arm: Apple Podcasts and generic RSS (spec.md §6).

Two subsystems, not one — yt-dlp handles anything video-shaped and this handles
anything feed-shaped, and both come back to the same transcription fallback. The
resolver is the interesting half: Apple is a directory, not a host, so an Apple
URL becomes an `id`, an `id` becomes a `feedUrl` through the iTunes Lookup API,
and everything after that is ordinary RSS.

Spotify is the stretch goal with the hard edge: resolve to RSS or fail. The
player is DRM'd and the kit never touches it, and a Spotify exclusive has no
feed at all — which is a dead end said out loud, not a workaround to find.
"""
import contextlib
import io
import json
import os
import unittest

from brainkit import BrainOnDisk

import fetching
import ingest_podcast
import rights
from brain_contract import parse_frontmatter
from scaffold import scaffold_brain

TRANSCRIPT_VTT = ("WEBVTT\n\n00:00.000 --> 00:05.000\n" +
                  "Hydration is the ratio of water to flour by weight. " * 10)

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>The Bread Show</title>
    <itunes:author>A Baker</itunes:author>
    <link>https://breadshow.example.com</link>
    <item>
      <title>Episode 1 — Hydration</title>
      <guid>ep-1</guid>
      <pubDate>Mon, 05 Jan 2026 09:00:00 +0000</pubDate>
      <itunes:duration>1:02:03</itunes:duration>
      <link>https://breadshow.example.com/1</link>
      <enclosure url="https://cdn.example.com/ep1.mp3" type="audio/mpeg" length="1"/>
      <podcast:transcript url="https://cdn.example.com/ep1.vtt" type="text/vtt"/>
    </item>
    <item>
      <title>Episode 2 — Shaping</title>
      <guid>ep-2</guid>
      <itunes:duration>1800</itunes:duration>
      <enclosure url="https://cdn.example.com/ep2.mp3" type="audio/mpeg" length="1"/>
    </item>
  </channel>
</rss>
"""

EXCLUSIVE_FEED = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Exclusive Show</title>
  <item><title>Members only</title><guid>ex-1</guid>
    <link>https://open.spotify.com/episode/xyz</link></item>
</channel></rss>
"""

LOOKUP = json.dumps({"resultCount": 1, "results": [
    {"feedUrl": "https://feeds.example.com/breadshow.xml",
     "collectionName": "The Bread Show", "artistName": "A Baker"}]})


class StubFetcher(object):
    """Every URL the arm might read, answered from a dict."""

    def __init__(self, pages=None):
        self.pages = pages or {}
        self.asked = []

    def __call__(self, url):
        self.asked.append(url)
        if url not in self.pages:
            raise fetching.FetchError("could not fetch {}: 404".format(url))
        body, content_type = self.pages[url]
        return fetching.Response(body.encode("utf-8"), content_type, url)

    def download(self, url, directory, filename="media"):
        self(url)
        path = os.path.join(directory, filename)
        with open(path, "wb") as handle:
            handle.write(b"audio")
        return path


class Resolving(unittest.TestCase):
    """Apple is a directory; RSS is the thing that actually gets read."""

    def fetcher(self, **pages):
        return StubFetcher({url: (body, "application/json")
                            for url, body in pages.items()})

    def test_an_apple_podcasts_url_becomes_a_feed_url_through_the_lookup_api(self):
        fetcher = self.fetcher(**{
            "https://itunes.apple.com/lookup?id=1234&entity=podcast": LOOKUP})
        feed = ingest_podcast.resolve_feed(
            "https://podcasts.apple.com/au/podcast/the-bread-show/id1234", fetcher)
        self.assertEqual("https://feeds.example.com/breadshow.xml", feed)

    def test_a_bare_itunes_id_resolves_the_same_way(self):
        fetcher = self.fetcher(**{
            "https://itunes.apple.com/lookup?id=1234&entity=podcast": LOOKUP})
        self.assertEqual("https://feeds.example.com/breadshow.xml",
                         ingest_podcast.resolve_feed("1234", fetcher))

    def test_a_feed_url_is_already_the_answer_and_costs_no_request(self):
        fetcher = self.fetcher()
        self.assertEqual("https://feeds.example.com/breadshow.xml",
                         ingest_podcast.resolve_feed(
                             "https://feeds.example.com/breadshow.xml", fetcher))
        self.assertEqual([], fetcher.asked)

    def test_a_show_name_is_searched_in_the_directory(self):
        fetcher = self.fetcher(**{
            "https://itunes.apple.com/search?media=podcast&limit=1&term=the+bread+show":
                LOOKUP})
        self.assertEqual("https://feeds.example.com/breadshow.xml",
                         ingest_podcast.resolve_feed("the bread show", fetcher))

    def test_a_directory_entry_with_no_feed_fails_loudly(self):
        empty = json.dumps({"resultCount": 0, "results": []})
        fetcher = self.fetcher(**{
            "https://itunes.apple.com/lookup?id=1234&entity=podcast": empty})
        with self.assertRaises(ingest_podcast.ResolveError):
            ingest_podcast.resolve_feed("1234", fetcher)

    def test_the_spotify_player_is_refused_and_rss_is_offered_instead(self):
        with self.assertRaises(rights.RightsError) as caught:
            ingest_podcast.resolve_feed("https://open.spotify.com/show/abc",
                                        self.fetcher())
        self.assertIn("RSS", str(caught.exception))


class FeedParsing(unittest.TestCase):
    """Ordinary RSS, plus the one namespaced tag that saves a transcription bill."""

    def setUp(self):
        self.feed = ingest_podcast.parse_feed(FEED)

    def test_the_show_metadata_is_read(self):
        self.assertEqual("The Bread Show", self.feed.title)
        self.assertEqual("A Baker", self.feed.author)

    def test_every_item_becomes_an_episode_in_feed_order(self):
        self.assertEqual(["Episode 1 — Hydration", "Episode 2 — Shaping"],
                         [episode.title for episode in self.feed.episodes])

    def test_the_enclosure_is_the_audio_to_fall_back_to(self):
        self.assertEqual("https://cdn.example.com/ep1.mp3",
                         self.feed.episodes[0].enclosure_url)

    def test_a_published_transcript_is_found_with_its_declared_type(self):
        self.assertEqual([("https://cdn.example.com/ep1.vtt", "text/vtt")],
                         self.feed.episodes[0].transcripts)
        self.assertEqual([], self.feed.episodes[1].transcripts)

    def test_durations_are_read_in_either_shape_for_the_cost_estimate(self):
        self.assertEqual(3723, self.feed.episodes[0].duration)
        self.assertEqual(1800, self.feed.episodes[1].duration)

    def test_a_transcript_type_the_kit_cannot_read_is_not_chosen(self):
        chosen = ingest_podcast.pick_transcript([("https://x/e.pdf", "application/pdf")])
        self.assertIsNone(chosen)

    def test_the_richest_transcript_format_wins(self):
        chosen = ingest_podcast.pick_transcript([("https://x/e.html", "text/html"),
                                                 ("https://x/e.vtt", "text/vtt")])
        self.assertEqual(("https://x/e.vtt", "text/vtt"), chosen)


class PodcastArm(BrainOnDisk):
    """A brain and a stub network."""

    FEED_URL = "https://feeds.example.com/breadshow.xml"

    def setUp(self):
        super(PodcastArm, self).setUp()
        self.brain = scaffold_brain(title="Test Brain", at=self.tmp)

    def fetcher(self, feed=FEED, **extra):
        pages = {self.FEED_URL: (feed, "application/rss+xml")}
        pages.update(extra)
        return StubFetcher(pages)

    def ingest(self, fetcher, **kwargs):
        return ingest_podcast.ingest([self.FEED_URL], self.brain, fetcher=fetcher, **kwargs)

    def raw_pages(self):
        return sorted(name for name in os.listdir(os.path.join(self.brain, "raw"))
                      if name.endswith(".md"))

    def raw_text(self, name):
        with open(os.path.join(self.brain, "raw", name), encoding="utf-8") as handle:
            return handle.read()

    def log(self):
        with open(os.path.join(self.brain, "log.md"), encoding="utf-8") as handle:
            return handle.read()


class PublishedTranscripts(PodcastArm):
    """The free path: the publisher already did the work."""

    def test_an_episode_with_a_transcript_lands_without_transcribing_anything(self):
        fetcher = self.fetcher(**{"https://cdn.example.com/ep1.vtt":
                                  (TRANSCRIPT_VTT, "text/vtt")})
        manifest = self.ingest(fetcher)
        self.assertEqual(1, len(manifest.ok))
        self.assertNotIn("https://cdn.example.com/ep1.mp3", fetcher.asked)

    def test_the_page_carries_the_show_episode_and_transcript_source(self):
        self.ingest(self.fetcher(**{"https://cdn.example.com/ep1.vtt":
                                    (TRANSCRIPT_VTT, "text/vtt")}))
        front, body, _ = parse_frontmatter(self.raw_text(self.raw_pages()[0]))
        self.assertEqual("https://breadshow.example.com/1", front["source"])
        self.assertEqual("podcast", front["source_format"])
        self.assertEqual("Episode 1 — Hydration", front["title"])
        self.assertEqual("A Baker", front["author"])
        self.assertEqual("The Bread Show", front["show"])
        self.assertEqual("publisher", front["transcript"])
        self.assertIn("Hydration is the ratio", body)

    def test_an_episode_with_no_transcript_is_recorded_not_skipped(self):
        manifest = self.ingest(self.fetcher(**{"https://cdn.example.com/ep1.vtt":
                                               (TRANSCRIPT_VTT, "text/vtt")}))
        self.assertEqual(1, len(manifest.empty))
        self.assertIn("--transcribe", manifest.empty[0].reason)

    def test_a_transcript_url_that_dies_falls_through_rather_than_failing_the_run(self):
        manifest = self.ingest(self.fetcher())
        self.assertEqual(2, len(manifest.empty))
        self.assertTrue(manifest.whole_corpus_failed)

    def test_every_episode_without_words_is_named_in_the_log(self):
        self.ingest(self.fetcher())
        self.assertIn("Episode 2", self.log())


class TranscriptionFallback(PodcastArm):
    """Publisher transcript → transcription → loud failure, in that order."""

    def transcriber(self, path):
        return "Shaping builds surface tension across the skin of the dough. " * 10

    def test_an_episode_without_a_transcript_is_transcribed_when_allowed(self):
        fetcher = self.fetcher(**{"https://cdn.example.com/ep1.vtt":
                                  (TRANSCRIPT_VTT, "text/vtt"),
                                  "https://cdn.example.com/ep2.mp3": ("", "audio/mpeg")})
        manifest = self.ingest(fetcher, transcribe_missing=True,
                               transcriber=self.transcriber)
        self.assertEqual(2, len(manifest.ok))

    def test_the_transcribed_page_says_which_engine_produced_it(self):
        fetcher = self.fetcher(feed=FEED, **{"https://cdn.example.com/ep2.mp3":
                                             ("", "audio/mpeg")})
        self.ingest(fetcher, transcribe_missing=True, transcriber=self.transcriber)
        fronts = [parse_frontmatter(self.raw_text(name))[0] for name in self.raw_pages()]
        self.assertIn("scribe-v2", [front.get("transcript") for front in fronts])

    def test_a_failed_transcription_is_a_loud_record(self):
        def transcriber(path):
            raise RuntimeError("no ELEVENLABS_API_KEY in the environment")

        fetcher = self.fetcher(**{"https://cdn.example.com/ep1.mp3": ("", "audio/mpeg"),
                                  "https://cdn.example.com/ep2.mp3": ("", "audio/mpeg")})
        manifest = self.ingest(fetcher, transcribe_missing=True, transcriber=transcriber)
        self.assertEqual(2, len(manifest.failed))
        self.assertIn("ELEVENLABS_API_KEY", manifest.failed[0].reason)


class Exclusives(PodcastArm):
    """A show with no audio in its feed is a dead end, and says so."""

    def test_an_episode_with_no_audio_and_no_transcript_fails_loudly(self):
        manifest = self.ingest(self.fetcher(feed=EXCLUSIVE_FEED), transcribe_missing=True)
        self.assertEqual(1, len(manifest.failed))
        self.assertIn("exclusive", manifest.failed[0].reason.lower())


class Estimating(PodcastArm):
    """Gate 2 needs the hours before the build is approved, not after."""

    def test_only_the_episodes_that_would_need_transcribing_are_priced(self):
        """Episode 1 ships its own transcript, so it costs nothing to ingest."""
        quote = ingest_podcast.estimate([self.FEED_URL], fetcher=self.fetcher())
        self.assertEqual(1800, quote.seconds)
        self.assertIn("$", quote.line())

    def test_a_show_that_publishes_every_transcript_is_free(self):
        quote = ingest_podcast.estimate([self.FEED_URL],
                                        fetcher=self.fetcher(feed=_all_transcribed()))
        self.assertEqual(0, quote.seconds)
        self.assertIn("none", quote.line().lower())


def _all_transcribed():
    """The fixture feed, with a published transcript on every episode."""
    return FEED.replace(
        "      <itunes:duration>1800</itunes:duration>",
        "      <itunes:duration>1800</itunes:duration>\n"
        '      <podcast:transcript url="https://cdn.example.com/ep2.vtt" type="text/vtt"/>')


class CommandLine(PodcastArm):
    """`python3 ingest_podcast.py <show> --into <brain>`."""

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            return ingest_podcast.main(["ingest_podcast.py"] + list(args)), out.getvalue()

    def test_missing_arguments_exit_two(self):
        self.assertEqual(2, self.run_cli("https://feeds.example.com/x.xml")[0])
        self.assertEqual(2, self.run_cli("--into", self.brain)[0])

    def test_a_bad_limit_exits_two(self):
        self.assertEqual(2, self.run_cli("x", "--into", self.brain, "--limit", "lots")[0])

    def test_a_refused_show_exits_one_without_touching_the_network(self):
        code, out = self.run_cli("https://open.spotify.com/show/abc",
                                 "--into", self.brain, "--delay", "0")
        self.assertEqual(1, code)
        self.assertIn("0 sources ingested", out)


if __name__ == "__main__":
    unittest.main()
