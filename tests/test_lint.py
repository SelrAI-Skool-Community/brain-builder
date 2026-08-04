"""Lint checks the on-disk brain contract (spec.md §2)."""
import contextlib
import io
import os
import shutil
import unittest

from brainkit import BrainOnDisk, page

from lint import lint_brain


class SkeletonRules(BrainOnDisk):
    """SKILL.md + index.md + wiki/ are mandatory; raw/, log.md, CHANGELOG.md warn."""

    def test_a_complete_brain_passes_with_nothing_to_report(self):
        report = lint_brain(self.minimal_brain())
        self.assertEqual([], report.errors)
        self.assertEqual([], report.warnings)
        self.assertTrue(report.ok)

    def test_missing_mandatory_skeleton_members_fail(self):
        for member in ("SKILL.md", "index.md", "wiki"):
            with self.subTest(member=member):
                brain = self.minimal_brain(slug="missing-" + member.replace(".", "-"))
                target = os.path.join(brain, member)
                shutil.rmtree(target) if os.path.isdir(target) else os.remove(target)
                report = lint_brain(brain)
                self.assertFalse(report.ok)
                self.assertTrue(any(member in e for e in report.errors), report.errors)

    def test_missing_optional_skeleton_members_warn_but_still_pass(self):
        for member in ("raw", "log.md", "CHANGELOG.md"):
            with self.subTest(member=member):
                brain = self.minimal_brain(slug="warn-" + member.replace(".", "-"))
                target = os.path.join(brain, member)
                shutil.rmtree(target) if os.path.isdir(target) else os.remove(target)
                report = lint_brain(brain)
                self.assertTrue(report.ok, report.errors)
                self.assertTrue(any(member in w for w in report.warnings), report.warnings)

    def test_unrecognised_folders_are_ignored_not_errors(self):
        brain = self.minimal_brain()
        self.write(brain, "atlas/map.md", "no frontmatter, unimagined shape\n")
        self.write(brain, "notes.txt", "loose file\n")
        report = lint_brain(brain)
        self.assertTrue(report.ok, report.errors)
        self.assertEqual([], report.warnings)

    def test_a_folder_that_is_not_a_brain_fails_rather_than_crashes(self):
        report = lint_brain(os.path.join(self.tmp, "nowhere"))
        self.assertFalse(report.ok)

    def test_index_must_carry_a_known_gaps_section(self):
        brain = self.minimal_brain()
        self.write(brain, "index.md", page(
            "# Test Brain\n\n- [Concept](wiki/concept.md) — one concept.\n",
            type="index", slug="test-brain", title="Test Brain",
            domain="A brain.", kind="subject", stance="advisor"))
        report = lint_brain(brain)
        self.assertFalse(report.ok)
        self.assertTrue(any("Known gaps" in e for e in report.errors), report.errors)


class FrontmatterRules(BrainOnDisk):
    """OKF conformance: a `type` field on every page, reserved index.md / log.md."""

    def test_a_wiki_page_without_frontmatter_fails(self):
        brain = self.minimal_brain()
        self.write(brain, "wiki/concept.md", "# Concept\n\nNo frontmatter.\n")
        report = lint_brain(brain)
        self.assertFalse(report.ok)
        self.assertTrue(any("frontmatter" in e for e in report.errors), report.errors)

    def test_a_wiki_page_without_a_type_field_fails(self):
        brain = self.minimal_brain()
        self.write(brain, "wiki/concept.md", page("# Concept\n", title="Concept"))
        report = lint_brain(brain)
        self.assertFalse(report.ok)
        self.assertTrue(any("type" in e for e in report.errors), report.errors)

    def test_reserved_files_must_carry_their_reserved_type(self):
        brain = self.minimal_brain()
        self.write(brain, "log.md", page("# Log\n", type="notes"))
        report = lint_brain(brain)
        self.assertFalse(report.ok)
        self.assertTrue(any("log.md" in e and "log" in e for e in report.errors), report.errors)

    def test_reserved_names_may_not_be_reused_inside_the_wiki(self):
        brain = self.minimal_brain()
        self.write(brain, "wiki/index.md", page("# Section\n", type="index"))
        report = lint_brain(brain)
        self.assertFalse(report.ok)
        self.assertTrue(any("reserved" in e for e in report.errors), report.errors)

    def test_raw_pages_are_exempt_from_frontmatter_rules(self):
        brain = self.minimal_brain()
        self.write(brain, "raw/transcript.md", "Bare transcript text, no frontmatter.\n")
        self.assertTrue(lint_brain(brain).ok)

    def test_overlay_pages_are_exempt_because_they_load_whole(self):
        """`persona/` and `standing/` are loaded whole, not routed as OKF pages."""
        brain = self.minimal_brain()
        self.write(brain, "standing/policy.md", "# Policy\n\nNo frontmatter.\n")
        self.write(brain, "persona/voice.md", "# Voice\n\nNo frontmatter either.\n")
        self.assertTrue(lint_brain(brain).ok, lint_brain(brain).errors)

    def test_overlay_pages_are_still_link_checked(self):
        brain = self.minimal_brain()
        self.write(brain, "standing/policy.md", "# Policy\n\nSee [gone](missing.md).\n")
        report = lint_brain(brain)
        self.assertFalse(report.ok)
        self.assertTrue(any("missing.md" in e for e in report.errors), report.errors)


