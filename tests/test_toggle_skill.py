"""`skills/brain-toggle/SKILL.md` is the toggle's whole interface (spec §7).

The script under it is covered thoroughly by `test_toggle.py`. The doc was not
covered at all, which is how it came to tell the model to run
`python3 skills/brain-toggle/scripts/toggle.py` — a repo-relative path that does
not exist in the installed layout, where the skill is symlinked into a skills
directory and the session's cwd is the member's own project.

So this holds the doc to the same standard `test_builder_skill.py` holds the
builder's: the commands it names exist, the flags it names are parsed, and the
§7 clauses that live *only* in prose are actually in it.
"""
import os
import re
import unittest

from brainkit import REPO_ROOT, flatten, read_text

import toggle
from brain_contract import parse_frontmatter

SKILL_DIR = os.path.join(REPO_ROOT, "skills", "brain-toggle")
SKILL_PATH = os.path.join(SKILL_DIR, "SKILL.md")


def skill_text():
    return read_text(SKILL_PATH)


class Frontmatter(unittest.TestCase):

    def setUp(self):
        self.front, self.body, self.present = parse_frontmatter(skill_text())

    def test_it_has_frontmatter_with_a_name_matching_its_directory(self):
        self.assertTrue(self.present)
        self.assertEqual("brain-toggle", self.front.get("name"))

    def test_the_description_fires_from_the_natural_language_the_spec_names(self):
        description = flatten(self.front.get("description") or "")
        self.assertIn("brain", description)
        for phrase in ("turn on", "attach", "detach"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, description)


class Wiring(unittest.TestCase):
    """Every command and flag the doc names has to be one the script has."""

    def test_the_script_it_calls_is_shipped_next_to_it(self):
        self.assertTrue(os.path.isfile(
            os.path.join(SKILL_DIR, "scripts", "toggle.py")))

    def test_no_command_is_written_relative_to_the_working_directory(self):
        """The installed skill runs with the member's project as cwd."""
        self.assertNotIn("python3 skills/", skill_text())
        self.assertIn("TOGGLE=", skill_text(),
                      "the skill has to resolve its own directory once")

    def test_every_command_it_names_exists(self):
        named = set(re.findall(r'"\$TOGGLE" ([a-z-]+)', skill_text()))
        self.assertTrue(named)
        for command in sorted(named):
            with self.subTest(command=command):
                self.assertIn(command, toggle.COMMANDS)

    def test_every_flag_it_names_is_one_the_script_parses(self):
        named = set(re.findall(r"`(--[a-z-]+)", skill_text()))
        self.assertTrue(named)
        _, options = toggle._parse([])
        for flag in sorted(named):
            with self.subTest(flag=flag):
                self.assertIn(flag, options)

    def test_the_harnesses_it_names_are_the_ones_the_script_knows(self):
        for harness in sorted(toggle.HARNESSES):
            with self.subTest(harness=harness):
                self.assertIn(harness, skill_text())


class SpecClauses(unittest.TestCase):
    """§7 rules that live in this file and nowhere else."""

    def setUp(self):
        self.text = flatten(skill_text())

    def test_global_is_stated_as_the_default_and_project_as_opt_in(self):
        self.assertIn("global is the default", self.text)
        self.assertIn("project-scoped is opt-in", self.text)

    def test_the_resolved_target_is_stated_before_linking(self):
        self.assertIn("git root", self.text)
        self.assertIn("state the resolved path before linking", self.text)

    def test_move_not_duplicate_is_offered_rather_than_retried(self):
        self.assertIn("--move", self.text)
        self.assertIn("never end up with the same brain attached twice", self.text)

    def test_the_assisted_split_carries_all_four_steps_in_order(self):
        split = self.text.split("assisted split", 1)[1]
        positions = [split.index(step) for step in (
            "propose the mapping", "detach the involved globals",
            "attach each brain into its project", "confirm per directory")]
        self.assertEqual(sorted(positions), positions)

    def test_the_pointer_block_is_delimited_reversible_and_never_content(self):
        self.assertIn("<!-- brain: hormozi -->", skill_text())
        self.assertIn("<!-- /brain: hormozi -->", skill_text())
        self.assertIn("never paste brain content into an instruction file", self.text)
        self.assertIn("removal restores the file byte for byte", self.text)

    def test_the_diff_is_shown_before_the_first_pointer_write(self):
        self.assertIn("pointer-diff", self.text)
        self.assertIn("show the diff before the first write", self.text)

    def test_instruction_file_harnesses_are_declared_global_only_in_v1(self):
        self.assertIn("global-only in v1", self.text)

    def test_the_unservable_edge_is_stated_rather_than_hidden(self):
        self.assertIn("same* directory", self.text.replace("*", "*"))
        self.assertIn("give each brain its own working directory", self.text)

    def test_an_unlisted_skill_md_harness_has_a_documented_way_in(self):
        """Spec §7 arm 1 covers "the SKILL.md open standard", not two harnesses."""
        self.assertIn("--skills-dir", self.text)


if __name__ == "__main__":
    unittest.main()
