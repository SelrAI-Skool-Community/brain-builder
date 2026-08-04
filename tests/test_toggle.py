"""Attaching and detaching brains from harnesses (spec.md §7)."""
import contextlib
import io
import os
import unittest

from brainkit import FIXTURES_DIR, BrainOnDisk

from gen_router import write_router

import toggle


def real(path):
    """macOS hands out a symlinked temp dir; compare resolved paths."""
    return os.path.realpath(path)


class TargetResolution(BrainOnDisk):
    """Where a brain gets linked — the path the skill states before linking."""

    def test_the_global_target_is_the_harnesss_user_skills_directory(self):
        self.assertEqual(
            os.path.join(self.tmp, ".claude", "skills"),
            toggle.skills_dir("claude-code", "global", home=self.tmp))
        self.assertEqual(
            os.path.join(self.tmp, ".codex", "skills"),
            toggle.skills_dir("codex", "global", home=self.tmp))

    def test_the_project_target_is_the_git_root_when_inside_a_repo(self):
        repo = os.path.join(self.tmp, "repo")
        deep = os.path.join(repo, "src", "inner")
        os.makedirs(os.path.join(repo, ".git"))
        os.makedirs(deep)
        self.assertEqual(
            os.path.join(repo, ".claude", "skills"),
            toggle.skills_dir("claude-code", "project", cwd=deep))

    def test_the_project_target_falls_back_to_cwd_outside_a_repo(self):
        plain = os.path.join(self.tmp, "not-a-repo")
        os.makedirs(plain)
        self.assertEqual(
            os.path.join(plain, ".claude", "skills"),
            toggle.skills_dir("claude-code", "project", cwd=plain))

    def test_a_worktrees_dot_git_file_still_marks_the_project_root(self):
        tree = os.path.join(self.tmp, "tree")
        os.makedirs(tree)
        with open(os.path.join(tree, ".git"), "w", encoding="utf-8") as handle:
            handle.write("gitdir: /elsewhere/.git/worktrees/tree\n")
        self.assertEqual(tree, toggle.project_root(tree))

    def test_an_unknown_harness_is_refused_by_name(self):
        with self.assertRaises(toggle.ToggleError) as caught:
            toggle.skills_dir("emacs", "global", home=self.tmp)
        self.assertIn("emacs", str(caught.exception))

    def test_every_harness_names_the_scopes_it_supports(self):
        self.assertIn("claude-code", toggle.HARNESSES)
        self.assertIn("codex", toggle.HARNESSES)