class FreshnessRules(BrainOnDisk):
    """Freshness frontmatter (spec §2) is optional, but validated when present."""

    def test_valid_freshness_frontmatter_passes(self):
        brain = self.minimal_brain()
        self.write(brain, "wiki/concept.md", page(
            "# Concept\n", type="concept", as_of="2026-02-01",
            volatility="fast", canonical="https://example.com/prices"))
        self.assertTrue(lint_brain(brain).ok)

    def test_an_unknown_volatility_fails(self):
        brain = self.minimal_brain()
        self.write(brain, "wiki/concept.md", page(
            "# Concept\n", type="concept", volatility="quick"))
        report = lint_brain(brain)
        self.assertFalse(report.ok)
        self.assertTrue(any("volatility" in e for e in report.errors), report.errors)

    def test_a_malformed_as_of_date_fails(self):
        brain = self.minimal_brain()
        self.write(brain, "wiki/concept.md", page(
            "# Concept\n", type="concept", as_of="last tuesday"))
        report = lint_brain(brain)
        self.assertFalse(report.ok)
        self.assertTrue(any("as_of" in e for e in report.errors), report.errors)

    def test_fast_facts_without_an_as_of_date_warn_but_pass(self):
        """The fields are optional (spec §2) — the pairing is advice, not a rule."""
        brain = self.minimal_brain()
        self.write(brain, "wiki/concept.md", page(
            "# Concept\n", type="concept", volatility="fast"))
        report = lint_brain(brain)
        self.assertTrue(report.ok, report.errors)
        self.assertTrue(any("as_of" in w for w in report.warnings), report.warnings)

    def test_an_empty_canonical_fails(self):
        brain = self.minimal_brain()
        self.write(brain, "wiki/concept.md", page(
            "# Concept\n", type="concept", canonical=""))
        report = lint_brain(brain)
        self.assertFalse(report.ok)
        self.assertTrue(any("canonical" in e for e in report.errors), report.errors)


class LinkRules(BrainOnDisk):
    """Wiki links must resolve — 4.2% dangled in the prototype."""

    def test_a_dangling_wiki_link_fails(self):
        brain = self.minimal_brain()
        self.write(brain, "wiki/concept.md", page(
            "# Concept\n\nSee [the other one](other.md).\n", type="concept"))
        report = lint_brain(brain)
        self.assertFalse(report.ok)
        self.assertTrue(any("other.md" in e for e in report.errors), report.errors)

    def test_links_that_resolve_pass_including_anchors_and_parent_paths(self):
        brain = self.minimal_brain()
        self.write(brain, "wiki/concept.md", page(
            "# Concept\n\nSee [siblings](sibling.md#part), [home](../index.md), "
            "[the web](https://example.com), [below](#part).\n", type="concept"))
        self.write(brain, "wiki/sibling.md", page("# Sibling\n\n## part\n", type="concept"))
        self.assertTrue(lint_brain(brain).ok, lint_brain(brain).errors)

    def test_links_out_of_the_brain_fail(self):
        brain = self.minimal_brain()
        self.write(brain, "wiki/concept.md", page(
            "# Concept\n\nSee [escape](../../elsewhere.md).\n", type="concept"))
        report = lint_brain(brain)
        self.assertFalse(report.ok)
        self.assertTrue(any("outside" in e for e in report.errors), report.errors)

    def test_dangling_links_inside_raw_are_not_checked(self):
        brain = self.minimal_brain()
        self.write(brain, "raw/source.md", "Quoted [link](nowhere.md) from the source.\n")
        self.assertTrue(lint_brain(brain).ok)


class CommandLine(BrainOnDisk):
    """`python3 lint.py <brain-dir>` — exit 0 pass, 1 fail, warnings don't count."""

    def run_cli(self, *args):
        import lint
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            return lint.main(["lint.py"] + list(args)), out.getvalue()

    def test_a_valid_brain_exits_zero(self):
        code, out = self.run_cli(self.minimal_brain())
        self.assertEqual(0, code)
        self.assertIn("valid brain", out)

    def test_warnings_alone_still_exit_zero(self):
        brain = self.minimal_brain()
        os.remove(os.path.join(brain, "CHANGELOG.md"))
        code, out = self.run_cli(brain)
        self.assertEqual(0, code)
        self.assertIn("WARN", out)

    def test_an_invalid_brain_exits_one_and_says_why(self):
        brain = self.minimal_brain()
        os.remove(os.path.join(brain, "index.md"))
        code, out = self.run_cli(brain)
        self.assertEqual(1, code)
        self.assertIn("ERROR", out)
        self.assertIn("index.md", out)

    def test_wrong_arity_exits_two(self):
        self.assertEqual(2, self.run_cli()[0])


if __name__ == "__main__":
    unittest.main()
