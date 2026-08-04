"""The closing beat: the brain opened in Obsidian, as a picture of itself.

Nothing here launches an app, installs software, or reads the machine's real
Obsidian config. The whole module hangs off one `Machine` — an OS name, a home
directory, what is on disk, what is on `PATH`, and something that runs
commands — so every branch is exercised against fakes and temp directories.

What is actually under test is the honesty of the thing: a garnish that cannot
fail the build. Every failure path has to come back as a `Reveal` carrying a
line the member can act on, never as an exception.
"""
import json
import os
import subprocess
import sys
import unittest

import brainkit  # noqa: F401 — puts the skill's scripts/ on the import path
from brainkit import BrainOnDisk

import open_in_obsidian as obsidian


def machine(system="macos", home="/home/member", files=(), tools=(), replies=None,
            **kwargs):
    """A pretend computer: what exists, what is installed, what commands say."""
    replies = dict(replies or {})

    def runner(argv):
        return replies.get(argv[0], (0, ""))

    return obsidian.Machine(system=system, home=home, files=list(files),
                            tools=list(tools), runner=runner, **kwargs)


class ConfigLocations(unittest.TestCase):
    """Obsidian keeps its vault list in one JSON file, in a different place per OS."""

    def test_macos_keeps_it_under_application_support(self):
        found = obsidian.registry_path(machine("macos", "/Users/m"))
        self.assertEqual("/Users/m/Library/Application Support/obsidian/obsidian.json",
                         found)

    def test_windows_follows_appdata_when_the_environment_states_it(self):
        found = obsidian.registry_path(machine(
            "windows", "C:\\Users\\m", environ={"APPDATA": "C:\\Users\\m\\Roaming"}))
        self.assertTrue(found.startswith("C:\\Users\\m\\Roaming"), found)
        self.assertTrue(found.endswith("obsidian.json"), found)

    def test_windows_falls_back_to_the_usual_roaming_path(self):
        found = obsidian.registry_path(machine("windows", "C:\\Users\\m", environ={}))
        self.assertIn("AppData", found)
        self.assertIn("Roaming", found)

    def test_linux_uses_the_xdg_config_home_when_one_is_set(self):
        found = obsidian.registry_path(machine(
            "linux", "/home/m", environ={"XDG_CONFIG_HOME": "/home/m/.conf"}))
        self.assertEqual("/home/m/.conf/obsidian/obsidian.json", found)

    def test_linux_prefers_the_flatpak_config_when_that_is_the_install(self):
        """A flatpak Obsidian never reads `~/.config` — writing there is a no-op."""
        flatpak = "/home/m/.var/app/md.obsidian.Obsidian/config/obsidian"
        found = obsidian.registry_path(machine("linux", "/home/m", files=[flatpak]))
        self.assertEqual(os.path.join(flatpak, "obsidian.json"), found)


class Detection(unittest.TestCase):
    """Whether Obsidian is here at all, asked the cheapest way each OS allows."""

    def test_macos_sees_the_app_bundle(self):
        self.assertTrue(obsidian.installed(
            machine("macos", files=["/Applications/Obsidian.app"])))

    def test_macos_also_sees_it_installed_for_one_user_only(self):
        self.assertTrue(obsidian.installed(
            machine("macos", home="/Users/m",
                    files=["/Users/m/Applications/Obsidian.app"])))

    def test_macos_falls_back_to_spotlight_before_giving_up(self):
        """Members drag it anywhere; `mdfind` is how the OS answers that."""
        self.assertTrue(obsidian.installed(machine(
            "macos", tools=["mdfind"],
            replies={"mdfind": (0, "/Users/m/Dev/Obsidian.app\n")})))

    def test_spotlight_finding_nothing_is_not_an_install(self):
        self.assertFalse(obsidian.installed(machine(
            "macos", tools=["mdfind"], replies={"mdfind": (0, "\n")})))

    def test_windows_sees_the_per_user_install(self):
        found = machine("windows", home="C:\\Users\\m",
                        environ={"LOCALAPPDATA": "C:\\Users\\m\\Local"},
                        files=["C:\\Users\\m\\Local\\Obsidian\\Obsidian.exe"])
        self.assertTrue(obsidian.installed(found))

    def test_windows_asks_winget_when_no_exe_is_where_it_should_be(self):
        self.assertTrue(obsidian.installed(machine(
            "windows", tools=["winget"],
            replies={"winget": (0, "Obsidian  Obsidian.Obsidian  1.5.3\n")})))

    def test_winget_reporting_no_package_is_not_an_install(self):
        self.assertFalse(obsidian.installed(machine(
            "windows", tools=["winget"],
            replies={"winget": (1, "No installed package found\n")})))

    def test_linux_sees_it_on_the_path(self):
        self.assertTrue(obsidian.installed(machine("linux", tools=["obsidian"])))

    def test_linux_sees_the_flatpak(self):
        self.assertTrue(obsidian.installed(machine(
            "linux", tools=["flatpak"],
            replies={"flatpak": (0, "md.obsidian.Obsidian\n")})))

    def test_a_machine_with_none_of_it_says_so(self):
        self.assertFalse(obsidian.installed(machine("macos")))
        self.assertFalse(obsidian.installed(machine("linux")))
        self.assertFalse(obsidian.installed(machine("windows")))

    def test_an_unknown_operating_system_is_not_guessed_at(self):
        self.assertFalse(obsidian.installed(machine("plan9")))


