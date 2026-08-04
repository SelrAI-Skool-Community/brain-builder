"""Figures are cross-checked before they become citable wiki facts (spec.md §6).

ASR corrupts exactly the names and figures that matter, and a corrupted figure
in a brain is worse than a missing one: it is stated with the same flat
certainty as a true one. So every number a page carries is checked against the
arithmetic sitting around it, and a bare figure with no unit is flagged as the
provenance gap it is — pages note the scale of their data, not just its source.
"""
import contextlib
import io
import json
import os
import unittest

from brainkit import BrainOnDisk, page

import verify_numbers
from scaffold import scaffold_brain


def kinds(text):
    return sorted(finding.kind for finding in verify_numbers.verify(text))


class Arithmetic(unittest.TestCase):
    """A figure that contradicts the sum next to it is the one worth catching."""

    def test_a_percentage_of_a_total_that_does_not_compute_is_an_error(self):
        self.assertEqual(["arithmetic"], kinds("20 % of 300 is 45 loaves."))

    def test_the_same_sentence_with_the_right_answer_passes(self):
        self.assertEqual([], kinds("20 % of 300 is 60 loaves."))

    def test_a_stated_sum_is_checked(self):
        self.assertEqual(["arithmetic"], kinds("40 plus 30 is 80 minutes."))
        self.assertEqual([], kinds("40 plus 30 is 70 minutes."))

    def test_the_arithmetic_operators_are_read_as_well_as_the_words(self):
        self.assertEqual(["arithmetic"], kinds("The bake is 40 + 30 = 80 minutes."))

    def test_a_ratio_restated_as_a_percentage_is_checked(self):
        self.assertEqual(["arithmetic"], kinds("8 out of 191 links dangled (12 %)."))
        self.assertEqual([], kinds("8 out of 191 links dangled (4 %)."))

    def test_a_reversed_range_is_an_error_because_one_end_is_wrong(self):
        self.assertEqual(["range"], kinds("Bake between 250 and 200 degrees."))
        self.assertEqual([], kinds("Bake between 200 and 250 degrees."))

    def test_the_message_says_what_was_expected(self):
        finding = verify_numbers.verify("20 % of 300 is 45 loaves.")[0]
        self.assertIn("60", finding.message)
        self.assertEqual("error", finding.severity)


class SpokenNumbers(unittest.TestCase):
    """The ASR failure shape: the words and the digits disagree."""

    def test_a_digit_that_contradicts_the_word_beside_it_is_an_error(self):
        self.assertEqual(["spoken"], kinds("He proofs it for fifteen (50) minutes."))

    def test_agreement_passes(self):
        self.assertEqual([], kinds("He proofs it for fifteen (15) minutes."))

    def test_compound_number_words_are_read(self):
        self.assertEqual(250, verify_numbers.words_to_number("two hundred and fifty"))
        self.assertEqual(15, verify_numbers.words_to_number("fifteen"))
        self.assertIsNone(verify_numbers.words_to_number("sourdough"))


class ScaleAndContext(unittest.TestCase):
    """A figure with no unit is a figure whose scale the page never noted."""

    def test_a_bare_figure_is_flagged_as_unscaled(self):
        self.assertEqual(["unscaled"], kinds("The oven holds 250."))

    def test_a_figure_with_its_unit_attached_passes(self):
        self.assertEqual([], kinds("The oven holds 250 grams."))

    def test_a_currency_figure_passes(self):
        self.assertEqual([], kinds("The run cost $1,200."))

    def test_a_percentage_passes(self):
        self.assertEqual([], kinds("Hydration runs at 70 % for most flours."))

    def test_a_year_is_not_a_measurement(self):
        self.assertEqual([], kinds("The method dates to 1997."))

    def test_small_counts_are_left_alone(self):
        self.assertEqual([], kinds("There are 3."))

    def test_an_unscaled_figure_is_a_warning_not_a_build_stopper(self):
        self.assertEqual("warn", verify_numbers.verify("The oven holds 250.")[0].severity)


