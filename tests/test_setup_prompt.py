"""The ship surface: the install path, the README, and the demo prompts.

`SETUP-PROMPT.md` is the one thing every member runs, and it is prose — which
means it drifts away from the code silently and nobody finds out until a member
on a clean machine follows a step that no longer works.

So the load-bearing half of it is executed here rather than proof-read. The
install is rehearsed against a genuine `git clone` of this repo, in a temp
directory, with `toggle.py --home` pointed at a throwaway home so the real
`~/.claude` is never written to. The other half — the dependency names and the
key the doc tells members to export — is asserted against the scripts' own
constants, so a renamed package breaks a test instead of a member's build.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from brainkit import REPO_ROOT, SCRIPTS_DIR, TOGGLE_SCRIPTS_DIR, flatten

import ingest_docs
import ingest_web
import ingest_youtube
import transcribe

SETUP_PROMPT = os.path.join(REPO_ROOT, "SETUP-PROMPT.md")
README = os.path.join(REPO_ROOT, "README.md")
DEMOS_DIR = os.path.join(REPO_ROOT, "demos")
FIXTURE = "sourdough-baking"


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def run(*argv, **kwargs):
    """A script, run the way the install document tells a member to run it."""
    return subprocess.run([sys.executable] + list(argv), capture_output=True,
                          text=True, **kwargs)


class InstallDocumentMatchesTheCode(unittest.TestCase):
    """Every dependency and key the document names, taken from the scripts."""

    def setUp(self):
        self.text = read(SETUP_PROMPT)

    def test_it_names_the_pip_line_each_arm_prints_for_itself(self):
        """A renamed package fails here, not half way through a member's build."""
        hints = set(ingest_docs.INSTALL_HINTS.values())
        hints.add(ingest_web.INSTALL_HINT)
        hints.add(ingest_youtube.INSTALL_HINT)
        self.assertEqual(4, len(hints), "an arm's install hint moved")
        for hint in sorted(hints):
            with self.subTest(hint=hint):
                self.assertIn(hint, self.text)

    def test_it_names_the_transcription_key_the_engine_actually_reads(self):
        key = transcribe.ENGINES[transcribe.DEFAULT_ENGINE].key_env
        self.assertEqual("ELEVENLABS_API_KEY", key)
        self.assertIn(key, self.text)

    def test_it_says_a_missing_dependency_is_recorded_rather_than_raised(self):
        flat = flatten(self.text)
        self.assertIn("carries on", flat)
        self.assertIn("log.md", flat)

    def test_it_is_honest_that_a_dead_corpus_stops_the_build(self):
        """The one exception to fail-loudly-and-continue, stated rather than hidden."""
        self.assertIn("stop and talk to the member rather than building "
                      "an empty brain", flatten(self.text))

    def test_every_repo_path_it_tells_an_agent_to_run_exists(self):
        paths = set(re.findall(r"(?:tests|skills)/[\w./-]+", self.text))
        self.assertTrue(paths)
        for path in sorted(paths):
            with self.subTest(path=path):
                self.assertTrue(os.path.exists(os.path.join(REPO_ROOT, path)))


class ReadmeShipState(unittest.TestCase):
    """The claims the README is not allowed to quietly lose."""

    def setUp(self):
        self.text = read(README)
        self.flat = flatten(self.text)

    def test_it_carries_the_one_paste_in_install(self):
        self.assertIn("clone https://github.com/luke-heka/brain-builder and "
                      "follow setup-prompt.md", self.flat)

    def test_it_names_all_three_shipped_components(self):
        for component in ("brain-builder", "brain-toggle", "blueprint"):
            with self.subTest(component=component):
                self.assertIn(component, self.flat)

    def test_it_keeps_the_instruction_file_harness_limit(self):
        self.assertIn("global-only in\nv1", self.text.replace("**", ""))

    def test_it_keeps_the_same_directory_edge_case_honesty(self):
        self.assertIn("same* directory", self.text)
        self.assertIn("give each brain its own working directory", self.flat)

    def test_it_states_the_rights_stance_and_links_the_detail(self):
        self.assertIn("docs/rights.md", self.text)
        self.assertIn("built locally, on your machine", self.flat)

    def test_every_repo_path_it_links_exists(self):
        links = set(re.findall(r"\]\(([\w./-]+)\)", self.text))
        self.assertTrue(links)
        for link in sorted(links):
            with self.subTest(link=link):
                self.assertTrue(os.path.exists(os.path.join(REPO_ROOT, link)))