class SymlinkArm(BrainOnDisk):
    """Attach is a symlink into a skills directory. Nothing is ever copied."""

    def setUp(self):
        super().setUp()
        self.skills = os.path.join(self.tmp, "harness", "skills")

    def link_path(self, slug="test-brain", skills=None):
        return os.path.join(skills or self.skills, slug)

    def test_attaching_symlinks_the_brain_under_its_slug(self):
        brain = self.minimal_brain()
        result = toggle.attach(brain, self.skills)
        self.assertEqual("linked", result.action)
        self.assertEqual(self.link_path(), result.link)
        self.assertTrue(os.path.islink(result.link))
        self.assertEqual(real(brain), os.path.realpath(result.link))

    def test_attaching_creates_the_skills_directory_if_it_is_missing(self):
        toggle.attach(self.minimal_brain(), self.skills)
        self.assertTrue(os.path.isdir(self.skills))

    def test_attaching_twice_is_idempotent_and_says_so(self):
        brain = self.minimal_brain()
        toggle.attach(brain, self.skills)
        again = toggle.attach(brain, self.skills)
        self.assertEqual("already-attached", again.action)
        self.assertEqual(1, len(os.listdir(self.skills)))

    def test_attaching_a_relocated_brain_repoints_the_existing_link(self):
        brain = self.minimal_brain()
        toggle.attach(brain, self.skills)
        moved = os.path.join(self.tmp, "moved", "test-brain")
        os.makedirs(os.path.dirname(moved))
        os.rename(brain, moved)
        result = toggle.attach(moved, self.skills)
        self.assertEqual("linked", result.action)
        self.assertEqual(real(moved), os.path.realpath(self.link_path()))
        self.assertEqual(1, len(os.listdir(self.skills)))

    def test_attaching_never_clobbers_a_real_directory_at_the_target(self):
        brain = self.minimal_brain()
        os.makedirs(self.link_path())
        with self.assertRaises(toggle.ToggleError) as caught:
            toggle.attach(brain, self.skills)
        self.assertIn("not a symlink", str(caught.exception))
        self.assertFalse(os.path.islink(self.link_path()))

    def test_a_folder_that_is_not_a_brain_is_refused_by_what_it_is_missing(self):
        not_a_brain = os.path.join(self.tmp, "notes")
        os.makedirs(not_a_brain)
        with self.assertRaises(toggle.ToggleError) as caught:
            toggle.attach(not_a_brain, self.skills)
        self.assertIn("index.md", str(caught.exception))

    def test_detaching_removes_the_link_and_leaves_the_brain_untouched(self):
        brain = self.minimal_brain()
        toggle.attach(brain, self.skills)
        removed = toggle.detach("test-brain", self.skills)
        self.assertEqual(self.link_path(), removed.link)
        self.assertEqual(real(brain), removed.target)
        self.assertFalse(os.path.lexists(self.link_path()))
        self.assertTrue(os.path.isfile(os.path.join(brain, "index.md")))

    def test_detaching_what_is_not_attached_reports_nothing_removed(self):
        os.makedirs(self.skills)
        self.assertIsNone(toggle.detach("test-brain", self.skills))

    def test_detaching_refuses_a_real_directory_rather_than_deleting_it(self):
        os.makedirs(self.link_path())
        with self.assertRaises(toggle.ToggleError):
            toggle.detach("test-brain", self.skills)
        self.assertTrue(os.path.isdir(self.link_path()))

    def test_listing_reports_each_attached_slug_and_its_target(self):
        brain = self.minimal_brain()
        other = self.minimal_brain(slug="other-brain")
        toggle.attach(brain, self.skills)
        toggle.attach(other, self.skills)
        found = {item.slug: item for item in toggle.attachments(self.skills)}
        self.assertEqual({"other-brain", "test-brain"}, set(found))
        self.assertEqual(real(brain), found["test-brain"].target)
        self.assertFalse(found["test-brain"].dangling)

    def test_listing_flags_a_link_whose_brain_has_gone_away(self):
        brain = self.minimal_brain()
        toggle.attach(brain, self.skills)
        os.rename(brain, brain + "-gone")
        self.assertTrue(toggle.attachments(self.skills)[0].dangling)

    def test_listing_ignores_real_skill_directories_the_member_wrote(self):
        os.makedirs(os.path.join(self.skills, "hand-written-skill"))
        self.assertEqual([], toggle.attachments(self.skills))

    def test_listing_a_missing_skills_directory_is_empty_not_an_error(self):
        self.assertEqual([], toggle.attachments(os.path.join(self.tmp, "nope")))


class ScopeChange(BrainOnDisk):
    """A brain attached globally is moved to a project, never duplicated."""

    def setUp(self):
        super().setUp()
        self.brain = self.minimal_brain()
        self.global_skills = os.path.join(self.tmp, "home", ".claude", "skills")
        self.project_skills = os.path.join(self.tmp, "proj", ".claude", "skills")

    def test_a_project_attach_stops_when_the_brain_is_already_global(self):
        toggle.attach(self.brain, self.global_skills)
        with self.assertRaises(toggle.AttachedElsewhere) as caught:
            toggle.attach(self.brain, self.project_skills,
                          elsewhere=[self.global_skills])
        self.assertEqual(os.path.join(self.global_skills, "test-brain"),
                         caught.exception.link)
        self.assertFalse(os.path.lexists(os.path.join(self.project_skills, "test-brain")))

    def test_moving_leaves_exactly_one_router_and_names_where_it_came_from(self):
        toggle.attach(self.brain, self.global_skills)
        result = toggle.attach(self.brain, self.project_skills,
                               elsewhere=[self.global_skills], move=True)
        self.assertEqual(os.path.join(self.global_skills, "test-brain"), result.moved_from)
        self.assertEqual([], toggle.attachments(self.global_skills))
        self.assertEqual(["test-brain"],
                         [item.slug for item in toggle.attachments(self.project_skills)])

    def test_a_same_named_link_to_a_different_brain_is_left_alone(self):
        impostor = self.minimal_brain(slug="decoy")
        os.makedirs(self.global_skills)
        os.symlink(impostor, os.path.join(self.global_skills, "test-brain"))
        result = toggle.attach(self.brain, self.project_skills,
                               elsewhere=[self.global_skills], move=True)
        self.assertIsNone(result.moved_from)
        self.assertEqual(real(impostor),
                         os.path.realpath(os.path.join(self.global_skills, "test-brain")))

    def test_a_global_attach_stops_when_the_brain_is_already_on_in_the_project(self):
        toggle.attach(self.brain, self.project_skills)
        with self.assertRaises(toggle.AttachedElsewhere):
            toggle.attach(self.brain, self.global_skills,
                          elsewhere=[self.project_skills])

    def test_an_unattached_brain_is_linked_straight_into_the_project(self):
        result = toggle.attach(self.brain, self.project_skills,
                               elsewhere=[self.global_skills])
        self.assertEqual("linked", result.action)
        self.assertIsNone(result.moved_from)


