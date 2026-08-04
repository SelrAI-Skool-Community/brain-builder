"""The shipped `brain-builder` skill, held to the things that silently break it.

The build loop itself is conversational and lives as instructions — not
something a unit test can judge. What a test *can* hold is the wiring: the skill
fires under its own name, every script and blueprint it tells the model to run
is actually there, and the commands it prints are the commands those scripts
accept.
"""
import os
import re
import subprocess
import sys
import unittest

from brainkit import REPO_ROOT, SCRIPTS_DIR, flatten

from brain_contract import parse_frontmatter

SKILL_DIR = os.path.join(REPO_ROOT, "skills", "brain-builder")
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")


def skill_text():
    with open(SKILL_MD, encoding="utf-8") as handle:
        return handle.read()


class SkillFrontmatter(unittest.TestCase):
    """The metadata that decides whether the skill ever fires at all."""

    def setUp(self):
        self.front, self.body, self.present = parse_frontmatter(skill_text())

    def test_the_skill_name_matches_its_directory_so_the_slash_command_works(self):
        """The name doubles as the slash command — `/brain-builder`."""
        self.assertTrue(self.present)
        self.assertEqual("brain-builder", self.front.get("name"))
        self.assertEqual(os.path.basename(SKILL_DIR), self.front.get("name"))

    def test_the_description_fires_from_natural_language_not_just_the_command(self):
        description = flatten(self.front.get("description") or "")
        self.assertTrue(description)
        for phrase in ("build", "brain"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, description)

    def test_the_body_stays_inside_the_progressive_disclosure_budget(self):
        """Under ~500 lines; past that the blueprint files carry the depth."""
        self.assertLess(len(self.body.splitlines()), 500)


class SkillWiring(unittest.TestCase):
    """Every path and command the skill tells the model to use has to exist."""

    def scripts_named(self):
        """Every script the skill tells the model to run.

        Commands are written `python3 "$KIT/<script>"` because the member's
        working directory is not the skill directory — a bare `scripts/x.py`
        is a `No such file or directory` in every real session.
        """
        return set(re.findall(r"(?:\$KIT|scripts)/(\w+\.py)", skill_text()))

    def test_no_command_is_written_relative_to_the_working_directory(self):
        """`python3 scripts/x.py` only works from inside the clone.

        The skill is installed by symlink and runs with the member's project as
        cwd, so a repo-relative command in it is a command that always fails.
        """
        self.assertNotIn("python3 scripts/", skill_text())
        self.assertIn("KIT=", skill_text(), "the skill has to resolve its own directory")

    def test_every_script_the_skill_calls_is_shipped_next_to_it(self):
        named = self.scripts_named()
        self.assertTrue(named)
        for script in sorted(named):
            with self.subTest(script=script):
                self.assertTrue(os.path.isfile(os.path.join(SCRIPTS_DIR, script)))

    def test_the_scripts_it_calls_all_run_and_report_their_usage(self):
        """A broken CLI surfaces here rather than half way through a member's build."""
        for script in sorted(self.scripts_named()):
            with self.subTest(script=script):
                result = subprocess.run(
                    [sys.executable, os.path.join(SCRIPTS_DIR, script)],
                    capture_output=True, text=True)
                self.assertEqual(2, result.returncode)
                self.assertIn("usage", (result.stderr + result.stdout).lower())

    def test_it_names_the_toggle_skill_for_the_attach_step(self):
        self.assertIn("brain-toggle", skill_text())

    def test_it_points_at_the_blueprints_directory_that_ships(self):
        self.assertIn("--list-blueprints", skill_text())
        self.assertTrue(os.path.isdir(os.path.join(SKILL_DIR, "blueprints")))

    def test_it_states_the_default_home_the_plan_gate_quotes(self):
        self.assertIn("~/brains/", skill_text())


if __name__ == "__main__":
    unittest.main()