class DemoPrompts(unittest.TestCase):
    """Three worked prompts, each a complete invocation with its fail questions."""

    DEMOS = ("ai-expert-karpathy.md", "marketing.md", "hormozi.md")

    def test_all_three_demos_ship_with_an_index(self):
        for name in self.DEMOS + ("README.md",):
            with self.subTest(name=name):
                self.assertTrue(os.path.isfile(os.path.join(DEMOS_DIR, name)))

    def test_each_prompt_covers_what_the_intake_has_to_understand(self):
        """Four things understood up front is what earns zero questions."""
        for name in self.DEMOS:
            flat = flatten(read(os.path.join(DEMOS_DIR, name)))
            for phrase in ("what it's about", "what it's built from",
                           "where the sources are", "what i want to ask it"):
                with self.subTest(demo=name, phrase=phrase):
                    self.assertIn(phrase, flat)

    def test_each_demo_carries_fail_questions_across_the_three_types(self):
        for name in self.DEMOS:
            flat = flatten(read(os.path.join(DEMOS_DIR, name)))
            with self.subTest(demo=name):
                self.assertIn("## fail questions", flat)
            for failure_type in ("number —", "framework —", "voice —"):
                with self.subTest(demo=name, failure_type=failure_type):
                    self.assertIn(failure_type, flat)

    def test_every_fail_question_says_the_control_fails_confidently(self):
        """The criterion that makes a fail question worth anything."""
        for name in self.DEMOS:
            text = read(os.path.join(DEMOS_DIR, name))
            questions = text.count("**A brain-less agent fails confidently")
            with self.subTest(demo=name):
                self.assertGreaterEqual(questions, 2)

    def test_an_unverified_answer_is_marked_rather_than_asserted(self):
        """No corpus, no certainty — the mark is the honesty."""
        for name in ("ai-expert-karpathy.md", "marketing.md"):
            text = read(os.path.join(DEMOS_DIR, name))
            with self.subTest(demo=name):
                self.assertIn("unverified-until-rebuild", text)

    def test_the_hormozi_literals_name_the_page_and_the_video_they_came_from(self):
        """Verified means traceable, or it means nothing."""
        text = read(os.path.join(DEMOS_DIR, "hormozi.md"))
        self.assertEqual(4, text.count("*Corpus answer verified*"))
        self.assertIn("wiki/offers-and-money-models/ltv-to-cac-ratios.md", text)
        self.assertIn("persona/voice.md", text)

    def test_the_index_states_the_rebuilds_are_the_acceptance_test_and_unrun(self):
        flat = flatten(read(os.path.join(DEMOS_DIR, "README.md")))
        self.assertIn("acceptance test", flat)
        self.assertIn("has not been run", flat)
        self.assertIn("never distributed", flat)


