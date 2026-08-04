"""Corpus-level dedup: the same talk, told again in another source (spec.md §6).

`ingest_local` already drops byte-identical text. What it cannot see is the
failure the prototype hit: a "best of" compilation that restates three episodes
almost verbatim, so the wiki counts the same claim four times and reads it as
four independent sources agreeing.

This pass reports rather than deletes, because `raw/` is immutable — the build
uses the report to distil once, not to throw material away.
"""
import contextlib
import io
import json
import os
import unittest

from brainkit import BrainOnDisk

import dedup_corpus
from scaffold import scaffold_brain

EPISODE = ("hydration is the ratio of water to flour measured by weight and it "
           "decides how open the crumb gets when the loaf finally bakes out in "
           "a properly steamed oven at two hundred and fifty degrees which is "
           "hotter than most home bakers ever push their equipment towards")

OTHER = ("shaping a boule is about building surface tension across the skin of "
         "the dough without tearing it so the loaf holds its height through the "
         "final proof rather than spreading sideways across the baking stone in "
         "the way a slack under shaped dough always eventually will")

REWORDED = EPISODE.replace("decides", "determines").replace("finally", "eventually")


class Comparison(unittest.TestCase):
    """The measure: how much of the smaller source is inside the larger."""

    def test_identical_text_is_wholly_contained(self):
        overlap = dedup_corpus.compare(EPISODE, EPISODE)
        self.assertEqual(1.0, overlap.containment)
        self.assertEqual(1.0, overlap.jaccard)

    def test_unrelated_sources_share_nothing(self):
        self.assertEqual(0.0, dedup_corpus.compare(EPISODE, OTHER).containment)

    def test_a_compilation_contains_the_episode_it_restates(self):
        overlap = dedup_corpus.compare(EPISODE, EPISODE + " " + OTHER)
        self.assertGreater(overlap.containment, 0.9)
        self.assertLess(overlap.jaccard, 0.9)

    def test_a_lightly_reworded_retelling_still_reads_as_the_same_source(self):
        self.assertGreater(dedup_corpus.compare(EPISODE, REWORDED).jaccard, 0.6)

    def test_a_source_too_short_to_shingle_is_compared_as_nothing(self):
        self.assertEqual(0.0, dedup_corpus.compare("too short", EPISODE).containment)


class FindingPairs(unittest.TestCase):
    """What the build is told: which sources restate which."""

    def pairs(self, **sources):
        return dedup_corpus.find_near_duplicates(sorted(sources.items()))

    def test_a_compilation_is_reported_against_the_source_it_repeats(self):
        pairs = self.pairs(**{"raw/episode.md": EPISODE,
                              "raw/compilation.md": EPISODE + " " + OTHER,
                              "raw/shaping.md": OTHER})
        restated = [pair for pair in pairs if pair.duplicate == "raw/episode.md"]
        self.assertEqual(1, len(restated))
        self.assertEqual("raw/compilation.md", restated[0].original)

    def test_the_verdict_separates_a_retelling_from_a_containing_compilation(self):
        contained = self.pairs(**{"raw/a.md": EPISODE,
                                  "raw/b.md": EPISODE + " " + OTHER})
        self.assertEqual("contained", contained[0].verdict)
        retold = self.pairs(**{"raw/a.md": EPISODE, "raw/b.md": REWORDED})
        self.assertEqual("near-duplicate", retold[0].verdict)

    def test_unrelated_sources_produce_no_pairs(self):
        self.assertEqual([], self.pairs(**{"raw/a.md": EPISODE, "raw/b.md": OTHER}))

    def test_raising_the_threshold_makes_it_stricter(self):
        pages = [("raw/a.md", EPISODE), ("raw/b.md", REWORDED)]
        self.assertTrue(dedup_corpus.find_near_duplicates(pages, threshold=0.6))
        self.assertFalse(dedup_corpus.find_near_duplicates(pages, threshold=0.99))


class AcrossABrain(BrainOnDisk):
    """Run over a real `raw/`, frontmatter and all."""

    def setUp(self):
        super(AcrossABrain, self).setUp()
        self.brain = scaffold_brain(title="Test Brain", at=self.tmp)

    def raw(self, name, text):
        self.write(self.brain, "raw/" + name,
                   "---\ntype: source\nsource: {}\n---\n\n{}\n".format(name, text))

    def log(self):
        with open(os.path.join(self.brain, "log.md"), encoding="utf-8") as handle:
            return handle.read()

    def test_it_reads_raw_pages_without_counting_their_frontmatter(self):
        self.raw("episode.md", EPISODE)
        self.raw("compilation.md", EPISODE + " " + OTHER)
        report = dedup_corpus.scan(self.brain)
        self.assertEqual(1, len(report.pairs))
        self.assertIn("raw/episode.md", report.summary())

    def test_a_corpus_with_no_repetition_says_so(self):
        self.raw("episode.md", EPISODE)
        self.raw("shaping.md", OTHER)
        self.assertEqual([], dedup_corpus.scan(self.brain).pairs)
        self.assertIn("no near-duplicates", dedup_corpus.scan(self.brain).summary())

    def test_the_finding_is_written_to_the_build_log(self):
        self.raw("episode.md", EPISODE)
        self.raw("compilation.md", EPISODE + " " + OTHER)
        dedup_corpus.scan(self.brain, log=True)
        self.assertIn("near-duplicate", self.log())

    def test_it_never_edits_or_removes_a_raw_page(self):
        """`raw/` is immutable — this pass reports, the distillation acts."""
        self.raw("episode.md", EPISODE)
        self.raw("compilation.md", EPISODE + " " + OTHER)
        before = sorted(os.listdir(os.path.join(self.brain, "raw")))
        dedup_corpus.scan(self.brain, log=True)
        self.assertEqual(before, sorted(os.listdir(os.path.join(self.brain, "raw"))))


class CommandLine(AcrossABrain):
    """`python3 dedup_corpus.py <brain>`."""

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            return dedup_corpus.main(["dedup_corpus.py"] + list(args)), out.getvalue()

    def test_it_reports_and_exits_zero_because_repetition_is_not_an_error(self):
        self.raw("episode.md", EPISODE)
        self.raw("compilation.md", EPISODE + " " + OTHER)
        code, out = self.run_cli(self.brain)
        self.assertEqual(0, code)
        self.assertIn("raw/compilation.md", out)

    def test_json_gives_the_build_the_pairs_to_act_on(self):
        self.raw("episode.md", EPISODE)
        self.raw("compilation.md", EPISODE + " " + OTHER)
        code, out = self.run_cli(self.brain, "--json")
        self.assertEqual(1, len(json.loads(out)["pairs"]))

    def test_a_missing_brain_exits_one(self):
        self.assertEqual(1, self.run_cli(os.path.join(self.tmp, "nope"))[0])

    def test_no_arguments_exit_two(self):
        self.assertEqual(2, self.run_cli()[0])


if __name__ == "__main__":
    unittest.main()
