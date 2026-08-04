"""The fixture brain is the kit's reference example of the contract.

`tests/fixtures/sourdough-baking/` is hand-authored, subject kind, advisor
stance. It exists to be *read* — by a member wanting to know what a brain looks
like, and by these tests, which hold it to the same contract every built brain
is held to.
"""
import os
import shutil
import unittest

from brainkit import FIXTURES_DIR, BrainOnDisk

from brain_contract import parse_frontmatter, read_page
from gen_router import read_brain_meta, write_router
from lint import lint_brain
from verify_numbers import verify_brain

FIXTURE = os.path.join(FIXTURES_DIR, "sourdough-baking")


class FixtureBrain(BrainOnDisk):

    def test_the_fixture_passes_lint_with_no_errors_and_no_warnings(self):
        report = lint_brain(FIXTURE)
        self.assertEqual([], report.errors)
        self.assertEqual([], report.warnings)

    def test_the_fixture_passes_number_verification_clean(self):
        """The self-check that closes every build (spec §5) has nothing to say.

        A reference brain that ships with warnings teaches the warnings are
        noise. Every wiki page here carries `sources:`, which is what chains its
        figures back to `raw/` — the per-chunk attribution of §6, demonstrated
        rather than only checked for.
        """
        report = verify_brain(FIXTURE)
        self.assertEqual([], [finding.line() for finding in report.findings])

    def test_the_fixture_is_a_subject_brain_in_advisor_stance(self):
        meta = read_brain_meta(FIXTURE)
        self.assertEqual("sourdough-baking", meta.slug)
        self.assertEqual("subject", meta.kind)
        self.assertEqual("advisor", meta.stance)
        self.assertEqual([], meta.overlays)

    def test_the_index_one_liners_link_to_every_wiki_page(self):
        index = read_page(FIXTURE, "index.md")
        linked = {target for target in index.links()}
        pages = {"wiki/" + name for name in os.listdir(os.path.join(FIXTURE, "wiki"))}
        self.assertEqual(pages, linked)

    def test_the_wiki_pages_cross_link_to_each_other(self):
        for name in sorted(os.listdir(os.path.join(FIXTURE, "wiki"))):
            with self.subTest(page=name):
                page = read_page(FIXTURE, os.path.join("wiki", name))
                self.assertTrue(page.links(), "{} links to nothing".format(name))

    def test_the_committed_router_is_what_the_generator_produces(self):
        """Regenerate into a copy and diff — modulo each router's own root."""
        copy = os.path.join(self.tmp, "sourdough-baking")
        shutil.copytree(FIXTURE, copy)
        os.remove(os.path.join(copy, "SKILL.md"))
        write_router(copy)
        self.assertEqual(self.rootless(FIXTURE), self.rootless(copy))

    @staticmethod
    def rootless(brain):
        with open(os.path.join(brain, "SKILL.md"), encoding="utf-8") as handle:
            text = handle.read()
        front, _, _ = parse_frontmatter(text)
        return text.replace(front["metadata"]["brain_root"], "<BRAIN_ROOT>")


if __name__ == "__main__":
    unittest.main()