class NoInternalInfrastructure(unittest.TestCase):
    """Zero Selr infrastructure in the kit — the shipping member meets none of it."""

    #: `docs/` records the decision and the tooling contributors use; neither is
    #: something a member installing the kit ever runs. This file names the
    #: markers in order to search for them.
    EXEMPT = ("docs/spec.md", "docs/agents/issue-tracker.md",
              "tests/test_setup_prompt.py")

    def shipped_files(self):
        for base, dirs, names in os.walk(REPO_ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
            for name in names:
                path = os.path.join(base, name)
                relpath = os.path.relpath(path, REPO_ROOT)
                if relpath.replace(os.sep, "/") not in self.EXEMPT:
                    yield relpath, path

    def test_the_gbrain_push_is_gone_from_everything_that_ships(self):
        found = []
        for relpath, path in self.shipped_files():
            try:
                text = read(path).lower()
            except (UnicodeDecodeError, OSError):
                continue
            found += ["{}: {}".format(relpath, marker)
                      for marker in ("gbrain", "mcp__", "selrai-team")
                      if marker in text]
        self.assertEqual([], found, "internal infrastructure still shipped")


class FreshCloneInstall(unittest.TestCase):
    """The install document, executed against a real clone of this repo.

    This is the "fresh clone on a clean profile" check in runnable form. It
    clones over the local filesystem, so it needs no network; it points
    `--home` at a throwaway directory, so it never touches the real one.
    """

    @classmethod
    def setUpClass(cls):
        if not shutil.which("git"):
            raise unittest.SkipTest("git is not on PATH")
        cls.tmp = tempfile.mkdtemp(prefix="brain-clone-")
        cls.clone = os.path.join(cls.tmp, "brain-builder")
        clone = subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", REPO_ROOT, cls.clone],
            capture_output=True, text=True)
        if clone.returncode != 0:
            shutil.rmtree(cls.tmp, True)
            raise unittest.SkipTest("could not clone the repo: " + clone.stderr)
        if not os.path.isfile(os.path.join(cls.clone, "SETUP-PROMPT.md")):
            shutil.rmtree(cls.tmp, True)
            raise unittest.SkipTest(
                "SETUP-PROMPT.md is not committed yet — a clone cannot see it")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="brain-home-")
        self.addCleanup(shutil.rmtree, self.home, True)
        self.toggle = os.path.join(self.clone, "skills", "brain-toggle",
                                   "scripts", "toggle.py")
        self.builder = os.path.join(self.clone, "skills", "brain-builder", "scripts")

    def brain(self):
        """A copy of a shipped fixture, standing in for a member's first brain."""
        source = os.path.join(self.clone, "tests", "fixtures", FIXTURE)
        target = os.path.join(self.home, FIXTURE)
        shutil.copytree(source, target)
        return target

    def test_the_clone_carries_both_skills_and_the_blueprints(self):
        """Step 3 links these two paths; a clone missing either is a broken install."""
        for relpath in ("skills/brain-builder/SKILL.md",
                        "skills/brain-toggle/SKILL.md",
                        "skills/brain-builder/blueprints"):
            with self.subTest(relpath=relpath):
                self.assertTrue(os.path.exists(os.path.join(self.clone, relpath)))

    def test_step_2_resolves_a_skills_directory_under_the_home_it_is_given(self):
        """`--home` is what keeps the rehearsal out of the member's real profile."""
        result = run(self.toggle, "resolve", "--home", self.home)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(os.path.join(self.home, ".claude", "skills"),
                         result.stdout.strip())

    def test_step_3_links_both_skills_into_the_resolved_directory(self):
        skills_dir = run(self.toggle, "resolve", "--home", self.home).stdout.strip()
        os.makedirs(skills_dir, exist_ok=True)
        for skill in ("brain-builder", "brain-toggle"):
            os.symlink(os.path.join(self.clone, "skills", skill),
                       os.path.join(skills_dir, skill))
        for skill in ("brain-builder", "brain-toggle"):
            link = os.path.join(skills_dir, skill)
            with self.subTest(skill=skill):
                self.assertTrue(os.path.islink(link))
                self.assertTrue(os.path.isfile(os.path.join(link, "SKILL.md")))

    def test_step_4_lints_a_fixture_brain_clean_out_of_the_clone(self):
        result = run(os.path.join(self.builder, "lint.py"), self.brain())
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("valid brain — 0 error(s), 0 warning(s)", result.stdout)

    def test_step_4_regenerates_the_router_as_a_byte_for_byte_no_op(self):
        brain = self.brain()
        router = os.path.join(brain, "SKILL.md")
        before = read(router)
        result = run(os.path.join(self.builder, "gen_router.py"), brain)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(router, result.stdout.strip())
        self.assertEqual(before, read(router))

    def test_step_4_attaches_lists_and_detaches_without_touching_the_real_home(self):
        brain = self.brain()
        fake_home = os.path.join(self.home, "profile")

        attach = run(self.toggle, "attach", brain, "--home", fake_home)
        self.assertEqual(0, attach.returncode, attach.stderr)
        self.assertIn("attached", attach.stdout)
        link = os.path.join(fake_home, ".claude", "skills", FIXTURE)
        self.assertTrue(os.path.islink(link))

        listing = run(self.toggle, "list", "--home", fake_home)
        self.assertEqual(0, listing.returncode, listing.stderr)
        self.assertIn(FIXTURE, listing.stdout)
        self.assertNotIn("BROKEN", listing.stdout)

        detach = run(self.toggle, "detach", FIXTURE, "--home", fake_home)
        self.assertEqual(0, detach.returncode, detach.stderr)
        self.assertFalse(os.path.lexists(link))

        self.assertFalse(os.path.exists(os.path.join(os.path.expanduser("~"),
                                                     ".claude", "skills", FIXTURE)))

    def test_attach_refuses_the_skills_themselves_as_the_document_warns(self):
        """Step 3 is two symlinks precisely because `attach` takes brains only."""
        result = run(self.toggle, "attach",
                     os.path.join(self.clone, "skills", "brain-builder"),
                     "--home", self.home)
        self.assertEqual(1, result.returncode)
        self.assertIn("is not a brain", result.stderr)

    def test_the_suite_the_document_ends_on_runs_from_the_clone(self):
        """Step 4's last command, run inside the clone rather than described."""
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "tests", "-p",
             "test_toggle.py"],
            cwd=self.clone, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
