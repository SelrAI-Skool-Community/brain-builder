"""Standing an empty brain up: slug derivation, the skeleton, blueprints, the log.

These are the mechanical steps of the build loop (spec.md §5). The builder skill
talks its way through intake and synthesis; everything deterministic about
*where the brain goes* and *what shape it starts in* lives here, so the model
never has to reinvent it mid-build.
"""
import contextlib
import io
import os
import unittest

from brainkit import BrainOnDisk, flatten

from gen_router import read_brain_meta, write_router
from lint import lint_brain
from scaffold import (
    BLUEPRINTS_DIR,
    derive_slug,
    list_blueprints,
    log_event,
    scaffold_brain,
)


class DeriveSlug(unittest.TestCase):
    """The slug is derived, stated at the plan gate, and never asked about."""

    def test_a_title_becomes_lowercase_and_hyphenated(self):
        self.assertEqual("sourdough-baking", derive_slug("Sourdough Baking"))

    def test_punctuation_and_runs_of_space_collapse_to_single_hyphens(self):
        self.assertEqual("alex-hormozis-offers", derive_slug("Alex Hormozi's  offers!"))

    def test_an_apostrophe_closes_up_rather_than_leaving_a_stray_letter(self):
        """`hormozi-s-offers` reads as a typo; the possessive belongs to the word."""
        self.assertEqual("dans-notes", derive_slug("Dan’s notes"))

    def test_leading_and_trailing_punctuation_is_trimmed(self):
        self.assertEqual("ai-engineering", derive_slug("  --AI engineering--  "))

    def test_accents_and_symbols_reduce_to_ascii_words(self):
        self.assertEqual("cafe-menus-2026", derive_slug("Café menus (2026)"))

    def test_a_long_title_is_truncated_at_a_word_boundary(self):
        slug = derive_slug("The complete and exhaustive guide to naturally "
                           "leavened bread at home")
        self.assertLessEqual(len(slug), 48)
        self.assertFalse(slug.endswith("-"))
        self.assertTrue(slug.startswith("the-complete-and-exhaustive-guide"))

    def test_a_title_with_nothing_sluggable_falls_back_to_a_usable_name(self):
        self.assertEqual("brain", derive_slug("!!!"))


