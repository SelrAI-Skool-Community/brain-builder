"""The ship surface: the install path, the README, and the demo prompts.

`SETUP-PROMPT.md` is the one thing every member runs, and it is prose — which
means it drifts away from the code silently and nobody finds out until a member
on a clean machine follows a step that no longer works.

So the load-bearing half of it is executed rather than proof-read. The install
is rehearsed against a genuine `git clone` of this repo, and the linking step is
lifted out of the document and run as written, with `$HOME` and `--home` pointed
at throwaway directories so the real profile is never touched. The other half —
the dependency names and the key the doc tells members to export — is asserted
against the scripts' own constants, so a renamed package breaks a test instead
of a member's build.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from brainkit import REPO_ROOT, flatten, read_text

import ingest_docs
import ingest_web
import ingest_youtube
import transcribe

SETUP_PROMPT = os.path.join(REPO_ROOT, "SETUP-PROMPT.md")
README = os.path.join(REPO_ROOT, "README.md")
DEMOS_DIR = os.path.join(REPO_ROOT, "demos")
FIXTURE = "sourdough-baking"


def run(*argv):
    """A script, run the way the install document tells a member to run it."""
    return subprocess.run([sys.executable] + list(argv), capture_output=True,
                          text=True)


def linking_step():
    """The shell block from step 3, lifted out of the document to be run.

    Taken from the document rather than copied into the test on purpose: a
    rewritten step is then a step this suite actually runs, instead of one it
    quietly stops covering.
    """
    blocks = re.findall(r"```bash\n(.*?)```", read_text(SETUP_PROMPT), re.DOTALL)
    linking = [block for block in blocks if "ln -sfn" in block]
    if len(linking) != 1:
        raise AssertionError(
            "expected exactly one `ln -sfn` block in SETUP-PROMPT.md, found "
            "{}".format(len(linking)))
    return linking[0]


class InstallDocumentMatchesTheCode(unittest.TestCase):
    """Every dependency and key the document names, taken from the scripts."""

    def setUp(self):
        self.text = read_text(SETUP_PROMPT)

    def test_it_names_the_pip_line_each_arm_prints_for_itself(self):
        """A renamed package fails here, not half way through a member's build."""
        hints = set(ingest_docs.INSTALL_HINTS.values())
        hints.add(ingest_web.INSTALL_HINT)
        hints.add(ingest_youtube.INSTALL_HINT)
        self.assertTrue(hints)
        for hint in sorted(hints):
            with self.subTest(hint=hint):
                self.assertIn(hint, self.text)

    def test_it_names_the_transcription_key_the_engine_actually_reads(self):
        """Whatever the default engine reads is what the doc has to tell members."""
        self.assertIn(transcribe.ENGINES[transcribe.DEFAULT_ENGINE].key_env,
                      self.text)

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
        self.flat = flatten(read_text(README))

    def test_it_carries_the_one_paste_in_install(self):
        self.assertIn("clone https://github.com/luke-heka/brain-builder and "
                      "follow setup-prompt.md", self.flat)

    def test_it_names_all_three_shipped_components(self):
        for component in ("brain-builder", "brain-toggle", "blueprint"):
            with self.subTest(component=component):
                self.assertIn(component, self.flat)

    def test_it_keeps_the_instruction_file_harness_limit(self):
        self.assertIn("global-only in v1", self.flat.replace("*", ""))

    def test_it_keeps_the_same_directory_edge_case_honesty(self):
        self.assertIn("two concurrent sessions in the same directory",
                      self.flat.replace("*", ""))
        self.assertIn("give each brain its own working directory", self.flat)

    def test_it_states_the_rights_stance_and_links_the_detail(self):
        self.assertIn("docs/rights.md", self.flat)
        self.assertIn("built locally, on your machine", self.flat)

    def test_every_repo_path_it_links_exists(self):
        links = set(re.findall(r"\]\(([\w./-]+)\)", read_text(README)))
        self.assertTrue(links)
        for link in sorted(links):
            with self.subTest(link=link):
                self.assertTrue(os.path.exists(os.path.join(REPO_ROOT, link)))


class DemoPrompts(unittest.TestCase):
    """Three worked prompts, each a complete invocation with its fail questions."""

    DEMOS = ("ai-expert-karpathy.md", "marketing.md", "hormozi.md")

    def demo(self, name):
        return read_text(os.path.join(DEMOS_DIR, name))

    def test_all_three_demos_ship_with_an_index(self):
        for name in self.DEMOS + ("README.md",):
            with self.subTest(name=name):
                self.assertTrue(os.path.isfile(os.path.join(DEMOS_DIR, name)))

    def test_each_prompt_covers_what_the_intake_has_to_understand(self):
        """Four things understood up front is what earns zero questions."""
        for name in self.DEMOS:
            flat = flatten(self.demo(name))
            for phrase in ("what it's about", "what it's built from",
                           "where the sources are", "what i want to ask it"):
                with self.subTest(demo=name, phrase=phrase):
                    self.assertIn(phrase, flat)

    def test_each_demo_carries_fail_questions_across_the_three_types(self):
        for name in self.DEMOS:
            flat = flatten(self.demo(name))
            with self.subTest(demo=name):
                self.assertIn("## fail questions", flat)
            for failure_type in ("number —", "framework —", "voice —"):
                with self.subTest(demo=name, failure_type=failure_type):
                    self.assertIn(failure_type, flat)

    def test_every_fail_question_says_the_control_fails_confidently(self):
        """The criterion that makes a fail question worth anything."""
        for name in self.DEMOS:
            with self.subTest(demo=name):
                self.assertGreaterEqual(
                    self.demo(name).count("**A brain-less agent fails confidently"),
                    3)

    def test_an_unverified_answer_is_marked_rather_than_asserted(self):
        """No corpus, no certainty — the mark is the honesty."""
        for name in ("ai-expert-karpathy.md", "marketing.md"):
            with self.subTest(demo=name):
                self.assertIn("unverified-until-rebuild", self.demo(name))

    def test_the_hormozi_literals_name_the_page_and_the_video_they_came_from(self):
        """Verified means traceable, or it means nothing."""
        text = self.demo("hormozi.md")
        self.assertGreaterEqual(text.count("*Corpus answer verified*"), 3)
        self.assertIn("wiki/offers-and-money-models/ltv-to-cac-ratios.md", text)
        self.assertIn("persona/voice.md", text)

    def test_the_index_states_the_rebuilds_are_the_acceptance_test_and_unrun(self):
        flat = flatten(self.demo("README.md"))
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
        """What git tracks — a member's clone, rather than this working copy."""
        listing = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT,
                                 capture_output=True, text=True)
        self.assertEqual(0, listing.returncode, listing.stderr)
        for relpath in listing.stdout.split("\0"):
            if relpath and relpath not in self.EXEMPT:
                yield relpath, os.path.join(REPO_ROOT, relpath)

    def test_the_gbrain_push_is_gone_from_everything_that_ships(self):
        found = []
        for relpath, path in self.shipped_files():
            try:
                text = read_text(path).lower()
            except (UnicodeDecodeError, OSError):
                continue
            found += ["{}: {}".format(relpath, marker)
                      for marker in ("gbrain", "mcp__", "selrai-team")
                      if marker in text]
        self.assertEqual([], found, "internal infrastructure still shipped")


