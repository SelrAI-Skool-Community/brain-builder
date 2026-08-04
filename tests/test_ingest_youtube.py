"""The YouTube arm, ported from the seed brain's prototype (spec.md §6).

yt-dlp is held behind a downloader seam, so the whole arm runs here with no
network, no cookies and no yt-dlp installed. The three things the prototype
proved matter are what the tests hold: the archive that makes a re-run cheap,
the empty-transcript detection that stops throttling from looking like silence,
and the ordering — publisher captions, then transcription, then a loud failure.
"""
import contextlib
import io
import json
import os
import unittest

from brainkit import BrainOnDisk

import ingest_youtube
from brain_contract import parse_frontmatter
from scaffold import scaffold_brain

TRANSCRIPT = "Hydration is the ratio of water to flour by weight. " * 10


class FakeDownloader(object):
    """yt-dlp, as the arm sees it: listings, captions, audio."""

    def __init__(self, listings=None, captions=None, audio=None):
        self.listings = listings or {}
        self.captions_by_id = captions or {}
        self.audio_by_id = audio or {}
        self.captions_asked = []
        self.audio_asked = []
        self.update_note = "yt-dlp 2026.08.01 (up to date)"

    def videos(self, target, limit=None):
        found = self.listings.get(target, [])
        return found[:limit] if limit else found

    def captions(self, video):
        self.captions_asked.append(video.video_id)
        value = self.captions_by_id.get(video.video_id, "")
        if isinstance(value, Exception):
            raise value
        return value

    def audio(self, video, directory):
        self.audio_asked.append(video.video_id)
        value = self.audio_by_id.get(video.video_id)
        if isinstance(value, Exception):
            raise value
        path = os.path.join(directory, video.video_id + ".m4a")
        with open(path, "wb") as handle:
            handle.write(b"audio")
        return path


def video(video_id, title=None):
    return ingest_youtube.Video(
        video_id=video_id, title=title or ("Video " + video_id),
        url="https://www.youtube.com/watch?v=" + video_id,
        channel="The Baker", duration=1800, published="20260101")


class YouTubeArm(BrainOnDisk):
    """A brain and a fake yt-dlp."""

    def setUp(self):
        super(YouTubeArm, self).setUp()
        self.brain = scaffold_brain(title="Test Brain", at=self.tmp)

    def downloader(self, videos, captions=None, audio=None, target="channel"):
        return FakeDownloader({target: videos}, captions, audio)

    def ingest(self, downloader, target="channel", **kwargs):
        return ingest_youtube.ingest([target], self.brain, downloader=downloader, **kwargs)

    def raw_pages(self):
        return sorted(name for name in os.listdir(os.path.join(self.brain, "raw"))
                      if name.endswith(".md"))

    def raw_text(self, name):
        with open(os.path.join(self.brain, "raw", name), encoding="utf-8") as handle:
            return handle.read()

    def log(self):
        with open(os.path.join(self.brain, "log.md"), encoding="utf-8") as handle:
            return handle.read()


class Captions(YouTubeArm):
    """The ordinary case: the platform has a transcript and it is used."""

    def test_each_video_with_captions_lands_as_one_page(self):
        downloader = self.downloader(
            [video("aaa"), video("bbb")],
            captions={"aaa": TRANSCRIPT, "bbb": TRANSCRIPT + " Second video."})
        manifest = self.ingest(downloader)
        self.assertEqual(2, len(manifest.ok))
        self.assertEqual(2, len(self.raw_pages()))

    def test_the_page_carries_the_video_url_channel_and_transcript_source(self):
        self.ingest(self.downloader([video("aaa", "Hydration explained")],
                                    captions={"aaa": TRANSCRIPT}))
        front, body, _ = parse_frontmatter(self.raw_text(self.raw_pages()[0]))
        self.assertEqual("https://www.youtube.com/watch?v=aaa", front["source"])
        self.assertEqual("youtube", front["source_format"])
        self.assertEqual("Hydration explained", front["title"])
        self.assertEqual("The Baker", front["author"])
        self.assertEqual("captions", front["transcript"])
        self.assertIn("Hydration is the ratio", body)

    def test_rolling_captions_are_collapsed_before_the_page_is_written(self):
        """Raw VTT would put the same sentence in three times over."""
        rolling = ("WEBVTT\n\n00:00.000 --> 00:02.000\n" + TRANSCRIPT +
                   "\n\n00:02.000 --> 00:04.000\n" + TRANSCRIPT + " and more words here\n")
        manifest = self.ingest(self.downloader([video("aaa")], captions={"aaa": rolling}))
        self.assertLess(manifest.ok[0].words, len(TRANSCRIPT.split()) * 2)

    def test_a_limit_caps_how_many_videos_are_pulled(self):
        downloader = self.downloader([video("aaa"), video("bbb"), video("ccc")],
                                     captions={"aaa": TRANSCRIPT, "bbb": TRANSCRIPT + " b",
                                               "ccc": TRANSCRIPT + " c"})
        self.assertEqual(2, len(self.ingest(downloader, limit=2).ok))

    def test_a_download_error_on_one_video_is_a_record_not_a_stopped_run(self):
        downloader = self.downloader(
            [video("aaa"), video("bbb")],
            captions={"aaa": TRANSCRIPT, "bbb": RuntimeError("HTTP 429 rate limited")})
        manifest = self.ingest(downloader)
        self.assertEqual(1, len(manifest.ok))
        self.assertIn("429", manifest.failed[0].reason)


