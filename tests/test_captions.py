"""Caption files become prose, without the 3–4× word count rolling captions add.

The prototype's decisive finding (spec.md §6): YouTube auto-captions restate
themselves cue after cue, so a naive concatenation inflates the corpus three to
four times over — every number in the brain then sits in a page that claims to
be four times longer than the source really was.
"""
import unittest

import brainkit  # noqa: F401 — puts the skill's scripts/ on the import path

import captions

ROLLING_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.120 --> 00:00:02.400
so today we're

00:00:02.400 --> 00:00:04.100
so today we're going to talk

00:00:04.100 --> 00:00:06.000
so today we're going to talk about hydration

00:00:06.000 --> 00:00:08.000
about hydration

00:00:08.000 --> 00:00:10.000
and why seventy percent is the baseline
"""

PUBLISHER_VTT = """WEBVTT

1
00:00:01.000 --> 00:00:04.000
<v Host>Welcome to the show.</v>

2
00:00:04.000 --> 00:00:07.000
Today we talk about starters. [MUSIC]
"""

SRT = """1
00:00:01,000 --> 00:00:04,000
Welcome to the show.

2
00:00:04,000 --> 00:00:07,000
Today we talk about starters.
"""


class RollingCaptions(unittest.TestCase):
    """The inflation case: each cue restates the one before it."""

    def test_a_growing_cue_is_kept_once_not_once_per_stage(self):
        text = captions.clean(ROLLING_VTT, "vtt")
        self.assertEqual(1, text.count("so today we're going to talk"))
        self.assertIn("about hydration", text)

    def test_a_repeated_cue_is_not_repeated_in_the_prose(self):
        self.assertEqual(1, captions.clean(ROLLING_VTT, "vtt").count("about hydration"))

    def test_the_whole_transcript_survives_in_order(self):
        self.assertEqual(
            "so today we're going to talk about hydration and why seventy "
            "percent is the baseline",
            captions.clean(ROLLING_VTT, "vtt"))

    def test_dedup_does_not_eat_a_genuinely_new_sentence(self):
        lines = ["the starter doubles in six hours", "the oven runs at 250 c"]
        self.assertEqual("the starter doubles in six hours the oven runs at 250 c",
                         captions.join_cues(lines))

    def test_it_collapses_the_two_line_rolling_window_shape(self):
        lines = ["hydration runs at seventy", "percent for most flours",
                 "percent for most flours", "and wholemeal drinks more"]
        self.assertEqual(
            "hydration runs at seventy percent for most flours and wholemeal drinks more",
            captions.join_cues(lines))

    def test_word_count_lands_near_the_real_transcript_not_a_multiple_of_it(self):
        """The 3–4× inflation is the failure this whole module exists for."""
        self.assertEqual(15, len(captions.clean(ROLLING_VTT, "vtt").split()))


class Markup(unittest.TestCase):
    """Timing, positioning and sound-effect markup are not the transcript."""

    def test_headers_timestamps_and_cue_numbers_are_dropped(self):
        text = captions.clean(PUBLISHER_VTT, "vtt")
        for noise in ("WEBVTT", "-->", "00:00:01"):
            with self.subTest(noise=noise):
                self.assertNotIn(noise, text)

    def test_speaker_tags_and_inline_timing_tags_are_stripped(self):
        self.assertNotIn("<v", captions.clean(PUBLISHER_VTT, "vtt"))
        self.assertIn("Welcome to the show.", captions.clean(PUBLISHER_VTT, "vtt"))

    def test_bracketed_sound_effects_are_dropped(self):
        self.assertNotIn("MUSIC", captions.clean(PUBLISHER_VTT, "vtt"))

    def test_srt_reads_the_same_way_as_vtt(self):
        self.assertEqual(captions.clean(SRT, "srt"),
                         "Welcome to the show. Today we talk about starters.")


class OtherTranscriptShapes(unittest.TestCase):
    """`<podcast:transcript>` ships in whatever format the publisher chose."""

    def test_the_podcast_index_json_transcript_is_read_by_segment(self):
        payload = ('{"version": "1.0.0", "segments": ['
                   '{"speaker": "Host", "body": "Welcome back."},'
                   '{"speaker": "Guest", "body": "Glad to be here."}]}')
        self.assertEqual("Welcome back. Glad to be here.", captions.clean(payload, "json"))

    def test_an_html_transcript_page_comes_back_as_its_text(self):
        html = "<html><body><p>Welcome back.</p><script>x=1</script><p>Part two.</p></body></html>"
        text = captions.clean(html, "html")
        self.assertIn("Welcome back.", text)
        self.assertIn("Part two.", text)
        self.assertNotIn("x=1", text)

    def test_plain_text_is_passed_through_with_whitespace_tidied(self):
        self.assertEqual("Just the words.", captions.clean("  Just   the\n\nwords.  ", "text"))

    def test_the_format_is_guessed_from_the_mime_type_the_feed_declared(self):
        self.assertEqual("vtt", captions.format_for("text/vtt", "https://x/e.vtt"))
        self.assertEqual("srt", captions.format_for("application/x-subrip", "https://x/e"))
        self.assertEqual("json", captions.format_for("application/json", "https://x/e"))
        self.assertEqual("html", captions.format_for("text/html", "https://x/e"))
        self.assertEqual("text", captions.format_for("text/plain", "https://x/e"))

    def test_an_unhelpful_mime_type_falls_back_to_the_url_extension(self):
        self.assertEqual("vtt", captions.format_for("application/octet-stream",
                                                    "https://x/ep1.vtt?v=2"))
        self.assertEqual("text", captions.format_for("", "https://x/ep1"))


class EmptyTranscripts(unittest.TestCase):
    """Throttle poisoning returns a file, not a transcript. It must not be silent."""

    def test_nothing_at_all_is_empty(self):
        self.assertTrue(captions.is_empty("WEBVTT\n\n"))
        self.assertTrue(captions.is_empty(""))

    def test_a_stub_far_below_a_real_transcript_is_empty(self):
        self.assertTrue(captions.is_empty("thanks for watching"))

    def test_a_real_transcript_is_not_empty(self):
        self.assertFalse(captions.is_empty("word " * 200))


if __name__ == "__main__":
    unittest.main()
