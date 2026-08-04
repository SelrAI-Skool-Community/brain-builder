"""The one transcription fallback both video-shaped and audio-shaped arms feed.

Two things are under test and neither of them is the network. The cost estimate,
because it is the number the member approves at Gate 2 and the spec says it
surfaces exactly once (spec.md §6). And the engine seam, because the arms have
to be able to run their whole pipeline against a stub with no API key present.
"""
import contextlib
import io
import unittest

import brainkit  # noqa: F401 — puts the skill's scripts/ on the import path

import transcribe


class Durations(unittest.TestCase):
    """Feeds state duration as seconds or as a clock, and the estimate needs both."""

    def test_bare_seconds_are_seconds(self):
        self.assertEqual(3600, transcribe.parse_duration("3600"))
        self.assertEqual(90, transcribe.parse_duration(90))

    def test_a_clock_becomes_seconds(self):
        self.assertEqual(3723, transcribe.parse_duration("1:02:03"))
        self.assertEqual(90, transcribe.parse_duration("01:30"))

    def test_nonsense_is_zero_rather_than_an_exception(self):
        """A feed with a junk duration still gets built; the estimate just misses it."""
        self.assertEqual(0, transcribe.parse_duration("soon"))
        self.assertEqual(0, transcribe.parse_duration(None))


class CostEstimate(unittest.TestCase):
    """The Gate 2 line: hours, engine, dollars, once."""

    def test_scribe_is_priced_at_twenty_two_cents_an_hour(self):
        estimate = transcribe.estimate([3600, 1800])
        self.assertEqual(1.5, estimate.hours)
        self.assertEqual(0.33, estimate.cost)

    def test_the_gate_line_names_the_hours_the_engine_and_the_money(self):
        line = transcribe.estimate([3600, 1800]).line()
        self.assertIn("1.5 hours", line)
        self.assertIn("Scribe", line)
        self.assertIn("$0.33", line)

    def test_nothing_to_transcribe_still_says_so_out_loud(self):
        """The line that stops a surprise on the arms that do transcribe."""
        estimate = transcribe.estimate([])
        self.assertEqual(0, estimate.cost)
        self.assertIn("none", estimate.line().lower())
        self.assertIn("$0", estimate.line())

    def test_the_cheap_mode_is_priced_and_carries_its_warning(self):
        estimate = transcribe.estimate([3600], engine="groq")
        self.assertLess(estimate.cost, 0.22)
        self.assertIn("never quote", estimate.line().lower())

    def test_an_unknown_engine_is_refused_rather_than_guessed(self):
        with self.assertRaises(ValueError):
            transcribe.estimate([3600], engine="whisper")

    def test_whisper_family_engines_are_not_on_offer_at_all(self):
        """Rejected for inventing fluent sentences during silences (spec.md §6)."""
        self.assertNotIn("whisper", " ".join(transcribe.ENGINES))


class TranscribingOneFile(unittest.TestCase):
    """The arms call this; the tests hand it a stub instead of an API."""

    def poster(self, payload=None, record=None):
        def post(url, headers, path, model_id):
            if record is not None:
                record.update({"url": url, "headers": headers, "path": path,
                               "model_id": model_id})
            return payload if payload is not None else {"text": "The transcript."}
        return post

    def test_it_returns_the_text_the_engine_sent_back(self):
        self.assertEqual("The transcript.", transcribe.transcribe(
            "/tmp/ep1.mp3", api_key="k", poster=self.poster()))

    def test_it_sends_the_key_and_the_model_the_engine_declares(self):
        seen = {}
        transcribe.transcribe("/tmp/ep1.mp3", api_key="k", poster=self.poster(record=seen))
        self.assertEqual("k", seen["headers"]["xi-api-key"])
        self.assertEqual("scribe_v2", seen["model_id"])
        self.assertIn("elevenlabs", seen["url"])

    def test_a_missing_key_fails_loudly_and_names_the_variable_to_set(self):
        with self.assertRaises(transcribe.TranscriptionError) as caught:
            transcribe.transcribe("/tmp/ep1.mp3", api_key="", environ={},
                                  poster=self.poster())
        self.assertIn("ELEVENLABS_API_KEY", str(caught.exception))

    def test_the_key_is_read_from_the_environment_when_not_passed(self):
        self.assertEqual("The transcript.", transcribe.transcribe(
            "/tmp/ep1.mp3", environ={"ELEVENLABS_API_KEY": "k"}, poster=self.poster()))

    def test_an_empty_response_is_a_failure_not_an_empty_transcript(self):
        with self.assertRaises(transcribe.TranscriptionError):
            transcribe.transcribe("/tmp/ep1.mp3", api_key="k",
                                  poster=self.poster(payload={"text": "   "}))

    def test_the_cheap_engine_uses_its_own_key_and_endpoint(self):
        seen = {}
        transcribe.transcribe("/tmp/ep1.mp3", engine="groq",
                              environ={"GROQ_API_KEY": "g"},
                              poster=self.poster(record=seen))
        self.assertIn("groq", seen["url"])


class CommandLine(unittest.TestCase):
    """`transcribe.py --estimate …` is what Gate 2 quotes."""

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            return transcribe.main(["transcribe.py"] + list(args)), out.getvalue()

    def test_estimating_prints_the_gate_line(self):
        code, out = self.run_cli("--estimate", "3600", "1800")
        self.assertEqual(0, code)
        self.assertIn("$0.33", out)

    def test_estimating_nothing_prints_the_no_cost_line(self):
        code, out = self.run_cli("--estimate")
        self.assertEqual(0, code)
        self.assertIn("none", out.lower())

    def test_an_unknown_engine_exits_two_with_usage(self):
        self.assertEqual(2, self.run_cli("--estimate", "3600", "--engine", "whisper")[0])

    def test_no_arguments_exits_two(self):
        self.assertEqual(2, self.run_cli()[0])


if __name__ == "__main__":
    unittest.main()