class RouterRoot(BrainOnDisk):
    """The router records where the brain lives; a moved brain needs a rebuild."""

    def test_attaching_a_brain_that_matches_its_recorded_root_warns_about_nothing(self):
        brain = self.minimal_brain()
        write_router(brain)
        result = toggle.attach(brain, os.path.join(self.tmp, "skills"))
        self.assertEqual([], result.warnings)

    def test_attaching_a_moved_brain_warns_and_names_the_regeneration_command(self):
        brain = self.minimal_brain()
        write_router(brain, recorded_root="~/brains/test-brain")
        result = toggle.attach(brain, os.path.join(self.tmp, "skills"))
        warning = " ".join(result.warnings)
        self.assertIn("~/brains/test-brain", warning)
        self.assertIn("gen_router.py", warning)
        self.assertIn("--root", warning)


class PointerArm(BrainOnDisk):
    """Instruction-file harnesses get a delimited, reversible pointer block."""

    MEMBER_TEXT = (
        "# My instructions\n\n"
        "Always answer in British English.\n\n"
        "## House style\n\n"
        "-   Loose  spacing  I  like.\n"
    )

    def setUp(self):
        super().setUp()
        self.brain = self.minimal_brain()
        self.instructions = os.path.join(self.tmp, "AGENTS.md")

    def write_instructions(self, text):
        with open(self.instructions, "w", encoding="utf-8") as handle:
            handle.write(text)

    def read_instructions(self):
        with open(self.instructions, encoding="utf-8") as handle:
            return handle.read()

    def test_the_block_is_delimited_by_the_slug_on_both_ends(self):
        block = toggle.render_pointer("test-brain", self.brain)
        self.assertTrue(block.startswith("<!-- brain: test-brain -->"))
        self.assertTrue(block.rstrip().endswith("<!-- /brain: test-brain -->"))
        self.assertIn(real(self.brain), block)

    def test_the_block_points_at_the_brain_and_never_carries_its_content(self):
        self.write(self.brain, "index.md",
                   "---\ntype: index\n---\n\n# Test\n\nHydration is 78 percent.\n")
        block = toggle.render_pointer("test-brain", self.brain)
        self.assertNotIn("Hydration is 78 percent", block)
        self.assertIn("index.md", block)
        self.assertLess(len(block.splitlines()), 8)

    def test_applying_appends_the_block_and_leaves_member_text_byte_identical(self):
        self.write_instructions(self.MEMBER_TEXT)
        toggle.apply_pointer(self.instructions, "test-brain", self.brain)
        text = self.read_instructions()
        self.assertTrue(text.startswith(self.MEMBER_TEXT))
        self.assertIn("<!-- brain: test-brain -->", text)

    def test_removing_restores_the_file_byte_for_byte(self):
        self.write_instructions(self.MEMBER_TEXT)
        toggle.apply_pointer(self.instructions, "test-brain", self.brain)
        self.assertTrue(toggle.remove_pointer(self.instructions, "test-brain"))
        self.assertEqual(self.MEMBER_TEXT, self.read_instructions())

    def test_a_trailing_blank_line_the_member_wrote_survives_the_round_trip(self):
        original = self.MEMBER_TEXT + "\n"
        self.write_instructions(original)
        toggle.apply_pointer(self.instructions, "test-brain", self.brain)
        toggle.remove_pointer(self.instructions, "test-brain")
        self.assertEqual(original, self.read_instructions())

    def test_applying_twice_leaves_exactly_one_block(self):
        self.write_instructions(self.MEMBER_TEXT)
        toggle.apply_pointer(self.instructions, "test-brain", self.brain)
        action = toggle.apply_pointer(self.instructions, "test-brain", self.brain)
        self.assertEqual("unchanged", action)
        self.assertEqual(1, self.read_instructions().count("<!-- brain: test-brain -->"))

    def test_a_moved_brain_updates_its_block_in_place(self):
        self.write_instructions(self.MEMBER_TEXT)
        toggle.apply_pointer(self.instructions, "test-brain", self.brain)
        moved = os.path.join(self.tmp, "elsewhere", "test-brain")
        os.makedirs(os.path.dirname(moved))
        os.rename(self.brain, moved)
        self.assertEqual("updated",
                         toggle.apply_pointer(self.instructions, "test-brain", moved))
        text = self.read_instructions()
        self.assertEqual(1, text.count("<!-- brain: test-brain -->"))
        self.assertIn(real(moved), text)
        self.assertTrue(text.startswith(self.MEMBER_TEXT))

    def test_two_brains_keep_separate_blocks_and_detach_independently(self):
        other = self.minimal_brain(slug="other-brain")
        self.write_instructions(self.MEMBER_TEXT)
        toggle.apply_pointer(self.instructions, "test-brain", self.brain)
        toggle.apply_pointer(self.instructions, "other-brain", other)
        toggle.remove_pointer(self.instructions, "test-brain")
        text = self.read_instructions()
        self.assertNotIn("<!-- brain: test-brain -->", text)
        self.assertIn("<!-- brain: other-brain -->", text)
        self.assertTrue(text.startswith(self.MEMBER_TEXT))

    def test_applying_to_a_file_that_does_not_exist_yet_creates_it(self):
        action = toggle.apply_pointer(self.instructions, "test-brain", self.brain)
        self.assertEqual("added", action)
        self.assertTrue(self.read_instructions().startswith("<!-- brain: test-brain -->"))

    def test_an_unreadable_instruction_file_is_never_overwritten_with_the_block(self):
        directory_not_a_file = os.path.join(self.tmp, "instructions-dir")
        os.makedirs(directory_not_a_file)
        with self.assertRaises(OSError):
            toggle.apply_pointer(directory_not_a_file, "test-brain", self.brain)
        self.assertTrue(os.path.isdir(directory_not_a_file))

    def test_removing_a_block_that_is_not_there_changes_nothing(self):
        self.write_instructions(self.MEMBER_TEXT)
        self.assertFalse(toggle.remove_pointer(self.instructions, "test-brain"))
        self.assertEqual(self.MEMBER_TEXT, self.read_instructions())

    def test_the_diff_shows_the_pending_change_without_writing_anything(self):
        self.write_instructions(self.MEMBER_TEXT)
        diff = toggle.pointer_diff(self.instructions, "test-brain", self.brain)
        self.assertIn("+<!-- brain: test-brain -->", diff)
        self.assertEqual(self.MEMBER_TEXT, self.read_instructions())

    def test_the_diff_is_empty_when_the_block_is_already_right(self):
        self.write_instructions(self.MEMBER_TEXT)
        toggle.apply_pointer(self.instructions, "test-brain", self.brain)
        self.assertEqual("", toggle.pointer_diff(self.instructions, "test-brain", self.brain))