class EmptyTranscripts(YouTubeArm):
    """Throttle poisoning returns a caption file with nothing in it."""

    def test_an_empty_transcript_is_recorded_not_silently_skipped(self):
        manifest = self.ingest(self.downloader([video("aaa")], captions={"aaa": ""}))
        self.assertEqual(1, len(manifest.empty))
        self.assertTrue(manifest.whole_corpus_failed)

    def test_the_reason_names_the_transcription_fallback_that_would_fix_it(self):
        manifest = self.ingest(self.downloader([video("aaa")], captions={"aaa": ""}))
        self.assertIn("--transcribe", manifest.empty[0].reason)

    def test_a_near_empty_caption_file_counts_as_empty(self):
        manifest = self.ingest(self.downloader([video("aaa")],
                                               captions={"aaa": "thanks for watching"}))
        self.assertEqual(1, len(manifest.empty))

    def test_every_empty_video_is_named_in_the_log(self):
        self.ingest(self.downloader([video("aaa")], captions={"aaa": ""}))
        self.assertIn("watch?v=aaa", self.log())


class TranscriptionFallback(YouTubeArm):
    """Captions first, transcription second, loud failure third."""

    def transcriber(self, path):
        return TRANSCRIPT + " transcribed by the engine."

    def test_a_video_with_no_captions_is_transcribed_when_the_build_may(self):
        downloader = self.downloader([video("aaa")], captions={"aaa": ""})
        manifest = self.ingest(downloader, transcribe_missing=True,
                               transcriber=self.transcriber)
        self.assertEqual(1, len(manifest.ok))
        self.assertEqual(["aaa"], downloader.audio_asked)

    def test_the_page_says_it_was_transcribed_rather_than_captioned(self):
        self.ingest(self.downloader([video("aaa")], captions={"aaa": ""}),
                    transcribe_missing=True, transcriber=self.transcriber)
        front, _, _ = parse_frontmatter(self.raw_text(self.raw_pages()[0]))
        self.assertEqual("scribe-v2", front["transcript"])

    def test_captions_win_so_nothing_is_paid_for_twice(self):
        downloader = self.downloader([video("aaa")], captions={"aaa": TRANSCRIPT})
        self.ingest(downloader, transcribe_missing=True, transcriber=self.transcriber)
        self.assertEqual([], downloader.audio_asked)

    def test_a_failed_transcription_fails_loudly(self):
        def transcriber(path):
            raise RuntimeError("no ELEVENLABS_API_KEY in the environment")

        manifest = self.ingest(self.downloader([video("aaa")], captions={"aaa": ""}),
                               transcribe_missing=True, transcriber=transcriber)
        self.assertEqual(1, len(manifest.failed))
        self.assertIn("ELEVENLABS_API_KEY", manifest.failed[0].reason)


