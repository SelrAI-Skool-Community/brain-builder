#!/usr/bin/env python3
"""The closing beat of a build: the brain, opened as a picture of itself.

    python3 open_in_obsidian.py <brain> [--json] [--home DIR]
    python3 open_in_obsidian.py <brain> --check [--json] [--home DIR]

A brain is a folder of linked markdown, which is exactly what Obsidian draws —
so the last thing a member sees is not a file listing but their own material as
a graph of connected pages. That picture is the proof the wiki is a wiki.

**This step is a garnish and behaves like one.** Nothing here can fail a build.
Every path that does not work comes back as a `Reveal` carrying a line the
member can act on, never as an exception. The exit code says only whether
Obsidian opened — a 1 means the picture is missing, never that the brain is
wrong, and the skill turns it into one calm line. Bad arguments are the one
hard failure, and exit 2 like every other script here.

**What is automated, and what is not.** Obsidian's URI scheme documents
`open`, `new`, `daily`, `unique`, `search` and `choose-vault` — and no action
for the graph view. So opening the vault is the automated part, and the graph
is the one keystroke the skill then names (`Cmd/Ctrl+G`, or the graph icon in
the left ribbon). No third-party plugin is involved, and none is required.

**Registering the vault.** Obsidian keeps its vault list in `obsidian.json`
under a per-OS config directory: `~/Library/Application Support/obsidian` on
macOS, `%APPDATA%\\obsidian` on Windows, `$XDG_CONFIG_HOME/obsidian` on Linux
(or the flatpak's own config directory, which is the only one a flatpak
install reads). `obsidian://open?path=…` resolves to the most specific vault
containing that path, so a brain that is not a vault yet has to be added to
that file first. That write is minimal and defensive: other vaults and other
settings are copied through untouched, a config that cannot be parsed is never
overwritten, and a brain already registered under someone else's id is left
exactly as it is. If Obsidian has never run there is no config to write — the
URI still launches it, and the member picks the folder in the vault chooser.

One honest caveat, stated here rather than discovered: Obsidian rewrites
`obsidian.json` from memory when it quits, so a vault registered while it is
already running may be dropped at exit. Opening again re-registers it.

Stdlib only. Every piece of the outside world — the OS name, the home
directory, the environment, what exists on disk, what is on `PATH`, reading and
writing the config, and anything that runs a command — arrives through one
`Machine`, so the whole module is testable without installing software,
launching an app, or reading the real Obsidian config.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse

import cli

#: Where a member goes when no package manager on the machine can install it.
DOWNLOAD = "https://obsidian.md"

#: The graph is a click, not a URI — this is the click.
GRAPH_KEYS = "Cmd+G on a Mac, Ctrl+G on Windows or Linux"

_APP_ID = "md.obsidian.Obsidian"


class Machine(object):
    """This computer, as the reveal sees it — and the only way out of the module.

    Which OS, where home is, the environment, what is on disk, what is on
    `PATH`, and something that runs commands. `files` and `tools` default to
    asking the real machine; a test hands in lists instead, and then nothing
    here can see past them.

    `dry` suppresses only what changes the machine — the install, the config
    write, the launch. Detection still runs, because a look that lies about
    whether Obsidian is installed is worth less than no look at all.
    """

    def __init__(self, system=None, home=None, environ=None, files=None,
                 tools=None, runner=None, dry=False):
        self.system = _system() if system is None else system
        self.home = os.path.expanduser("~") if home is None else home
        self.environ = dict(os.environ if environ is None else environ)
        self.dry = dry
        self._files = None if files is None else set(files)
        self._tools = None if tools is None else set(tools)
        self._runner = runner
        #: Every command the reveal asked for, in order, run or merely intended.
        self.commands = []

    def readonly(self):
        """The same machine with everything that changes it switched off.

        Shares the command record, so a look that ran a detection command still
        says it ran one.
        """
        twin = Machine(system=self.system, home=self.home, environ=self.environ,
                       runner=self._runner, dry=True)
        twin._files, twin._tools = self._files, self._tools
        twin.commands = self.commands
        return twin

    def exists(self, path):
        if self._files is None:
            return os.path.exists(path)
        # A fake filesystem is compared separator-blind: `os.path.join` uses the
        # separator of the machine running the test, not of the machine being
        # described, and a Windows path is a Windows path either way.
        return _flat(path) in {_flat(known) for known in self._files}

    def has(self, tool):
        """Whether `tool` can be run from `PATH`."""
        if self._tools is None:
            return bool(shutil.which(tool))
        return tool in self._tools

    def read(self, path):
        """The text of a file, or `None` when it cannot be read at all."""
        try:
            with open(path, encoding="utf-8") as handle:
                return handle.read()
        except (OSError, UnicodeDecodeError):
            return None

    def write(self, path, text):
        """Replace a file in one step, so a crash cannot truncate it.

        A dry machine changes nothing, and says so by returning False.
        """
        if self.dry:
            return False
        scratch = path + ".brain-builder.tmp"
        with open(scratch, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(scratch, path)
        return True

    def run(self, argv, changes=False):
        """Run a command; return `(exit code, output)`. Never raises.

        `changes=True` marks a command that alters the machine — those are
        recorded but not run on a dry machine.
        """
        self.commands.append(list(argv))
        if changes and self.dry:
            return 0, ""
        runner = self._runner or _run
        try:
            return runner(list(argv))
        except Exception as failure:            # a missing launcher, a killed process
            return 1, str(failure)


def _flat(path):
    return path.replace("\\", "/").rstrip("/")


def _normal(path):
    """One spelling of a folder: `~` expanded, absolute, no trailing separator."""
    return os.path.abspath(os.path.expanduser(path)).rstrip("/\\")


def _system():
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    return sys.platform


def _run(argv):
    result = subprocess.run(argv, capture_output=True, text=True)
    return result.returncode, (result.stdout or "") + (result.stderr or "")


# --- where Obsidian keeps itself -------------------------------------------

def config_dir(machine):
    """The directory holding `obsidian.json` on this machine.

    Returned whether or not it exists — the caller decides what an absent
    config means, and it means something different at every step.
    """
    if machine.system == "macos":
        return os.path.join(machine.home, "Library", "Application Support", "obsidian")
    if machine.system == "windows":
        roaming = machine.environ.get("APPDATA") or os.path.join(
            machine.home, "AppData", "Roaming")
        return os.path.join(roaming, "obsidian")
    flatpak = os.path.join(machine.home, ".var", "app", _APP_ID, "config", "obsidian")
    if machine.exists(flatpak):
        return flatpak
    base = machine.environ.get("XDG_CONFIG_HOME") or os.path.join(machine.home, ".config")
    return os.path.join(base, "obsidian")


def registry_path(machine):
    """The `obsidian.json` this machine's Obsidian reads its vault list from."""
    return os.path.join(config_dir(machine), "obsidian.json")


