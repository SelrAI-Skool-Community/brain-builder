"""Two brains attached at once, and the contract that keeps them apart (spec §3).

`tests/fixtures/marlow-quist/` (persona) and `tests/fixtures/rye-lane-bakery/`
(business) are hand-authored reference brains, and they are a **pair**: the
stacking contract is the thing that only shows up when more than one brain is
attached, so it needs more than one brain to check.

Both fixtures are **invented**. Marlow Quist is not a real person and Rye Lane
Bakery is not a real business — a persona fixture built from a real person's
words would be exactly the redistribution the rights stance forbids
(docs/rights.md).

What a unit test can hold is the static half of the contract: that each brain
declares itself distinctly enough to route on, that each router carries its
kind's rules and its slug-prefixed citation paths, and that the shared
one-voice, page-budget and conflict rules survive in both. The live half — a
real session with both attached, routing correctly with no misroutes — is
recorded in `docs/research/stacking-verification.md`.
"""
import os
import re
import shutil
import unittest

from brainkit import FIXTURES_DIR, BrainOnDisk, flatten

from brain_contract import parse_frontmatter, read_page
from gen_router import read_brain_meta, write_router
from lint import lint_brain

PERSONA = os.path.join(FIXTURES_DIR, "marlow-quist")
BUSINESS = os.path.join(FIXTURES_DIR, "rye-lane-bakery")


def router_of(brain):
    with open(os.path.join(brain, "SKILL.md"), encoding="utf-8") as handle:
        return handle.read()


def wiki_pages(brain):
    return sorted(name for name in os.listdir(os.path.join(brain, "wiki"))
                  if name.endswith(".md"))


class BothFixturesAreValidBrains(BrainOnDisk):
    """Whatever else they are, they are brains — held to the same contract."""

    def test_each_fixture_passes_lint_with_no_errors_and_no_warnings(self):
        for brain in (PERSONA, BUSINESS):
            with self.subTest(brain=os.path.basename(brain)):
                report = lint_brain(brain)
                self.assertEqual([], report.errors)
                self.assertEqual([], report.warnings)

    def test_each_committed_router_is_what_the_generator_produces(self):
        """Routers are generated, never hand-edited — so a regeneration is a no-op."""
        for brain in (PERSONA, BUSINESS):
            with self.subTest(brain=os.path.basename(brain)):
                copy = os.path.join(self.tmp, os.path.basename(brain))
                shutil.copytree(brain, copy)
                os.remove(os.path.join(copy, "SKILL.md"))
                write_router(copy, recorded_root=self.recorded_root(brain))
                self.assertEqual(router_of(brain), router_of(copy))

    @staticmethod
    def recorded_root(brain):
        front, _, _ = parse_frontmatter(router_of(brain))
        return front["metadata"]["brain_root"]

    def test_each_index_links_every_page_the_router_is_expected_to_reach(self):
        """`wiki/` always; `standing/` too, because it is routed rather than fenced."""
        for brain, routed in ((PERSONA, ["wiki"]), (BUSINESS, ["wiki", "standing"])):
            with self.subTest(brain=os.path.basename(brain)):
                linked = set(read_page(brain, "index.md").links())
                expected = {"{}/{}".format(folder, name)
                            for folder in routed
                            for name in sorted(os.listdir(os.path.join(brain, folder)))
                            if name.endswith(".md")}
                self.assertEqual(expected, linked)

    def test_the_persona_overlay_is_never_linked_from_the_index(self):
        """`persona/` is loaded whole by the router, not routed to off the map."""
        for target in read_page(PERSONA, "index.md").links():
            self.assertFalse(target.startswith("persona/"), target)


class TheTwoKindsAreDistinct(unittest.TestCase):
    """A persona brain and a business brain, declaring themselves as such."""

    def test_the_persona_fixture_speaks_as_the_person(self):
        meta = read_brain_meta(PERSONA)
        self.assertEqual("marlow-quist", meta.slug)
        self.assertEqual("persona", meta.kind)
        self.assertEqual("persona", meta.stance)
        self.assertEqual(["persona"], meta.overlays)

    def test_the_business_fixture_answers_from_outside_the_business(self):
        meta = read_brain_meta(BUSINESS)
        self.assertEqual("rye-lane-bakery", meta.slug)
        self.assertEqual("business", meta.kind)
        self.assertEqual("advisor", meta.stance)
        self.assertEqual(["standing"], meta.overlays)

    def test_only_the_persona_router_carries_the_anti_caricature_brake(self):
        self.assertIn("## Anti-caricature", router_of(PERSONA))
        self.assertNotIn("## Anti-caricature", router_of(BUSINESS))

    def test_only_the_persona_router_carries_a_calibration_slot(self):
        self.assertIn("## Calibration", router_of(PERSONA))
        self.assertNotIn("## Calibration", router_of(BUSINESS))

    def test_only_the_business_router_carries_freshness_and_confidentiality(self):
        for heading in ("## Freshness", "## Confidentiality"):
            with self.subTest(heading=heading):
                self.assertIn(heading, router_of(BUSINESS))
                self.assertNotIn(heading, router_of(PERSONA))

    def test_only_the_business_router_makes_the_sources_block_conditional(self):
        self.assertIn("only on answers carrying numbers", flatten(router_of(BUSINESS)))
        self.assertIn("every answer grounded in this brain ends with",
                      flatten(router_of(PERSONA)))