class Installers(unittest.TestCase):
    """One package manager per OS, and no install at all when none is there."""

    def test_macos_installs_the_cask_when_homebrew_is_present(self):
        route = obsidian.installer(machine("macos", tools=["brew"]))
        self.assertEqual("Homebrew", route.label)
        self.assertEqual(["brew", "install", "--cask", "obsidian"], route.argv)

    def test_windows_installs_through_winget(self):
        route = obsidian.installer(machine("windows", tools=["winget"]))
        self.assertEqual("winget", route.label)
        self.assertIn("Obsidian.Obsidian", route.argv)

    def test_linux_installs_the_flatpak(self):
        route = obsidian.installer(machine("linux", tools=["flatpak"]))
        self.assertEqual("Flatpak", route.label)
        self.assertIn("md.obsidian.Obsidian", route.argv)

    def test_no_package_manager_means_no_route_rather_than_a_guess(self):
        self.assertIsNone(obsidian.installer(machine("macos")))
        self.assertIsNone(obsidian.installer(machine("linux")))
        self.assertIsNone(obsidian.installer(machine("plan9", tools=["brew"])))


class TheUri(unittest.TestCase):
    """`obsidian://open?path=` is the only documented way in — there is no graph action."""

    def test_the_path_is_percent_encoded_whole(self):
        uri = obsidian.vault_uri("/Users/m/brains/my brain")
        self.assertEqual(
            "obsidian://open?path=%2FUsers%2Fm%2Fbrains%2Fmy%20brain", uri)

    def test_a_windows_path_survives_its_backslashes(self):
        uri = obsidian.vault_uri("C:\\Users\\m\\brains\\b")
        self.assertIn("%5C", uri)
        self.assertNotIn("\\", uri)