class CommandLine(BrainOnDisk):
    """The surface SKILL.md drives. `--home` keeps tests off the real machine."""

    def setUp(self):
        super().setUp()
        self.home = os.path.join(self.tmp, "home")
        self.project = os.path.join(self.tmp, "project")
        os.makedirs(os.path.join(self.project, ".git"))

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = toggle.main(["toggle.py"] + list(args))
        return code, out.getvalue(), err.getvalue()

    def home_skills(self, harness="claude-code"):
        return toggle.skills_dir(harness, "global", home=self.home)

    def test_resolve_states_the_path_before_anything_is_linked(self):
        code, out, _ = self.run_cli("resolve", "--scope", "project",
                                    "--cwd", os.path.join(self.project, "deep"))
        self.assertEqual(0, code)
        self.assertEqual(os.path.join(self.project, ".claude", "skills"), out.strip())

    def test_attach_defaults_to_global_and_reports_the_target(self):
        brain = self.minimal_brain()
        code, out, _ = self.run_cli("attach", brain, "--home", self.home)
        self.assertEqual(0, code)
        self.assertIn(self.home_skills(), out)
        self.assertTrue(os.path.islink(os.path.join(self.home_skills(), "test-brain")))

    def test_attach_to_a_project_targets_the_git_root(self):
        brain = self.minimal_brain()
        code, out, _ = self.run_cli("attach", brain, "--scope", "project",
                                    "--cwd", self.project, "--home", self.home)
        self.assertEqual(0, code)
        self.assertIn(os.path.join(self.project, ".claude", "skills"), out)
        self.assertFalse(os.path.exists(self.home_skills()))

    def test_attach_to_a_project_stops_on_a_global_attachment_with_its_own_code(self):
        brain = self.minimal_brain()
        self.run_cli("attach", brain, "--home", self.home)
        code, _, err = self.run_cli("attach", brain, "--scope", "project",
                                    "--cwd", self.project, "--home", self.home)
        self.assertEqual(3, code)
        self.assertIn("--move", err)
        self.assertFalse(os.path.lexists(
            os.path.join(self.project, ".claude", "skills", "test-brain")))

    def test_attach_move_relocates_the_only_router(self):
        brain = self.minimal_brain()
        self.run_cli("attach", brain, "--home", self.home)
        code, out, _ = self.run_cli("attach", brain, "--scope", "project", "--move",
                                    "--cwd", self.project, "--home", self.home)
        self.assertEqual(0, code)
        self.assertIn("moved", out)
        self.assertEqual([], toggle.attachments(self.home_skills()))
        self.assertEqual(["test-brain"], [item.slug for item in toggle.attachments(
            os.path.join(self.project, ".claude", "skills"))])

    def test_detach_removes_the_link_and_says_so(self):
        brain = self.minimal_brain()
        self.run_cli("attach", brain, "--home", self.home)
        code, out, _ = self.run_cli("detach", "test-brain", "--home", self.home)
        self.assertEqual(0, code)
        self.assertIn("detached", out)
        self.assertEqual([], toggle.attachments(self.home_skills()))

    def test_detaching_what_is_not_attached_is_not_an_error(self):
        code, out, _ = self.run_cli("detach", "test-brain", "--home", self.home)
        self.assertEqual(0, code)
        self.assertIn("not attached", out)

    def test_list_reports_every_scope_it_scanned_and_what_is_attached(self):
        brain = self.minimal_brain()
        self.run_cli("attach", brain, "--home", self.home)
        code, out, _ = self.run_cli("list", "--home", self.home, "--cwd", self.project)
        self.assertEqual(0, code)
        self.assertIn(self.home_skills(), out)
        self.assertIn(os.path.join(self.project, ".claude", "skills"), out)
        self.assertIn("test-brain", out)
        self.assertIn("global", out)

    def test_pointer_diff_writes_nothing_and_pointer_add_then_remove_round_trips(self):
        brain = self.minimal_brain()
        instructions = os.path.join(self.tmp, "AGENTS.md")
        original = "# Mine\n\nKeep this exactly.\n"
        with open(instructions, "w", encoding="utf-8") as handle:
            handle.write(original)

        code, out, _ = self.run_cli("pointer-diff", instructions, brain)
        self.assertEqual(0, code)
        self.assertIn("+<!-- brain: test-brain -->", out)
        with open(instructions, encoding="utf-8") as handle:
            self.assertEqual(original, handle.read())

        self.assertEqual(0, self.run_cli("pointer-add", instructions, brain, "--yes")[0])
        self.assertEqual(0, self.run_cli("pointer-remove", instructions, "test-brain")[0])
        with open(instructions, encoding="utf-8") as handle:
            self.assertEqual(original, handle.read())

    def test_the_first_block_into_a_file_shows_the_diff_and_waits(self):
        """spec §7: the pointer arm shows the diff on first use.

        The instruction file is the member's own and is injected whole on every
        turn, so the first write into one is not made until they have seen it.
        Exit 3 is "needs a decision", not a failure.
        """
        brain = self.minimal_brain()
        instructions = os.path.join(self.tmp, "AGENTS.md")
        original = "# Mine\n"
        with open(instructions, "w", encoding="utf-8") as handle:
            handle.write(original)

        code, out, err = self.run_cli("pointer-add", instructions, brain)

        self.assertEqual(3, code)
        self.assertIn("+<!-- brain: test-brain -->", out)
        self.assertIn("--yes", err)
        with open(instructions, encoding="utf-8") as handle:
            self.assertEqual(original, handle.read(), "nothing was written")

    def test_updating_a_block_that_is_already_there_needs_no_second_consent(self):
        """Only the *first* block is unseen; a re-point is a change to their yes."""
        brain = self.minimal_brain()
        instructions = os.path.join(self.tmp, "AGENTS.md")
        self.assertEqual(0, self.run_cli("pointer-add", instructions, brain, "--yes")[0])

        self.assertEqual(0, self.run_cli("pointer-add", instructions, brain)[0],
                         "the block is already there — nothing unseen to show")

    def test_a_file_created_only_for_the_block_does_not_survive_removal(self):
        """Reversible means the harness sees what it saw before — not 0 bytes."""
        brain = self.minimal_brain()
        instructions = os.path.join(self.tmp, "GEMINI.md")

        self.run_cli("pointer-add", instructions, brain, "--yes")
        self.assertTrue(os.path.isfile(instructions))

        self.assertEqual(0, self.run_cli("pointer-remove", instructions, "test-brain")[0])
        self.assertFalse(os.path.exists(instructions))

    def test_an_unknown_command_is_a_usage_error(self):
        self.assertEqual(2, self.run_cli("frobnicate")[0])

    def test_bare_invocation_prints_usage_to_stderr_and_fails(self):
        code, out, err = self.run_cli()
        self.assertEqual(2, code)
        self.assertEqual("", out)
        self.assertIn("usage:", err)

    def test_help_prints_usage_to_stdout_and_succeeds(self):
        code, out, _ = self.run_cli("--help")
        self.assertEqual(0, code)
        self.assertIn("usage:", out)

    def test_a_global_attach_over_a_project_one_stops_too(self):
        brain = self.minimal_brain()
        self.run_cli("attach", brain, "--scope", "project",
                     "--cwd", self.project, "--home", self.home)
        code, _, err = self.run_cli("attach", brain, "--cwd", self.project,
                                    "--home", self.home)
        self.assertEqual(3, code)
        self.assertIn("--move", err)

    def test_the_same_brain_may_be_attached_to_a_second_harness(self):
        brain = self.minimal_brain()
        self.run_cli("attach", brain, "--home", self.home)
        code, _, _ = self.run_cli("attach", brain, "--harness", "codex",
                                  "--home", self.home)
        self.assertEqual(0, code)
        self.assertEqual(["test-brain"], [item.slug for item in toggle.attachments(
            self.home_skills("codex"))])

    def test_attaching_something_that_is_not_a_brain_fails_without_linking(self):
        code, _, err = self.run_cli("attach", self.tmp, "--home", self.home)
        self.assertEqual(1, code)
        self.assertIn("not a brain", err)