class RoutingOffTheDescriptionsAlone(unittest.TestCase):
    """Stacked routing has nothing but the two frontmatter descriptions to go on."""

    def description(self, brain):
        front, _, _ = parse_frontmatter(router_of(brain))
        return flatten(front["description"])

    def test_each_description_names_its_own_subject_and_not_the_others(self):
        persona, business = self.description(PERSONA), self.description(BUSINESS)
        self.assertIn("marlow quist", persona)
        self.assertNotIn("rye lane", persona)
        self.assertIn("rye lane bakery", business)
        self.assertNotIn("marlow quist", business)

    def test_each_description_carries_the_start_at_index_never_glob_clause(self):
        """Two stacked-test sessions globbed before any router body was in context."""
        for brain in (PERSONA, BUSINESS):
            with self.subTest(brain=os.path.basename(brain)):
                description = self.description(brain)
                self.assertIn("index.md", description)
                self.assertIn("never glob", description)


class TheStackingContractHoldsInBothRouters(unittest.TestCase):
    """The rules that only matter when a second brain is attached (spec §3)."""

    def bodies(self):
        return {os.path.basename(brain): flatten(router_of(brain))
                for brain in (PERSONA, BUSINESS)}

    def assertBothCarry(self, *phrases):
        for name, body in self.bodies().items():
            for phrase in phrases:
                with self.subTest(brain=name, phrase=phrase):
                    self.assertIn(flatten(phrase), body)

    def test_both_state_the_page_budget_as_per_brain(self):
        self.assertBothCarry("2–3 wiki pages per question, per brain",
                             "the budget is per brain, not shared between them")

    def test_both_hold_one_voice_per_session_with_the_rest_as_fact_sources(self):
        self.assertBothCarry("one voice per session",
                             "at most one persona drives the voice",
                             "silent fact source")

    def test_both_surface_conflicts_rather_than_resolving_them_silently(self):
        self.assertBothCarry("outrank", "outward-facing",
                             "surface every conflict; never silently resolve one")

    def test_each_prefixes_its_citation_paths_with_its_own_slug(self):
        self.assertIn("marlow-quist/wiki/<page>.md", router_of(PERSONA))
        self.assertIn("rye-lane-bakery/wiki/<page>.md", router_of(BUSINESS))

    def test_the_routed_overlay_is_citable_and_the_loaded_one_is_not(self):
        """`standing/` grounds answers, so it needs a path; `persona/` is not evidence."""
        self.assertIn("rye-lane-bakery/standing/<page>.md", router_of(BUSINESS))
        self.assertIn("never cited", flatten(router_of(PERSONA)))

    def test_no_router_ever_relays_a_third_party_at_arms_length(self):
        self.assertBothCarry("no middleman", "banned")


class ThePersonaOverlay(unittest.TestCase):
    """`voice.md` names the rules; `exemplars.md` is the evidence (spec §4)."""

    def overlay(self, name):
        with open(os.path.join(PERSONA, "persona", name), encoding="utf-8") as handle:
            return handle.read()

    def exemplars(self):
        """Each `### <label>` heading and the block that follows it."""
        blocks = re.split(r"^### ", self.overlay("exemplars.md"), flags=re.MULTILINE)[1:]
        return [(block.split("\n", 1)[0], block) for block in blocks]

    def test_there_are_between_ten_and_twenty_exemplars(self):
        self.assertTrue(10 <= len(self.exemplars()) <= 20, len(self.exemplars()))

    def test_every_exemplar_is_quoted_verbatim_and_carries_its_source(self):
        for label, block in self.exemplars():
            with self.subTest(exemplar=label):
                self.assertRegex(block, r"(?m)^> ")
                self.assertEqual(1, len(re.findall(r"^Source: ", block, re.MULTILINE)))

    def test_the_exemplars_are_chosen_for_range_including_short_form(self):
        labels = flatten(" ".join(label for label, _ in self.exemplars()))
        self.assertIn("short-form", labels)

    def test_voice_md_is_a_thin_list_of_observable_rules(self):
        voice = self.overlay("voice.md")
        self.assertLess(len(voice.splitlines()), 60,
                        "voice.md is a list of rules, not an essay about them")
        self.assertIn("## Short-form register", voice)

    def test_voice_md_carries_its_own_anti_caricature_section(self):
        self.assertIn("## Anti-caricature", self.overlay("voice.md"))


class TheBusinessFreshnessContract(unittest.TestCase):
    """The frontmatter the business router's date-attached answers run on."""

    def pages(self):
        return {name: read_page(BUSINESS, os.path.join("wiki", name)).frontmatter
                for name in wiki_pages(BUSINESS)}

    def test_at_least_one_page_is_fast_volatility_and_fully_dated(self):
        fast = [front for front in self.pages().values()
                if front.get("volatility") == "fast"]
        self.assertTrue(fast, "the business kind needs a page that actually rots")
        for front in fast:
            self.assertRegex(str(front.get("as_of")), r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(str(front.get("canonical") or "").strip(),
                            "a fast page says where the live truth lives")

    def test_every_page_declares_how_fast_it_rots(self):
        for name, front in self.pages().items():
            with self.subTest(page=name):
                self.assertIn(front.get("volatility"), ("fast", "slow", "stable"))

    def test_the_standing_overlay_holds_policy_that_binds_outward_facing_work(self):
        standing = os.path.join(BUSINESS, "standing")
        self.assertTrue([n for n in os.listdir(standing) if n.endswith(".md")])


if __name__ == "__main__":
    unittest.main()