def installed(machine):
    """Whether Obsidian is on this machine.

    A cascade rather than a table, because each OS answers a different
    question: macOS looks for a bundle and then asks Spotlight, Windows looks
    for an exe in two roots and then asks winget, Linux asks `PATH` and then
    flatpak. Only the parts that *are* the same shape — how it installs, how it
    launches — are tables.
    """
    if machine.system == "macos":
        for folder in ("/Applications", os.path.join(machine.home, "Applications")):
            if machine.exists(os.path.join(folder, "Obsidian.app")):
                return True
        if machine.has("mdfind"):
            code, output = machine.run(
                ["mdfind", "kMDItemCFBundleIdentifier == 'md.obsidian'"])
            return code == 0 and bool(output.strip())
        return False
    if machine.system == "windows":
        roots = [machine.environ.get("LOCALAPPDATA"),
                 machine.environ.get("PROGRAMFILES"),
                 machine.environ.get("PROGRAMFILES(X86)")]
        for root in [path for path in roots if path]:
            if machine.exists(os.path.join(root, "Obsidian", "Obsidian.exe")):
                return True
        if machine.has("winget"):
            code, output = machine.run(
                ["winget", "list", "--id", "Obsidian.Obsidian", "-e"])
            return code == 0 and "obsidian" in output.lower()
        return False
    if machine.system == "linux":
        if machine.has("obsidian"):
            return True
        if machine.has("flatpak"):
            code, _ = machine.run(["flatpak", "info", _APP_ID])
            return code == 0
        return False
    return False


