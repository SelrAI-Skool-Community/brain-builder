# SETUP-PROMPT.md

**You are Claude (or any coding agent), and you are installing Brain Builder on
this machine.** The member has just cloned this repo and pointed you here. Do
every step yourself. If a step fails, fix it and retry — never hand a terminal
command back to the member, and never stop to ask a question you can answer by
looking.

Everything below runs from the root of the clone. Nothing here needs the
network, an API key, or a `pip install`.

---

## What you are installing

Three things, and only the first two are files you move:

1. **`brain-builder`** — the builder skill. Runs the whole build: intake, source
   list, plan gate, ingest, wiki, router, attach, demo.
2. **`brain-toggle`** — the attach/detach skill. Connects built brains to the
   harnesses on this machine.
3. **Blueprints** — `subject`, `persona`, `business`. They ship *inside*
   `brain-builder` (`skills/brain-builder/blueprints/`) and need no install step
   of their own.

A **brain** is a separate thing from these skills: a standalone folder of
markdown, built later, living at `~/brains/<slug>/` by default. Installing the
kit builds no brains. That is the member's first build, not part of setup.

---

## Step 1 — Check the interpreter

```bash
python3 -V
```

Python 3.7 or newer. The scripts are stdlib-only and deliberately avoid
f-strings, dataclasses and typing imports, so they run on old interpreters as
well as new ones. If `python3` is missing, install it and carry on.

---

## Step 2 — Find the skills directory

Do not guess the path. Ask the toggle script, which is the same resolver the
skill itself uses:

```bash
python3 skills/brain-toggle/scripts/toggle.py resolve
```

It prints one absolute path and writes nothing — on Claude Code,
`~/.claude/skills`. For Codex, add `--harness codex` and you get
`~/.codex/skills` instead.

**Install into every harness the member actually uses.** If they use both Claude
Code and Codex, run steps 2 and 3 once per harness. The two are independent;
neither loads the other's directory.

---

## Step 3 — Link both skills in

Symlink rather than copy, so a `git pull` in the clone updates the installed
skills with no reinstall step:

```bash
SKILLS_DIR="$(python3 skills/brain-toggle/scripts/toggle.py resolve)"
mkdir -p "$SKILLS_DIR"
for skill in brain-builder brain-toggle; do
  link="$SKILLS_DIR/$skill"
  if [ -e "$link" ] && [ ! -L "$link" ]; then
    echo "$link exists and is not a symlink — move it aside yourself" >&2
    exit 1
  fi
  ln -sfn "$PWD/skills/$skill" "$link"
done
```

**The guard is not decoration.** `ln -sfn` pointed at a path where a real
directory already sits does not replace it and does not fail — it quietly
creates the link *inside* it, at `$SKILLS_DIR/brain-builder/brain-builder`. The
skill is then dead and `ls -l` looks fine. The same refusal is built into
`toggle.py` for brains; this loop is that refusal for the two skills.

Two consequences to state to the member in one line each, because both surprise
people later:

- **The clone has to stay where it is.** Moving or deleting it breaks both
  links. If they want it somewhere tidier, move it *first*, then re-run step 3.
- **No restart.** Skills are read per session; a new session picks them up.

Confirm the links landed:

```bash
ls -l "$SKILLS_DIR/brain-builder" "$SKILLS_DIR/brain-toggle"
```

`brain-toggle` is what `attach` uses on brains later, but it does **not** attach
these two skills — `attach` takes a *brain* folder (`SKILL.md` + `index.md` +
`wiki/`) and refuses anything else. Installing the kit is the two symlinks
above; `attach` is for what the kit builds.

---

## Step 4 — Verify, without touching the real profile

Prove the machinery runs before telling the member it is ready. The repo ships
fixture brains for exactly this, and `toggle.py` takes `--home DIR` so the whole
rehearsal happens in a throwaway directory:

```bash
TMP="$(mktemp -d)"
cp -R tests/fixtures/sourdough-baking "$TMP/sourdough-baking"

# the contract check: skeleton, frontmatter, links, router
python3 skills/brain-builder/scripts/lint.py "$TMP/sourdough-baking"

# regenerate the router — it records the brain's root, so run it before attaching
python3 skills/brain-builder/scripts/gen_router.py "$TMP/sourdough-baking"

# attach / list / detach against a fake home, so ~/.claude is never written to
python3 skills/brain-toggle/scripts/toggle.py attach "$TMP/sourdough-baking" --home "$TMP/home"
python3 skills/brain-toggle/scripts/toggle.py list --home "$TMP/home"
python3 skills/brain-toggle/scripts/toggle.py detach sourdough-baking --home "$TMP/home"

rm -rf "$TMP"
```

What a healthy run looks like:

- `lint.py` prints one line ending `valid brain — 0 error(s), 0 warning(s)` and
  exits 0. Errors exit 1; warnings never do.
- `gen_router.py` prints the absolute path of the `SKILL.md` it wrote. Run twice
  in the same place it is a no-op diff; run on a brain that has *moved* it
  re-records the new root, which is why it comes before `attach` here. (Attach a
  brain whose router still records an old root and you get a `warning:` line
  naming the fix — that is the mechanism working, not a fault.)