class DemoPath(BrainOnDisk):
    """The shipped demo: the fixture brain on globally, then per project, then off."""

    def setUp(self):
        super().setUp()
        self.brain = os.path.join(FIXTURES_DIR, "sourdough-baking")
        self.home = os.path.join(self.tmp, "home")
        self.project = os.path.join(self.tmp, "project")
        os.makedirs(os.path.join(self.project, ".git"))

    def test_attach_globally_then_move_to_a_project_then_detach_leaves_nothing(self):
        global_skills = toggle.skills_dir("claude-code", "global", home=self.home)
        project_skills = toggle.skills_dir("claude-code", "project", cwd=self.project)

        first = toggle.attach(self.brain, global_skills)
        self.assertEqual("linked", first.action)
        self.assertEqual(["sourdough-baking"],
                         [item.slug for item in toggle.attachments(global_skills)])

        moved = toggle.attach(self.brain, project_skills,
                              elsewhere=[global_skills], move=True)
        self.assertEqual(first.link, moved.moved_from)
        self.assertEqual([], toggle.attachments(global_skills))
        self.assertEqual(["sourdough-baking"],
                         [item.slug for item in toggle.attachments(project_skills)])

        toggle.detach("sourdough-baking", project_skills)
        self.assertEqual([], toggle.attachments(project_skills))
        self.assertTrue(os.path.isfile(os.path.join(self.brain, "index.md")))

    def test_the_fixture_brain_satisfies_the_pre_attach_check(self):
        try:
            toggle.check_brain(self.brain)
        except toggle.ToggleError as refused:
            self.fail("the shipped fixture brain was refused: {}".format(refused))


if __name__ == "__main__":
    unittest.main()