class Blueprints(BrainOnDisk):
    """Kinds are files, enumerated at runtime — adding a kind is adding a file."""

    def blueprint(self, name, kind, summary="A shape.", body="# Shape\n"):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("---\nkind: {}\nsummary: {}\n---\n\n{}".format(
                kind, summary, body))
        return path

    def test_a_blueprint_dropped_into_the_directory_becomes_an_offered_kind(self):
        """The follow-up kinds ticket ships persona and business as files only."""
        self.blueprint("subject.md", "subject")
        self.assertEqual(["subject"], [b.kind for b in list_blueprints(self.tmp)])

        self.blueprint("persona.md", "persona")
        self.assertEqual(["persona", "subject"],
                         sorted(b.kind for b in list_blueprints(self.tmp)))

    def test_each_blueprint_carries_the_one_line_summary_the_builder_explains(self):
        self.blueprint("subject.md", "subject", summary="A wiki organised by concept.")
        blueprint = list_blueprints(self.tmp)[0]
        self.assertEqual("A wiki organised by concept.", blueprint.summary)
        self.assertTrue(blueprint.path.endswith("subject.md"))

    def test_the_kind_falls_back_to_the_filename_when_undeclared(self):
        path = os.path.join(self.tmp, "business.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("# Business\n")
        self.assertEqual(["business"], [b.kind for b in list_blueprints(self.tmp)])

    def test_non_markdown_files_are_not_kinds(self):
        self.blueprint("subject.md", "subject")
        with open(os.path.join(self.tmp, "README.txt"), "w", encoding="utf-8") as handle:
            handle.write("not a blueprint")
        self.assertEqual(["subject"], [b.kind for b in list_blueprints(self.tmp)])

    def test_a_missing_blueprints_directory_offers_no_kinds_rather_than_raising(self):
        self.assertEqual([], list_blueprints(os.path.join(self.tmp, "nope")))


class ShippedBlueprints(unittest.TestCase):
    """The blueprints this kit actually ships (spec.md §4)."""

    def shipped(self):
        return {b.kind: b for b in list_blueprints(BLUEPRINTS_DIR)}

    def text_of(self, kind):
        with open(self.shipped()[kind].path, encoding="utf-8") as handle:
            return flatten(handle.read())

    def test_the_subject_blueprint_ships_and_declares_itself(self):
        kinds = self.shipped()
        self.assertIn("subject", kinds)
        self.assertTrue(kinds["subject"].summary,
                        "the builder explains the shape in a line — it needs a summary")

    def test_all_three_v1_kinds_ship_as_files(self):
        """Spec §4: subject, persona and business all ship in v1."""
        self.assertEqual({"business", "persona", "subject"}, set(self.shipped()))

    def test_every_shipped_blueprint_is_enumerable_and_declares_a_summary(self):
        blueprints = list_blueprints(BLUEPRINTS_DIR)
        self.assertTrue(blueprints)
        for blueprint in blueprints:
            with self.subTest(kind=blueprint.kind):
                self.assertTrue(blueprint.kind)
                self.assertTrue(blueprint.summary)
                self.assertTrue(blueprint.stance)

    def test_each_shipped_blueprint_declares_the_stance_its_brains_are_built_with(self):
        """`scaffold_brain` takes the stance off the file — so the file must be right."""
        stances = {kind: b.stance for kind, b in self.shipped().items()}
        self.assertEqual({"subject": "advisor", "persona": "persona",
                          "business": "advisor"}, stances)

    def test_no_shipped_blueprint_is_a_worked_example(self):
        """A worked example gets copied; a skeleton gets filled in (spec.md §4)."""
        for kind in self.shipped():
            for tell in ("sourdough", "hormozi", "70 %"):
                with self.subTest(kind=kind, tell=tell):
                    self.assertNotIn(tell, self.text_of(kind))

    def test_the_subject_blueprint_names_its_own_kind(self):
        self.assertIn("subject", self.text_of("subject"))

    def test_the_persona_blueprint_is_one_composite_shape_with_the_voice_contract(self):
        """Spec §4: subject core + voice on top, in one blueprint, never two."""
        text = self.text_of("persona")
        for phrase in ("composite", "voice.md", "exemplars.md", "10", "20",
                       "short-form", "verbatim", "anti-caricature",
                       "never merged with facts", "loaded whole"):
            with self.subTest(phrase=phrase):
                self.assertIn(flatten(phrase), text)

    def test_the_persona_blueprint_keeps_voice_only_behind_the_warned_opt_out(self):
        """Never advertised — reachable only as a custom shape, after the warning."""
        text = self.text_of("persona")
        self.assertIn("no corpus of its own", text)
        self.assertIn("live research", text)
        self.assertIn("never advertise", text)

    def test_the_business_blueprint_carries_the_kinds_signature_behaviours(self):
        """Spec §4: entity/process wiki, standing overlay, freshness, authority, secrecy."""
        text = self.text_of("business")
        for phrase in ("entity", "process", "standing/", "unfenced", "as_of",
                       "volatility", "canonical", "source-authority",
                       "contradiction", "confidential", "write-back"):
            with self.subTest(phrase=phrase):
                self.assertIn(flatten(phrase), text)

    def test_the_business_blueprint_speaks_from_outside_the_business(self):
        """Advisor stance: "you/the business offers X", never "we"."""
        text = self.text_of("business")
        self.assertIn('never "we"', text)
        self.assertIn("outside the business", text)


class Skeleton(BrainOnDisk):
    """`scaffold_brain` writes the shape every later phase fills in."""

    def scaffold(self, **kwargs):
        options = dict(title="Sourdough Baking", at=self.tmp,
                       domain="Naturally leavened bread at home.", kind="subject")
        options.update(kwargs)
        return scaffold_brain(**options)

    def test_the_brain_lands_at_the_derived_slug_under_the_given_directory(self):
        root = self.scaffold()
        self.assertEqual(os.path.join(self.tmp, "sourdough-baking"), root)
        self.assertTrue(os.path.isdir(root))

    def test_an_explicit_slug_overrides_the_derived_one(self):
        """The plan gate states the slug; a member can override it in passing."""
        root = self.scaffold(slug="my-bread")
        self.assertEqual(os.path.join(self.tmp, "my-bread"), root)

    def test_the_skeleton_carries_every_part_of_the_contract(self):
        root = self.scaffold()
        for relpath in ("index.md", "log.md", "CHANGELOG.md", "wiki", "raw"):
            with self.subTest(part=relpath):
                self.assertTrue(os.path.exists(os.path.join(root, relpath)))

    def test_a_blueprints_declared_stance_is_what_the_brain_is_built_with(self):
        """Adding a kind is adding a file — including the stance it answers in."""
        blueprints = os.path.join(self.tmp, "blueprints")
        os.makedirs(blueprints)
        with open(os.path.join(blueprints, "coach.md"), "w", encoding="utf-8") as handle:
            handle.write("---\nkind: coach\nsummary: A coaching shape.\n"
                         "stance: coach\n---\n\n# Coach\n")

        root = self.scaffold(kind="coach", blueprints=blueprints)

        meta = read_brain_meta(root)
        self.assertEqual("coach", meta.kind)
        self.assertEqual("coach", meta.stance)

    def test_an_explicit_stance_still_wins_for_a_custom_shape(self):
        root = self.scaffold(kind="subject", stance="persona")
        self.assertEqual("persona", read_brain_meta(root).stance)

    def test_the_index_carries_the_frontmatter_the_router_generator_reads(self):
        """CORE-146 decision: router metadata comes off index.md frontmatter."""
        root = self.scaffold(stance="advisor")
        meta = read_brain_meta(root)
        self.assertEqual("sourdough-baking", meta.slug)
        self.assertEqual("Sourdough Baking", meta.title)
        self.assertEqual("Naturally leavened bread at home.", meta.domain)
        self.assertEqual("subject", meta.kind)
        self.assertEqual("advisor", meta.stance)

    def test_a_domain_spanning_several_lines_survives_as_one_readable_value(self):
        root = self.scaffold(domain="Bread:\nstarter through bake.\n")
        self.assertEqual("Bread: starter through bake.", read_brain_meta(root).domain)

    def test_the_index_ships_the_known_gaps_section_lint_requires(self):
        with open(os.path.join(self.scaffold(), "index.md"), encoding="utf-8") as handle:
            self.assertIn("## Known gaps", handle.read())

    def test_a_scaffolded_brain_lints_clean_once_pages_and_router_exist(self):
        """The whole mechanical chain: scaffold, fill, generate, lint."""
        root = self.scaffold()
        self.write(root, "wiki/hydration.md", "---\ntype: concept\n---\n\n# Hydration\n")
        self.write(root, "raw/notes.md", "Bench notes.\n")
        with open(os.path.join(root, "index.md"), "a", encoding="utf-8") as handle:
            handle.write("\n- [Hydration](wiki/hydration.md) — 70 % baseline.\n")
        write_router(root)

        report = lint_brain(root)
        self.assertEqual([], report.errors)
        self.assertEqual([], report.warnings)

    def test_scaffolding_refuses_to_overwrite_a_brain_that_is_already_there(self):
        self.scaffold()
        with self.assertRaises(FileExistsError):
            self.scaffold()


class BuildLog(BrainOnDisk):
    """Failures land in `log.md` and the build carries on (spec.md §5)."""

    def test_an_event_is_appended_without_disturbing_what_is_already_there(self):
        root = scaffold_brain(title="Test Brain", at=self.tmp)
        log_event(root, "3 sources produced no text — skipped")
        log_event(root, "taxonomy: 9 concepts")

        with open(os.path.join(root, "log.md"), encoding="utf-8") as handle:
            log = handle.read()
        self.assertIn("brain scaffolded", log)
        self.assertIn("3 sources produced no text — skipped", log)
        self.assertLess(log.index("3 sources"), log.index("taxonomy: 9 concepts"))

    def test_the_log_stays_a_valid_contract_page_after_appends(self):
        """`log.md` is a reserved OKF page — appending must not break its type."""
        root = scaffold_brain(title="Test Brain", at=self.tmp)
        log_event(root, "a dead source")
        self.write(root, "wiki/concept.md", "---\ntype: concept\n---\n\n# Concept\n")
        self.write(root, "raw/source.md", "raw text\n")
        write_router(root)
        self.assertEqual([], lint_brain(root).errors)


class CommandLine(BrainOnDisk):
    """`python3 scaffold.py` — the builder's one mechanical call for the skeleton."""

    def run_cli(self, *args):
        import scaffold
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            return scaffold.main(["scaffold.py"] + list(args)), out.getvalue()

    def test_it_prints_the_root_it_created_so_the_build_can_use_it(self):
        code, out = self.run_cli("--title", "Sourdough Baking", "--at", self.tmp)
        self.assertEqual(0, code)
        self.assertEqual(os.path.join(self.tmp, "sourdough-baking"), out.strip())
        self.assertTrue(os.path.isdir(out.strip()))

    def test_listing_blueprints_reports_the_kinds_on_offer(self):
        code, out = self.run_cli("--list-blueprints")
        self.assertEqual(0, code)
        self.assertIn("subject", out)

    def test_a_title_is_required(self):
        self.assertEqual(2, self.run_cli("--at", self.tmp)[0])

    def test_building_over_an_existing_brain_exits_one_rather_than_clobbering_it(self):
        self.run_cli("--title", "Sourdough Baking", "--at", self.tmp)
        self.assertEqual(1, self.run_cli("--title", "Sourdough Baking", "--at", self.tmp)[0])


if __name__ == "__main__":
    unittest.main()
