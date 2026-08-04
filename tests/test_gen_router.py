"""The generated SKILL.md router carries the whole contract (spec.md §3)."""
import contextlib
import io
import os
import unittest

from brainkit import BrainOnDisk, flatten, page

from brain_contract import parse_frontmatter
from gen_router import generate_router, read_brain_meta, write_router
from lint import lint_brain


class RouterGeneration(BrainOnDisk):
    """Regenerable, self-contained, and rooted at a real absolute path."""

    def read(self, path):
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_writing_the_router_creates_skill_md_at_the_brain_root(self):
        brain = self.minimal_brain()
        path = write_router(brain)
        self.assertEqual(os.path.join(brain, "SKILL.md"), path)
        self.assertTrue(os.path.isfile(path))

    def test_regenerating_rewrites_in_place_and_is_byte_identical(self):
        brain = self.minimal_brain()
        self.assertEqual(self.read(write_router(brain)), self.read(write_router(brain)))

    def test_regenerating_replaces_a_stale_router_rather_than_appending(self):
        brain = self.minimal_brain()
        self.write(brain, "SKILL.md", "---\nname: stale\n---\n\nOld router body.\n")
        text = self.read(write_router(brain))
        self.assertNotIn("Old router body", text)
        self.assertNotIn("stale", text)

    def test_the_router_records_the_brains_absolute_root(self):
        brain = self.minimal_brain()
        frontmatter, body, _ = parse_frontmatter(generate_router(brain))
        self.assertEqual(os.path.abspath(brain), frontmatter["metadata"]["brain_root"])
        self.assertIn(os.path.abspath(brain), body)

    def test_a_generated_router_passes_lint(self):
        brain = self.minimal_brain()
        write_router(brain)
        report = lint_brain(brain)
        self.assertTrue(report.ok, report.errors)

    def test_a_folder_without_an_index_cannot_produce_a_router(self):
        brain = self.minimal_brain()
        os.remove(os.path.join(brain, "index.md"))
        with self.assertRaises(ValueError):
            generate_router(brain)


class BrainMetadata(BrainOnDisk):
    """Metadata comes off the brain itself — `index.md` frontmatter."""

    def test_metadata_is_read_from_index_frontmatter(self):
        brain = self.minimal_brain(
            slug="sourdough", title="Sourdough", domain="Baking bread.",
            kind="business", stance="advisor")
        meta = read_brain_meta(brain)
        self.assertEqual("sourdough", meta.slug)
        self.assertEqual("Sourdough", meta.title)
        self.assertEqual("Baking bread.", meta.domain)
        self.assertEqual("business", meta.kind)

    def test_a_missing_slug_falls_back_to_the_folder_name(self):
        brain = os.path.join(self.tmp, "fallback-brain")
        os.makedirs(os.path.join(brain, "wiki"))
        self.write(brain, "index.md", page("# X\n\n## Known gaps\n\n- All.\n", type="index"))
        meta = read_brain_meta(brain)
        self.assertEqual("fallback-brain", meta.slug)
        self.assertEqual("fallback-brain", meta.title)
        self.assertEqual("subject", meta.kind)

    def test_an_explicit_kind_overrides_the_one_on_disk(self):
        brain = self.minimal_brain(kind="subject")
        text = generate_router(brain, kind="business")
        frontmatter, _, _ = parse_frontmatter(text)
        self.assertEqual("business", frontmatter["metadata"]["kind"])

    def test_overlays_are_detected_from_disk_not_declared(self):
        brain = self.minimal_brain()
        self.assertEqual([], read_brain_meta(brain).overlays)
        self.write(brain, "persona/voice.md", page("# Voice\n", type="voice"))
        self.write(brain, "standing/policy.md", page("# Policy\n", type="policy"))
        self.assertEqual(["persona", "standing"], read_brain_meta(brain).overlays)


class FrontmatterContract(BrainOnDisk):
    """The description fires the skill — and carries the never-glob clause."""

    def setUp(self):
        super().setUp()
        self.brain = self.minimal_brain(slug="sourdough", title="Sourdough",
                                        domain="Baking sourdough bread at home.")
        self.frontmatter, self.body, present = parse_frontmatter(generate_router(self.brain))
        self.assertTrue(present)

    def test_the_skill_is_named_for_the_brain(self):
        self.assertEqual("sourdough", self.frontmatter["name"])

    def test_the_description_carries_the_domain_so_it_fires_from_natural_language(self):
        self.assertIn("Sourdough", self.frontmatter["description"])
        self.assertIn("Baking sourdough bread at home", self.frontmatter["description"])

    def test_the_description_itself_carries_the_start_at_index_never_glob_clause(self):
        description = self.frontmatter["description"].lower()
        self.assertIn("index.md", description)
        self.assertIn("never glob", description)