class Installer(object):
    """One route to installing Obsidian: the tool it needs, and what to run."""

    def __init__(self, tool, label, argv):
        self.tool = tool
        self.label = label
        self.argv = list(argv)


#: One package manager per OS. Nothing is downloaded or unpacked by hand — an
#: installer the member already has is the only route this kit will take.
_INSTALLERS = {
    "macos": Installer("brew", "Homebrew", ["brew", "install", "--cask", "obsidian"]),
    "windows": Installer("winget", "winget", [
        "winget", "install", "--id", "Obsidian.Obsidian", "-e",
        "--accept-package-agreements", "--accept-source-agreements"]),
    "linux": Installer("flatpak", "Flatpak", [
        "flatpak", "install", "-y", "flathub", _APP_ID]),
}

#: How each OS is handed a URI. `{uri}` is filled in with the encoded vault link.
_LAUNCHERS = {
    "macos": ["open", "{uri}"],
    "windows": ["cmd", "/c", "start", "", "{uri}"],
    "linux": ["xdg-open", "{uri}"],
}


def installer(machine):
    """How Obsidian would be installed here, or `None` when nothing can."""
    route = _INSTALLERS.get(machine.system)
    return route if route and machine.has(route.tool) else None


# --- the vault registry ----------------------------------------------------

def vault_id(path):
    """A stable 16-hex id for this folder, in the shape Obsidian writes.

    Derived from the path rather than random so that re-running a build cannot
    leave two entries pointing at one brain.
    """
    return hashlib.sha1(_normal(path).encode("utf-8")).hexdigest()[:16]


def register(brain, machine):
    """Add the brain to Obsidian's vault list. Returns what it did.

    `added` · `already` · `absent` (Obsidian has never run, so there is no
    config to write and inventing one is the invasive move) · `unreadable`
    (a config that will not parse is left exactly as found).
    """
    path = registry_path(machine)
    if not machine.exists(path):
        return "absent"
    try:
        payload = json.loads(machine.read(path) or "")
        if not isinstance(payload, dict):
            raise ValueError("not an object")
    except (ValueError, TypeError):
        return "unreadable"

    vaults = payload.get("vaults")
    if not isinstance(vaults, dict):
        vaults = {}
    wanted = _normal(brain)
    for entry in vaults.values():
        recorded = str(entry.get("path") or "") if isinstance(entry, dict) else ""
        if recorded and _normal(recorded) == wanted:
            return "already"

    vaults = dict(vaults)
    vaults[vault_id(brain)] = {"path": wanted, "ts": int(time.time() * 1000)}
    machine.write(path, json.dumps(dict(payload, vaults=vaults), indent=2))
    return "added"


# --- opening it ------------------------------------------------------------

def vault_uri(brain):
    """`obsidian://open?path=…` — the only documented way in, path-encoded whole."""
    return "obsidian://open?path=" + urllib.parse.quote(_normal(brain), safe="")


def open_vault(brain, machine):
    """Hand the URI to the OS. True when the launcher accepted it."""
    launcher = _LAUNCHERS.get(machine.system)
    if not launcher:
        return False
    uri = vault_uri(brain)
    code, _ = machine.run([part.format(uri=uri) for part in launcher], changes=True)
    return code == 0


# --- the whole step --------------------------------------------------------