class BrainWithPages(BrainOnDisk):
    """A scaffolded brain whose wiki pages the test writes."""

    def setUp(self):
        super(BrainWithPages, self).setUp()
        self.brain = scaffold_brain(title="Test Brain", at=self.tmp)
        self.write(self.brain, "index.md", page(
            "# Test Brain\n\n- [Hydration](wiki/hydration.md) — 70 % baseline.\n"
            "\n## Known gaps\n\n- Everything else.\n",
            type="index", slug="test-brain", title="Test Brain",
            domain="Testing.", kind="subject", stance="advisor"))

    def wiki(self, name, body, **frontmatter):
        front = dict(type="concept", title=name)
        front.update(frontmatter)
        return self.write(self.brain, "wiki/" + name + ".md", page(body, **front))


class Pages(BrainWithPages):
    """Run across a brain: the wiki, its index, and where each figure came from."""

    def test_a_clean_brain_reports_nothing(self):
        self.wiki("hydration", "# Hydration\n\nHydration runs at 70 % of flour weight.\n",
                  sources="raw/notes.md")
        report = verify_numbers.verify_brain(self.brain)
        self.assertEqual([], report.findings)
        self.assertIn("no figure", report.summary())

    def test_a_bad_figure_is_reported_against_the_page_that_carries_it(self):
        self.wiki("hydration", "# Hydration\n\n20 % of 300 is 45 grams.\n",
                  sources="raw/notes.md")
        report = verify_numbers.verify_brain(self.brain)
        self.assertEqual(1, len(report.findings))
        self.assertEqual("wiki/hydration.md", report.findings[0].source)

    def test_a_page_carrying_figures_with_no_provenance_is_flagged(self):
        """Per-page provenance: a number is only citable if the page says where from."""
        self.wiki("hydration", "# Hydration\n\nThe starter doubles in 480 minutes.\n")
        kinds_found = [finding.kind for finding in
                       verify_numbers.verify_brain(self.brain).findings]
        self.assertIn("unsourced", kinds_found)

    def test_a_page_with_no_figures_needs_no_provenance_note(self):
        self.wiki("shaping", "# Shaping\n\nBuild surface tension without tearing.\n")
        self.assertEqual([], verify_numbers.verify_brain(self.brain).findings)

    def test_raw_is_not_verified_because_it_is_the_source_not_the_claim(self):
        self.write(self.brain, "raw/notes.md", "---\ntype: source\n---\n\n20 % of 300 is 45.\n")
        self.assertEqual([], verify_numbers.verify_brain(self.brain).findings)

    def test_the_summary_lands_in_the_build_log(self):
        self.wiki("hydration", "# Hydration\n\n20 % of 300 is 45 grams.\n",
                  sources="raw/notes.md")
        verify_numbers.verify_brain(self.brain, log=True)
        with open(os.path.join(self.brain, "log.md"), encoding="utf-8") as handle:
            self.assertIn("verify", handle.read())


class CommandLine(BrainWithPages):
    """`python3 verify_numbers.py <brain>`."""

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            return verify_numbers.main(["verify_numbers.py"] + list(args)), out.getvalue()

    def test_a_clean_brain_exits_zero(self):
        self.wiki("hydration", "# Hydration\n\n70 % of flour weight.\n",
                  sources="raw/notes.md")
        self.assertEqual(0, self.run_cli(self.brain)[0])

    def test_a_contradicted_figure_exits_one_so_the_build_stops_and_looks(self):
        self.wiki("hydration", "# Hydration\n\n20 % of 300 is 45 grams.\n",
                  sources="raw/notes.md")
        code, out = self.run_cli(self.brain)
        self.assertEqual(1, code)
        self.assertIn("wiki/hydration.md", out)

    def test_warnings_alone_do_not_stop_a_build(self):
        self.wiki("hydration", "# Hydration\n\nThe oven holds 250.\n",
                  sources="raw/notes.md")
        self.assertEqual(0, self.run_cli(self.brain)[0])

    def test_json_gives_the_build_the_findings(self):
        self.wiki("hydration", "# Hydration\n\n20 % of 300 is 45 grams.\n",
                  sources="raw/notes.md")
        code, out = self.run_cli(self.brain, "--json")
        self.assertEqual(1, code)
        self.assertEqual(1, len(json.loads(out)["findings"]))

    def test_no_arguments_exit_two(self):
        self.assertEqual(2, self.run_cli()[0])


if __name__ == "__main__":
    unittest.main()