- `attach` prints `target: …` then `attached … -> …`; `list` shows the brain
  under the fake home; `detach` prints `detached …`.

Then run the test suite, which is the same check with more corners covered:

```bash
python3 -m unittest discover tests
```

It is stdlib-only, needs no network, and takes seconds. If it is green, the
install is good.

---

## Step 5 — Optional dependencies, and only when an arm needs one

**Install nothing in this step by default.** Every one of these is needed only
by the single ingestion arm that reads that format, and a brain built from local
markdown needs none of them.

| Arm | Reads | Needs | Install line the script itself prints |
|---|---|---|---|
| `ingest_local.py` | md, txt, csv, json, docx | nothing | — |
| `ingest_youtube.py` | YouTube channels, playlists, searches | `yt-dlp` | `pip install yt-dlp` |
| `ingest_docs.py` | PDF | `pymupdf4llm` | `pip install pymupdf4llm` |
| `ingest_docs.py` | EPUB | `EbookLib` | `pip install EbookLib` |
| `ingest_web.py` | web articles | `trafilatura` | `pip install trafilatura` |
| `ingest_podcast.py` | Apple Podcasts, any RSS | nothing to read feeds | — |

`docx` is read with `zipfile` and `ElementTree`, so the local arm genuinely has
no dependency. The podcast arm resolves and reads feeds on stdlib alone; it only
reaches for a key when an episode ships no transcript and the member has
approved transcription.

### The transcription key

```bash
export ELEVENLABS_API_KEY=...     # optional
```

Needed only when an arm falls back to transcribing audio — a YouTube video with
no captions, a podcast episode with no published transcript — and only after the
member has approved the cost at the plan gate. ElevenLabs Scribe v2 is the
default engine at $0.22/hour. The key is read from the environment, is never
written to disk, and never reaches a `raw/` page. `GROQ_API_KEY` is the
alternative for the cheap rough-indexing engine; do not offer it unless the
member raises cost.

Without the key, nothing else in the build is affected — only the sources that
needed transcribing fail, by name.

### What a missing dependency actually does

A missing library or key is **recorded against the source that needed it and the
build carries on**. It is never an exception, never a silent skip:

```
failed  https://youtube.com/watch?v=…  No module named 'yt_dlp' — pip install yt-dlp
failed  "Some Episode"  transcription failed: no ELEVENLABS_API_KEY in the
        environment — ElevenLabs Scribe needs a key to transcribe. Set it and
        re-run this arm; nothing else in the build depends on it.
```

Every such record is also appended to the brain's `log.md`, so the failure is
still there after the session ends.

**The one case that stops:** if an arm was given sources and *none* of them
produced any text, it exits 1 with a line like `ingest_web.py: no article could
be read — stop and talk to the member rather than building an empty brain`. That
is deliberate. An arm that lost the whole corpus should stop, not build an empty
brain. Fix the cause — usually the one `pip install` named on the records — and
re-run the arm. Re-running adds material rather than overwriting it; `raw/` is
immutable and YouTube keeps a download archive, so nothing is re-fetched.

---

## Step 6 — Tell the member it is ready

Report in a few lines, no more — and **in plain words**. Everything above this
step is your vocabulary, not theirs: symlink, harness, fixture, lint and router
are all words to translate before they reach the member, or to explain in-line
where the detail genuinely matters. Do not hide anything; just do not assume they
know the term.

- Both skills installed, and where they now work. If they only use Claude Code,
  that is *"installed for Claude Code — a new session will have it, no restart"*
  and nothing about tools plural. Say "and Codex too" only if you installed there
  as well, and explain the pair once when you do.
- **Say the clone has to stay put, and why**, in the same breath: *"the skills
  are linked to this folder rather than copied, so a `git pull` updates them —
  but move the folder and the links break."*
- The checks passed — *"I ran it against a sample brain end to end and the full
  test suite: all green"*, not "fixture linted clean, router regenerated".
- One example of how to start, in their words rather than a command:

  > Say *"build me a brain on X from the files in ~/Documents/Y"* — or paste one
  > of the worked prompts in `demos/`.

- If, and only if, they have already said what they want to build from: name the
  one `pip install` that build will need.

Do **not** list the optional dependencies at them, do not explain the rights
stance unprompted, and do not offer to build something. Setup is finished; the
first build is a separate conversation they start.

---

## If something goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| The skill does not fire in a new session | linked into the wrong harness | re-run step 2 with `--harness`, then step 3 |
| `… is not a brain — missing SKILL.md, wiki` | `attach` was pointed at a skill or a plain folder | `attach` takes brains; the kit installs by symlink (step 3) |
| `… exists and is not a symlink` | a real directory sits at the link path — from step 3's guard, or from `attach` | move it aside by hand; neither will delete it for you |
| `warning: the router records brain_root …` | the brain folder was moved after it was built | run the `gen_router.py … --root …` command the warning prints |
| Suite fails | a broken clone, or a stale interpreter | re-clone; check `python3 -V` is 3.7+ |

Fix it and retry. Only escalate to the member if the machine itself is the
problem — no Python, no write access to their home directory.
