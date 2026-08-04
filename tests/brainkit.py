"""Shared test helpers: path wiring and a builder for throwaway brains on disk."""
import os
import re
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "skills", "brain-builder", "scripts")
FIXTURES_DIR = os.path.join(REPO_ROOT, "tests", "fixtures")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def flatten(text):
    """Lowercase with whitespace runs collapsed — assert on wording, not wrapping."""
    return re.sub(r"\s+", " ", text).lower()


def page(body="Body.\n", **frontmatter):
    """A markdown page: frontmatter keys in order given, then the body."""
    lines = ["---"]
    for key, value in frontmatter.items():
        lines.append("{}: {}".format(key.rstrip("_"), value))
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + body


class BrainOnDisk(unittest.TestCase):
    """Base case that builds throwaway brains in a temp dir."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="brain-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write(self, brain, relpath, text):
        path = os.path.join(brain, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def minimal_brain(self, slug="test-brain", **index_frontmatter):
        """A brain that satisfies every mandatory rule, ready to be broken."""
        brain = os.path.join(self.tmp, slug)
        os.makedirs(os.path.join(brain, "wiki"), exist_ok=True)
        os.makedirs(os.path.join(brain, "raw"), exist_ok=True)
        front = dict(
            type="index",
            slug=slug,
            title="Test Brain",
            domain="A brain used by the test suite.",
            kind="subject",
            stance="advisor",
        )
        front.update(index_frontmatter)
        self.write(brain, "index.md", page(
            "# Test Brain\n\n- [Concept](wiki/concept.md) — the one concept, 3 of them.\n"
            "\n## Known gaps\n\n- Everything else.\n",
            **front))
        self.write(brain, "wiki/concept.md", page(
            "# Concept\n\nThe concept.\n", type="concept", title="Concept"))
        self.write(brain, "SKILL.md", "---\nname: {}\ndescription: A test brain.\n---\n\n# Router\n".format(slug))
        self.write(brain, "log.md", page("# Log\n\n- Built.\n", type="log"))
        self.write(brain, "CHANGELOG.md", "# Changelog\n\n## 2026-01-01\n- Built.\n")
        self.write(brain, "raw/source.md", "Unfenced raw text with no frontmatter at all.\n")
        return brain