class TheArchive(YouTubeArm):
    """A re-run after a Gate 1 edit must not re-fetch what it already has."""

    def test_a_second_run_skips_what_the_first_one_ingested(self):
        downloader = self.downloader([video("aaa")], captions={"aaa": TRANSCRIPT})
        self.ingest(downloader)
        again = self.downloader([video("aaa"), video("bbb")],
                                captions={"aaa": TRANSCRIPT, "bbb": TRANSCRIPT + " b"})
        manifest = self.ingest(again)
        self.assertEqual(1, len(manifest.ok))
        self.assertEqual(1, len(manifest.duplicate))
        self.assertEqual(["bbb"], again.captions_asked)

    def test_the_archive_is_a_file_inside_the_brain(self):
        self.ingest(self.downloader([video("aaa")], captions={"aaa": TRANSCRIPT}))
        self.assertTrue(os.path.isfile(ingest_youtube.archive_path(self.brain)))

    def test_a_video_that_failed_is_not_archived_so_a_re_run_retries_it(self):
        self.ingest(self.downloader([video("aaa")], captions={"aaa": ""}))
        with open(ingest_youtube.archive_path(self.brain), encoding="utf-8") as handle:
            self.assertNotIn("aaa", handle.read())

    def test_raw_pages_are_never_overwritten_by_a_re_run(self):
        self.ingest(self.downloader([video("aaa")], captions={"aaa": TRANSCRIPT}))
        before = self.raw_text(self.raw_pages()[0])
        self.ingest(self.downloader([video("aaa")], captions={"aaa": "different text"}))
        self.assertEqual(before, self.raw_text(self.raw_pages()[0]))


class SelfUpdate(YouTubeArm):
    """A pinned yt-dlp breaks; the prototype found that the hard way."""

    def test_the_update_note_lands_in_the_build_log(self):
        self.ingest(self.downloader([video("aaa")], captions={"aaa": TRANSCRIPT}))
        self.assertIn("yt-dlp", self.log())

    def test_a_successful_update_is_reported_with_the_version(self):
        note = ingest_youtube.self_update(_FakeYtDlp(), updater=lambda: True)
        self.assertIn("2026.08.01", note)
        self.assertIn("updated", note)

    def test_an_update_that_cannot_run_never_stops_the_arm(self):
        def updater():
            raise RuntimeError("not a binary install")

        note = ingest_youtube.self_update(_FakeYtDlp(), updater=updater)
        self.assertIn("pip install -U yt-dlp", note)

    def test_an_install_with_no_updater_at_all_says_how_to_update_by_hand(self):
        self.assertIn("pip install -U yt-dlp", ingest_youtube.self_update(_FakeYtDlp()))


class _FakeYtDlp(object):
    class version(object):
        __version__ = "2026.08.01"


class MissingLibrary(YouTubeArm):
    """No yt-dlp on the machine is a named record, never a traceback."""

    def test_the_pip_line_is_the_reason_on_the_record(self):
        class NoYtDlp(object):
            update_note = ""

            def videos(self, target, limit=None):
                raise ImportError("No module named 'yt_dlp'")

        manifest = self.ingest(NoYtDlp())
        self.assertEqual(1, len(manifest.failed))
        self.assertIn("pip install yt-dlp", manifest.failed[0].reason)


class NothingFound(YouTubeArm):
    """A search or channel with no videos is a dead end, said out loud."""

    def test_a_target_with_no_videos_is_a_failed_record(self):
        manifest = self.ingest(self.downloader([]))
        self.assertEqual(1, len(manifest.failed))
        self.assertTrue(manifest.whole_corpus_failed)


class CommandLine(YouTubeArm):
    """`python3 ingest_youtube.py <target> --into <brain>`."""

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            return ingest_youtube.main(["ingest_youtube.py"] + list(args)), out.getvalue()

    def test_missing_arguments_exit_two(self):
        self.assertEqual(2, self.run_cli("https://youtube.com/@baker")[0])
        self.assertEqual(2, self.run_cli("--into", self.brain)[0])

    def test_a_bad_limit_exits_two(self):
        self.assertEqual(2, self.run_cli("x", "--into", self.brain, "--limit", "lots")[0])

    def test_the_summary_is_printed_and_json_is_available(self):
        class NoVideos(object):
            update_note = ""

            def videos(self, target, limit=None):
                return []

        manifest = ingest_youtube.ingest(["x"], self.brain, downloader=NoVideos())
        self.assertIn("0 sources ingested", manifest.summary())
        self.assertEqual(1, json.loads(json.dumps(manifest.as_dict()))["counts"]["failed"])


if __name__ == "__main__":
    unittest.main()