class FreshCloneInstall(unittest.TestCase):
    """The install document, executed against a real clone of this repo.

    This is the "fresh clone on a clean profile" check in runnable form. It
    clones over the local filesystem, so it needs no network; `$HOME` and
    `--home` both point at throwaway directories, so it never touches the real
    one.
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

    def link_skills(self):
        """Step 3, run verbatim from the document against a throwaway `$HOME`.

        `toggle.py resolve` expands `~`, which honours `$HOME`, so overriding it
        is what keeps the documented command — which takes no `--home` — off the
        real profile.
        """
        environ = dict(os.environ, HOME=self.home)
        return subprocess.run(["bash", "-c", linking_step()], cwd=self.clone,
                              env=environ, capture_output=True, text=True)

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

    def test_step_3_as_written_links_both_skills_out_of_the_clone(self):
        result = self.link_skills()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        for skill in ("brain-builder", "brain-toggle"):
            link = os.path.join(self.home, ".claude", "skills", skill)
            with self.subTest(skill=skill):
                self.assertTrue(os.path.islink(link))
                self.assertEqual(
                    os.path.realpath(os.path.join(self.clone, "skills", skill)),
                    os.path.realpath(link))
                self.assertTrue(os.path.isfile(os.path.join(link, "SKILL.md")))

    def test_step_3_is_idempotent_so_a_repeated_install_is_harmless(self):
        self.assertEqual(0, self.link_skills().returncode)
        second = self.link_skills()
        self.assertEqual(0, second.returncode, second.stdout + second.stderr)
        link = os.path.join(self.home, ".claude", "skills", "brain-builder")
        self.assertTrue(os.path.islink(link))

    def test_step_3_refuses_a_real_directory_instead_of_nesting_inside_it(self):
        """`ln -sfn` alone links *into* an existing directory and exits 0.

        That leaves `<skills>/brain-builder/brain-builder`, a dead skill and a
        healthy-looking `ls`. The guard in the documented block is what turns
        that into a stop.
        """
        occupied = os.path.join(self.home, ".claude", "skills", "brain-builder")
        os.makedirs(occupied)

        result = self.link_skills()

        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("is not a symlink", result.stderr)
        self.assertFalse(os.path.islink(occupied))
        self.assertFalse(os.path.exists(os.path.join(occupied, "brain-builder")))

    def test_step_4_lints_a_fixture_brain_clean_out_of_the_clone(self):
        result = run(os.path.join(self.builder, "lint.py"), self.brain())
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("valid brain — 0 error(s), 0 warning(s)", result.stdout)

    def test_step_4_regenerates_the_router_and_records_where_the_brain_now_is(self):
        """A copied brain is a moved brain, and the router records its root."""
        brain = self.brain()
        router = os.path.join(brain, "SKILL.md")
        self.assertIn("brain_root: ~/brains/" + FIXTURE, read_text(router))

        result = run(os.path.join(self.builder, "gen_router.py"), brain)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(router, result.stdout.strip())
        self.assertIn("brain_root: " + brain, read_text(router))

    def test_step_4_regeneration_in_place_is_a_no_op_diff(self):
        """No timestamps in the output, so the second run changes nothing."""
        brain = self.brain()
        router = os.path.join(brain, "SKILL.md")
        run(os.path.join(self.builder, "gen_router.py"), brain)
        once = read_text(router)
        run(os.path.join(self.builder, "gen_router.py"), brain)
        self.assertEqual(once, read_text(router))

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
        """Step 3 is a symlink loop precisely because `attach` takes brains only."""
        result = run(self.toggle, "attach",
                     os.path.join(self.clone, "skills", "brain-builder"),
                     "--home", self.home)
        self.assertEqual(1, result.returncode)
        self.assertIn("is not a brain", result.stderr)

    def test_the_suite_the_document_ends_on_runs_from_the_clone(self):
        """Step 4's last command, narrowed to one module.

        The document says `python3 -m unittest discover tests`; running all of
        it here would re-enter this class and clone the repo again, once per
        nesting level. `test_toggle.py` is the module the install path depends
        on, so it is the one worth proving runs out of a clone.
        """
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "tests", "-p",
             "test_toggle.py"],
            cwd=self.clone, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