class Reveal(object):
    """What happened when the brain was opened, and what is left for the member.

    `trouble` is the honest half: every line in it is something the member has
    to do because this step could not do it for them. It is never empty for a
    reason that was not stated.
    """

    def __init__(self, brain):
        self.brain = _normal(brain)
        self.name = os.path.basename(self.brain)
        self.installed = False
        self.installed_now = False
        self.install = ""           # the package manager used, when one was
        self.vault = "absent"       # added · already · absent · unreadable
        self.opened = False
        self.uri = vault_uri(brain)
        self.trouble = []

    def line(self):
        """One plain line. The skill says it in its own words, not verbatim."""
        if not self.opened:
            return "Obsidian did not open. " + " ".join(self.trouble)
        opened = "Opened {} in Obsidian".format(self.name)
        if self.installed_now:
            opened = "Installed Obsidian and opened {} in it".format(self.name)
        line = "{} — the graph view is one click away ({}).".format(opened, GRAPH_KEYS)
        if self.trouble:
            line += " " + " ".join(self.trouble)
        return line

    def as_dict(self):
        return {"brain": self.brain, "name": self.name,
                "installed": self.installed, "installed_now": self.installed_now,
                "install": self.install, "vault": self.vault,
                "opened": self.opened, "uri": self.uri,
                "trouble": list(self.trouble), "line": self.line()}


def reveal(brain, machine=None):
    """Install if needed, register the vault, open it. Never raises.

    Installing is not optional here and has no flag: `inspect()` is how a
    caller finds out an install is coming, so it can say so before this runs.
    """
    machine = machine or Machine()
    found = Reveal(brain)
    found.installed = installed(machine)

    if not found.installed:
        route = installer(machine)
        if route:
            found.install = route.label
            code, _ = machine.run(route.argv, changes=True)
            if code == 0:
                # An installer that exits 0 installed it. Re-detecting here
                # races the disk — a freshly written app bundle is not always
                # visible the instant the installer returns.
                found.installed = found.installed_now = True
            else:
                found.trouble.append("{} could not install it.".format(route.label))

    if not found.installed:
        found.trouble.append(
            "Obsidian is not on this machine and could not be installed here — "
            "download it from {} and open {} as a vault.".format(DOWNLOAD, found.brain))
        return found

    found.vault = register(brain, machine)
    found.opened = open_vault(brain, machine)

    if not found.opened:
        found.trouble.append(
            "The folder is at {} — open it in Obsidian with "
            "“Open folder as vault”.".format(found.brain))
    elif found.vault in ("absent", "unreadable"):
        found.trouble.append(
            "Obsidian may ask which folder to open — choose {} as a vault.".format(
                found.brain))
    return found


def inspect(brain, machine=None):
    """What the machine looks like, changing none of it — the `--check` answer.

    This is what makes "say it before you install it" possible: it names the
    package manager an install would use, without using it.
    """
    quiet = (machine or Machine()).readonly()
    route = installer(quiet)
    status = register(brain, quiet)
    return {"brain": _normal(brain), "system": quiet.system,
            "installed": installed(quiet),
            "installer": route.label if route else None,
            "config": registry_path(quiet), "uri": vault_uri(brain),
            "vault": {"already": "registered",
                      "added": "unregistered"}.get(status, status)}


# --- cli -------------------------------------------------------------------

USAGE = ("usage: open_in_obsidian.py <brain> [--json] [--home DIR]\n"
         "       open_in_obsidian.py <brain> --check [--json] [--home DIR]\n")


def main(argv):
    try:
        positional, options = cli.scan(
            argv, options={"--check": False, "--json": False, "--home": None},
            flags=("--check", "--json"))
    except cli.UsageError as failure:
        sys.stderr.write("open_in_obsidian.py: {}\n{}".format(failure, USAGE))
        return 2

    if len(positional) != 1:
        sys.stderr.write(USAGE)
        return 2
    brain = os.path.expanduser(positional[0])
    if not os.path.isdir(brain):
        sys.stderr.write("open_in_obsidian.py: no brain at {}\n{}".format(brain, USAGE))
        return 2

    home = options["--home"]
    machine = Machine(home=os.path.expanduser(home) if home else None)

    if options["--check"]:
        print(json.dumps(inspect(brain, machine), indent=2))
        return 0

    found = reveal(brain, machine)
    print(json.dumps(found.as_dict(), indent=2) if options["--json"] else found.line())
    # A garnish never reports a broken build — but it does not claim a success it
    # did not have either. The skill turns a 1 here into one calm line.
    return 0 if found.opened else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