class RuleBlocks(BrainOnDisk):
    """All four rule blocks from spec §3, plus write-back and the conflict rule."""

    def setUp(self):
        super().setUp()
        self.brain = self.minimal_brain(slug="sourdough", title="Sourdough")
        self.body = flatten(generate_router(self.brain))

    def assertCarries(self, *phrases):
        for phrase in phrases:
            self.assertIn(flatten(phrase), self.body)

    def test_all_four_rule_blocks_are_present(self):
        self.assertCarries("## navigation", "## stance", "## answering", "## citation")

    def test_navigation_rules(self):
        self.assertCarries(
            "start at `index.md`",       # start at the map
            "never glob",                # never bulk-load
            "2–3 wiki pages",            # the page budget
            "per brain",                 # ... per brain, in stacked sessions
            "once per session",          # index.md loads once, then direct routing
            "direct routing",
            "`raw/` is fenced",          # raw/ opened only for a verbatim quote
            "verbatim quote",
        )

    def test_stance_rules(self):
        self.assertCarries(
            "advisor stance is the default",
            "never relay",               # no middleman
            "here's what the brain says",  # ... banned in every stance
            "banned",
            "one voice per session",
            "extensible",                # never written as a cap of two
        )

    def test_answering_rules(self):
        self.assertCarries(
            "lead with the answer",
            "never narrate retrieval",
            "## known gaps",
            "inside the domain but uncovered",  # when refusal fires
            "out-of-domain",
            "no disclaimer",
            "as-of date",                # fast-volatility facts
            "volatility: fast",
        )

    def test_citation_rules(self):
        self.assertCarries(
            "exactly one",
            "closing `sources` block",
            "wiki/<page>.md",            # brain-relative paths
            "sourdough/wiki/<page>.md",  # slug-prefixed when stacked
            "never cite `raw/`",
            "derived-from-conversation",
        )

    def test_write_back_rules(self):
        self.assertCarries(
            "during the conversation",
            "no staging",
            "no approval gate",
            "announce",
            "log.md",
            "undo is git",
        )

    def test_the_conflict_rule(self):
        self.assertCarries(
            "outrank",
            "standing policies",
            "outward-facing",
            "surface",
            "never silently",
        )


class PerKindAndOverlayRules(BrainOnDisk):
    """Kinds and overlays change the router; nothing else does."""

    def body_for(self, **kwargs):
        kind = kwargs.pop("kind", "subject")
        overlays = kwargs.pop("overlays", ())
        brain = self.minimal_brain(slug=kwargs.pop("slug", "kb"), kind=kind, **kwargs)
        for overlay in overlays:
            self.write(brain, "{}/voice.md".format(overlay), page("# V\n", type="voice"))
        return flatten(generate_router(brain))

    def test_a_subject_brain_carries_the_always_on_sources_rule(self):
        body = self.body_for(kind="subject", slug="subject-kb")
        self.assertIn("every answer grounded in this brain ends with", body)
        self.assertNotIn("only on answers carrying numbers", body)

    def test_a_business_brain_carries_the_conditional_sources_rule(self):
        body = self.body_for(kind="business", slug="business-kb")
        self.assertIn("only on answers carrying numbers", body)
        self.assertIn(flatten("(as of …; canonical …)"), body)

    def test_a_persona_overlay_switches_the_stance_and_loads_the_overlay(self):
        body = self.body_for(kind="persona", slug="persona-kb", overlays=("persona",))
        self.assertIn("persona/voice.md", body)
        self.assertIn("persona/exemplars.md", body)
        self.assertIn("speak as", body)

    def test_without_a_persona_overlay_the_router_says_nothing_about_one(self):
        self.assertNotIn("persona/voice.md", self.body_for(slug="plain-kb"))

    def test_a_standing_overlay_is_routed_like_wiki_pages_and_unfenced(self):
        body = self.body_for(kind="business", slug="standing-kb", overlays=("standing",))
        self.assertIn("standing/", body)
        self.assertIn("unfenced", body)


class CommandLine(BrainOnDisk):
    """`python3 gen_router.py <brain-dir>` is the whole interface."""

    def run_cli(self, *args):
        import gen_router
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return gen_router.main(["gen_router.py"] + list(args))

    def test_the_cli_writes_the_router_and_exits_zero(self):
        brain = self.minimal_brain()
        self.assertEqual(0, self.run_cli(brain))
        with open(os.path.join(brain, "SKILL.md"), encoding="utf-8") as handle:
            self.assertIn("## Navigation", handle.read())

    def test_the_cli_takes_a_kind_override(self):
        brain = self.minimal_brain(kind="subject")
        self.assertEqual(0, self.run_cli(brain, "--kind", "business"))
        with open(os.path.join(brain, "SKILL.md"), encoding="utf-8") as handle:
            self.assertIn("kind: business", handle.read())

    def test_the_cli_reports_a_folder_it_cannot_route(self):
        self.assertEqual(1, self.run_cli(os.path.join(self.tmp, "nope")))

    def test_the_cli_rejects_wrong_arity(self):
        self.assertEqual(2, self.run_cli())

    def test_the_cli_rejects_a_kind_flag_with_no_value(self):
        self.assertEqual(2, self.run_cli(self.minimal_brain(), "--kind"))


if __name__ == "__main__":
    unittest.main()