class VaultRegistry(BrainOnDisk):
    """Registering the brain as a vault — minimally, and never over anyone else's."""

    def registry(self, payload=None, home=None):
        """A temp macOS config dir, optionally with an `obsidian.json` in it."""
        home = home or os.path.join(self.tmp, "home")
        directory = os.path.join(home, "Library", "Application Support", "obsidian")
        os.makedirs(directory, exist_ok=True)
        if payload is not None:
            with open(os.path.join(directory, "obsidian.json"), "w",
                      encoding="utf-8") as handle:
                handle.write(payload if isinstance(payload, str)
                             else json.dumps(payload))
        return machine("macos", home=home)

    def vaults(self, machine_):
        with open(obsidian.registry_path(machine_), encoding="utf-8") as handle:
            return json.load(handle)["vaults"]

    def test_a_brain_that_is_not_a_vault_yet_becomes_one(self):
        brain = self.minimal_brain()
        found = self.registry({"vaults": {}})
        self.assertEqual("added", obsidian.register(brain, found))
        paths = [vault["path"] for vault in self.vaults(found).values()]
        self.assertEqual([brain], paths)

    def test_the_entry_carries_the_fields_obsidian_writes_itself(self):
        brain = self.minimal_brain()
        found = self.registry({"vaults": {}})
        obsidian.register(brain, found)
        (identifier, entry), = self.vaults(found).items()
        self.assertEqual(16, len(identifier))
        self.assertTrue(all(char in "0123456789abcdef" for char in identifier))
        self.assertEqual(brain, entry["path"])
        self.assertIsInstance(entry["ts"], int)

    def test_registering_twice_does_not_add_the_brain_twice(self):
        brain = self.minimal_brain()
        found = self.registry({"vaults": {}})
        obsidian.register(brain, found)
        self.assertEqual("already", obsidian.register(brain, found))
        self.assertEqual(1, len(self.vaults(found)))

    def test_a_vault_the_member_already_registered_is_left_exactly_as_it_was(self):
        """Their own entry, their own id — we recognise it by path and stop."""
        brain = self.minimal_brain()
        found = self.registry({"vaults": {
            "aaaaaaaaaaaaaaaa": {"path": brain, "ts": 1, "open": True}}})
        self.assertEqual("already", obsidian.register(brain, found))
        self.assertEqual({"aaaaaaaaaaaaaaaa": {"path": brain, "ts": 1, "open": True}},
                         self.vaults(found))

    def test_every_other_vault_and_every_other_setting_survives(self):
        brain = self.minimal_brain()
        found = self.registry({
            "vaults": {"bbbbbbbbbbbbbbbb": {"path": "/elsewhere", "ts": 7}},
            "updates": {"channel": "beta"},
        })
        obsidian.register(brain, found)
        with open(obsidian.registry_path(found), encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual({"channel": "beta"}, payload["updates"])
        self.assertEqual({"path": "/elsewhere", "ts": 7},
                         payload["vaults"]["bbbbbbbbbbbbbbbb"])
        self.assertEqual(2, len(payload["vaults"]))

    def test_a_trailing_slash_is_the_same_vault(self):
        brain = self.minimal_brain()
        found = self.registry({"vaults": {"cccccccccccccccc": {"path": brain, "ts": 1}}})
        self.assertEqual("already", obsidian.register(brain + os.sep, found))

    def test_no_config_at_all_is_left_alone_rather_than_invented(self):
        """Obsidian has never run. Writing its config for it is the invasive move."""
        home = os.path.join(self.tmp, "fresh")
        found = machine("macos", home=home)
        self.assertEqual("absent", obsidian.register(self.minimal_brain(), found))
        self.assertFalse(os.path.exists(obsidian.registry_path(found)))

    def test_an_unreadable_config_is_never_clobbered(self):
        brain = self.minimal_brain()
        found = self.registry("{not json at all")
        self.assertEqual("unreadable", obsidian.register(brain, found))
        with open(obsidian.registry_path(found), encoding="utf-8") as handle:
            self.assertEqual("{not json at all", handle.read())

    def test_a_config_with_no_vaults_key_gains_one_without_losing_the_rest(self):
        brain = self.minimal_brain()
        found = self.registry({"updates": {"channel": "stable"}})
        self.assertEqual("added", obsidian.register(brain, found))
        with open(obsidian.registry_path(found), encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual({"channel": "stable"}, payload["updates"])
        self.assertEqual(1, len(payload["vaults"]))

    def test_a_dry_run_reports_what_it_would_do_and_writes_nothing(self):
        brain = self.minimal_brain()
        found = self.registry({"vaults": {}})
        found.dry = True
        self.assertEqual("added", obsidian.register(brain, found))
        self.assertEqual({}, self.vaults(found))


class TheReveal(BrainOnDisk):
    """The whole step, end to end, on machines in every state it can meet."""

    def ready(self, **kwargs):
        """A machine with Obsidian installed and a config it has already written."""
        home = os.path.join(self.tmp, "home")
        directory = os.path.join(home, "Library", "Application Support", "obsidian")
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "obsidian.json"), "w",
                  encoding="utf-8") as handle:
            handle.write('{"vaults": {}}')
        kwargs.setdefault("files", ["/Applications/Obsidian.app"])
        return machine("macos", home=home, **kwargs)

    def test_an_installed_obsidian_gets_the_vault_registered_and_opened(self):
        brain = self.minimal_brain()
        found = self.ready()
        reveal = obsidian.reveal(brain, found)
        self.assertTrue(reveal.ok)
        self.assertTrue(reveal.installed)
        self.assertFalse(reveal.installed_now)
        self.assertEqual("added", reveal.vault)
        self.assertTrue(reveal.opened)
        self.assertEqual([["open", obsidian.vault_uri(brain)]], found.commands)

    def test_a_missing_obsidian_is_installed_through_the_package_manager(self):
        """An installer that exits 0 installed it — re-detecting races the disk."""
        brain = self.minimal_brain()
        found = self.ready(files=[], tools=["brew"])
        reveal = obsidian.reveal(brain, found)
        self.assertTrue(reveal.installed_now)
        self.assertEqual("Homebrew", reveal.install)
        self.assertEqual(["brew", "install", "--cask", "obsidian"], found.commands[0])
        self.assertTrue(reveal.opened)

    def test_an_install_that_fails_is_one_calm_line_not_an_exception(self):
        brain = self.minimal_brain()
        found = self.ready(files=[], tools=["brew"],
                           replies={"brew": (1, "could not download\n")})
        reveal = obsidian.reveal(brain, found)
        self.assertFalse(reveal.ok)
        self.assertFalse(reveal.opened)
        self.assertIn(obsidian.DOWNLOAD, " ".join(reveal.trouble))

    def test_no_package_manager_falls_back_to_the_download_link(self):
        brain = self.minimal_brain()
        found = self.ready(files=[])
        reveal = obsidian.reveal(brain, found)
        self.assertFalse(reveal.installed)
        self.assertFalse(reveal.opened)
        self.assertEqual([], found.commands)
        trouble = " ".join(reveal.trouble)
        self.assertIn(obsidian.DOWNLOAD, trouble)
        self.assertIn("vault", trouble.lower())

    def test_installing_can_be_declined_and_then_nothing_is_installed(self):
        brain = self.minimal_brain()
        found = self.ready(files=[], tools=["brew"])
        reveal = obsidian.reveal(brain, found, install=False)
        self.assertEqual([], found.commands)
        self.assertIn(obsidian.DOWNLOAD, " ".join(reveal.trouble))

    def test_a_launcher_that_fails_still_returns_a_reveal(self):
        brain = self.minimal_brain()
        found = self.ready(replies={"open": (1, "")})
        reveal = obsidian.reveal(brain, found)
        self.assertFalse(reveal.opened)
        self.assertFalse(reveal.ok)
        self.assertTrue(reveal.trouble)

    def test_a_launcher_that_explodes_is_caught_rather_than_raised(self):
        """A garnish never takes the build down with it."""
        brain = self.minimal_brain()

        def explode(argv):
            raise OSError("no such thing as `open` here")

        found = obsidian.Machine(system="macos", home=self.tmp,
                                 files=["/Applications/Obsidian.app"],
                                 tools=[], runner=explode)
        reveal = obsidian.reveal(brain, found)
        self.assertFalse(reveal.opened)
        self.assertTrue(reveal.trouble)

    def test_windows_and_linux_each_get_their_own_launcher(self):
        brain = self.minimal_brain()
        windows = machine("windows", home=self.tmp,
                          environ={"LOCALAPPDATA": self.tmp},
                          files=[os.path.join(self.tmp, "Obsidian", "Obsidian.exe")])
        obsidian.reveal(brain, windows)
        self.assertEqual("cmd", windows.commands[-1][0])
        self.assertIn(obsidian.vault_uri(brain), windows.commands[-1])

        linux = machine("linux", home=self.tmp, tools=["obsidian", "xdg-open"])
        obsidian.reveal(brain, linux)
        self.assertEqual(["xdg-open", obsidian.vault_uri(brain)], linux.commands[-1])

    def test_the_config_being_absent_still_opens_and_says_what_is_left_to_click(self):
        """Obsidian has never run: it opens on its own vault picker, so say so."""
        brain = self.minimal_brain()
        found = machine("macos", home=os.path.join(self.tmp, "fresh"),
                        files=["/Applications/Obsidian.app"])
        reveal = obsidian.reveal(brain, found)
        self.assertEqual("absent", reveal.vault)
        self.assertTrue(reveal.opened)
        self.assertIn("vault", " ".join(reveal.trouble).lower())

    def test_a_dry_run_touches_nothing_and_launches_nothing(self):
        brain = self.minimal_brain()
        found = self.ready()
        found.dry = True
        reveal = obsidian.reveal(brain, found)
        self.assertTrue(reveal.dry)
        self.assertEqual([["open", obsidian.vault_uri(brain)]], found.commands)
        with open(obsidian.registry_path(found), encoding="utf-8") as handle:
            self.assertEqual({}, json.load(handle)["vaults"])

    def test_the_line_says_where_it_opened_and_that_the_graph_is_one_click(self):
        brain = self.minimal_brain()
        reveal = obsidian.reveal(brain, self.ready())
        line = reveal.line()
        self.assertIn(os.path.basename(brain), line)
        self.assertIn("graph", line.lower())

    def test_the_report_is_machine_readable_all_the_way_down(self):
        brain = self.minimal_brain()
        payload = obsidian.reveal(brain, self.ready()).as_dict()
        self.assertEqual(True, payload["opened"])
        self.assertEqual("added", payload["vault"])
        self.assertEqual(obsidian.vault_uri(brain), payload["uri"])
        json.dumps(payload)  # nothing in it is unserialisable


class Checking(BrainOnDisk):
    """`--check` answers what the machine looks like and changes none of it."""

    def test_it_reports_state_without_installing_registering_or_opening(self):
        brain = self.minimal_brain()
        found = machine("macos", home=os.path.join(self.tmp, "fresh"),
                        tools=["brew"])
        state = obsidian.inspect(brain, found)
        self.assertEqual([], found.commands)
        self.assertEqual(False, state["installed"])
        self.assertEqual("Homebrew", state["installer"])
        self.assertEqual("absent", state["vault"])
        self.assertEqual(obsidian.vault_uri(brain), state["uri"])

    def test_it_recognises_a_brain_that_is_already_a_vault(self):
        brain = self.minimal_brain()
        home = os.path.join(self.tmp, "home")
        directory = os.path.join(home, "Library", "Application Support", "obsidian")
        os.makedirs(directory)
        with open(os.path.join(directory, "obsidian.json"), "w",
                  encoding="utf-8") as handle:
            json.dump({"vaults": {"dddddddddddddddd": {"path": brain, "ts": 2}}}, handle)
        state = obsidian.inspect(brain, machine("macos", home=home))
        self.assertEqual("registered", state["vault"])


class TheCli(BrainOnDisk):
    """The commands the skill actually writes down, run as the skill writes them."""

    script = os.path.join(brainkit.SCRIPTS_DIR, "open_in_obsidian.py")

    def run_it(self, *argv):
        return subprocess.run([sys.executable, self.script] + list(argv),
                              capture_output=True, text=True)

    def test_no_arguments_is_a_usage_error(self):
        result = self.run_it()
        self.assertEqual(2, result.returncode)
        self.assertIn("usage", (result.stdout + result.stderr).lower())

    def test_an_unknown_flag_is_a_usage_error(self):
        result = self.run_it(self.minimal_brain(), "--turbo")
        self.assertEqual(2, result.returncode)

    def test_a_folder_that_is_not_there_is_a_usage_error(self):
        result = self.run_it(os.path.join(self.tmp, "nope"))
        self.assertEqual(2, result.returncode)

    def test_check_prints_json_and_runs_no_commands(self):
        result = self.run_it(self.minimal_brain(), "--check")
        self.assertEqual(0, result.returncode)
        state = json.loads(result.stdout)
        self.assertIn("installed", state)
        self.assertIn("vault", state)

    def test_a_dry_run_reports_without_installing_or_launching_anything(self):
        result = self.run_it(self.minimal_brain(), "--dry-run", "--json")
        self.assertEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["dry"])


if __name__ == "__main__":
    unittest.main()
