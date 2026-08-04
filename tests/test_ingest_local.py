"""The local-files ingest arm: a folder of files becomes an attributed `raw/`.

This is the v1 ingestion arm (spec.md §6 — md/txt/csv/json/docx). The rules it
has to hold: every chunk carries its source and ingest date, nothing silently
disappears, and one bad file never stops a build.
"""
import contextlib
import io
import json
import os
import unittest
import zipfile

from brainkit import BrainOnDisk

from brain_contract import parse_frontmatter
from ingest_local import ingest
from scaffold import scaffold_brain

DOCX_XML = ("<?xml version='1.0'?>"
            "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
            "<w:body>{}</w:body></w:document>")


class IngestOnDisk(BrainOnDisk):
    """A brain and a source folder, both throwaway."""

    def setUp(self):
        super(IngestOnDisk, self).setUp()
        self.brain = scaffold_brain(title="Test Brain", at=self.tmp)
        self.sources = os.path.join(self.tmp, "sources")
        os.makedirs(self.sources)

    def source(self, name, text):
        path = os.path.join(self.sources, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def docx(self, name, paragraphs):
        path = os.path.join(self.sources, name)
        body = "".join("<w:p><w:r><w:t>{}</w:t></w:r></w:p>".format(p) for p in paragraphs)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", DOCX_XML.format(body))
        return path

    def raw_pages(self):
        raw = os.path.join(self.brain, "raw")
        return sorted(name for name in os.listdir(raw) if name.endswith(".md"))

    def raw_text(self, name):
        with open(os.path.join(self.brain, "raw", name), encoding="utf-8") as handle:
            return handle.read()


class TextFiles(IngestOnDisk):

    def test_markdown_and_text_files_land_in_raw_one_page_each(self):
        self.source("notes.md", "# Notes\n\nHydration runs at 70 %.\n")
        self.source("interview.txt", "He said the starter peaks in six hours.\n")

        manifest = ingest([self.sources], self.brain)

        self.assertEqual(2, len(manifest.ok))
        self.assertEqual(2, len(self.raw_pages()))
        self.assertIn("Hydration runs at 70 %.", "".join(
            self.raw_text(name) for name in self.raw_pages()))

    def test_every_page_carries_its_source_path_and_ingest_date(self):
        """The rights stance: every chunk is attributed, always."""
        path = self.source("notes.md", "Some material.\n")

        ingest([self.sources], self.brain)

        front, body, present = parse_frontmatter(self.raw_text(self.raw_pages()[0]))
        self.assertTrue(present)
        self.assertEqual(path, front["source"])
        self.assertEqual("md", front["source_format"])
        self.assertRegex(front["ingested"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("Some material.", body)

    def test_a_single_file_can_be_ingested_as_well_as_a_folder(self):
        path = self.source("notes.md", "Some material.\n")
        manifest = ingest([path], self.brain)
        self.assertEqual(1, len(manifest.ok))

    def test_nested_folders_are_walked_and_names_stay_unique(self):
        self.source("a/notes.md", "First set of notes.\n")
        self.source("b/notes.md", "Second set of notes.\n")

        manifest = ingest([self.sources], self.brain)

        self.assertEqual(2, len(manifest.ok))
        self.assertEqual(2, len(set(self.raw_pages())))


class StructuredFiles(IngestOnDisk):
    """csv/json/docx keep the structure that makes them readable (spec.md §6)."""

    def test_a_csv_keeps_its_columns_rather_than_becoming_a_run_on_line(self):
        self.source("prices.csv", "product,price,margin\nStarter kit,49,0.62\n"
                                  "Masterclass,249,0.81\n")

        ingest([self.sources], self.brain)

        text = self.raw_text("prices.md")
        self.assertIn("| product | price | margin |", text)
        self.assertIn("| Masterclass | 249 | 0.81 |", text)

    def test_a_ragged_csv_row_is_padded_rather_than_dropped(self):
        self.source("prices.csv", "product,price,margin\nStarter kit,49\n")
        ingest([self.sources], self.brain)
        self.assertIn("| Starter kit | 49 |  |", self.raw_text("prices.md"))

    def test_json_keeps_its_structure_and_is_fenced_off_from_the_markdown(self):
        self.source("plans.json", json.dumps({"tiers": [{"name": "Pro", "price": 99}]}))

        ingest([self.sources], self.brain)

        text = self.raw_text("plans.md")
        self.assertIn("```json", text)
        self.assertIn('"price": 99', text)

    def test_a_docx_gives_up_its_paragraphs(self):
        self.docx("brief.docx", ["The margin target is 62 %.", "Second paragraph."])

        manifest = ingest([self.sources], self.brain)

        self.assertEqual(1, len(manifest.ok))
        text = self.raw_text("brief.md")
        self.assertIn("The margin target is 62 %.", text)
        self.assertIn("Second paragraph.", text)

    def test_word_counts_are_recorded_so_the_plan_gate_can_state_a_size(self):
        self.source("notes.md", "one two three four five\n")
        self.assertEqual(5, ingest([self.sources], self.brain).ok[0].words)


class FailuresNeverHalt(IngestOnDisk):
    """A dead source is a line in the log, not the end of the run (spec.md §5)."""

    def test_an_unreadable_file_is_recorded_and_the_rest_still_lands(self):
        self.docx("locked.docx", [])                 # a zip with no document.xml
        with zipfile.ZipFile(os.path.join(self.sources, "locked.docx"), "w") as archive:
            archive.writestr("EncryptedPackage", b"\x00\x01")
        self.source("notes.md", "Material that must survive the failure.\n")

        manifest = ingest([self.sources], self.brain)

        self.assertEqual(1, len(manifest.ok))
        self.assertEqual(1, len(manifest.failed))
        self.assertIn("locked.docx", manifest.failed[0].source)
        self.assertFalse(manifest.whole_corpus_failed)

    def test_a_file_the_kit_cannot_open_says_so_rather_than_guessing(self):
        """Rights stance: DRM is refused, never worked around."""
        with zipfile.ZipFile(os.path.join(self.sources, "drm.docx"), "w") as archive:
            archive.writestr("EncryptedPackage", b"\x00")
        manifest = ingest([self.sources], self.brain)
        self.assertIn("DRM", manifest.failed[0].reason)

    def test_an_empty_source_is_counted_separately_from_a_broken_one(self):
        self.source("blank.txt", "   \n\n")
        manifest = ingest([self.sources], self.brain)
        self.assertEqual(1, len(manifest.empty))
        self.assertEqual([], manifest.failed)
        self.assertEqual([], self.raw_pages())

    def test_the_same_text_twice_is_ingested_once(self):
        """Compilations repeat other sources near-verbatim (spec.md §6 dedup)."""
        self.source("notes.md", "Identical material.\n")
        self.source("copy-of-notes.md", "Identical  material.\n")

        manifest = ingest([self.sources], self.brain)

        self.assertEqual(1, len(manifest.ok))
        self.assertEqual(1, len(manifest.duplicate))
        self.assertEqual(1, len(self.raw_pages()))

    def test_file_types_this_arm_does_not_read_are_left_for_the_later_arms(self):
        self.source("paper.pdf", "%PDF-1.4 not really\n")
        self.source("notes.md", "Material.\n")

        manifest = ingest([self.sources], self.brain)

        self.assertEqual(1, len(manifest.unsupported))
        self.assertEqual(1, len(manifest.ok))
        self.assertFalse(manifest.whole_corpus_failed)

    def test_a_corpus_where_nothing_worked_is_the_one_stop_condition(self):
        self.source("blank.txt", "\n")
        with zipfile.ZipFile(os.path.join(self.sources, "drm.docx"), "w") as archive:
            archive.writestr("EncryptedPackage", b"\x00")

        self.assertTrue(ingest([self.sources], self.brain).whole_corpus_failed)

    def test_a_folder_of_only_unsupported_files_is_not_a_failed_corpus(self):
        """Nothing was ever a candidate — that is a conversation, not a crash."""
        self.source("paper.pdf", "%PDF\n")
        self.assertFalse(ingest([self.sources], self.brain).whole_corpus_failed)

    def test_failures_are_written_to_the_brains_log(self):
        self.source("blank.txt", "\n")
        self.source("notes.md", "Material.\n")

        ingest([self.sources], self.brain)

        with open(os.path.join(self.brain, "log.md"), encoding="utf-8") as handle:
            log = handle.read()
        self.assertIn("ingest:", log)
        self.assertIn("blank.txt", log)

    def test_the_summary_line_carries_the_counts_the_build_narrates(self):
        self.source("notes.md", "Material.\n")
        self.source("blank.txt", "\n")

        summary = ingest([self.sources], self.brain).summary()

        self.assertIn("1 sources ingested", summary)
        self.assertIn("1 empty", summary)


class CommandLine(IngestOnDisk):
    """`python3 ingest_local.py <paths> --into <brain>`."""

    def run_cli(self, *args):
        import ingest_local
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            return ingest_local.main(["ingest_local.py"] + list(args)), out.getvalue()

    def test_it_reports_the_summary_and_exits_zero(self):
        self.source("notes.md", "Material.\n")
        code, out = self.run_cli(self.sources, "--into", self.brain)
        self.assertEqual(0, code)
        self.assertIn("1 sources ingested", out)

    def test_json_output_gives_the_build_the_counts_to_narrate(self):
        self.source("notes.md", "Material.\n")
        code, out = self.run_cli(self.sources, "--into", self.brain, "--json")
        self.assertEqual(0, code)
        self.assertEqual(1, json.loads(out)["counts"]["ok"])

    def test_a_wholly_failed_corpus_exits_one(self):
        self.source("blank.txt", "\n")
        self.assertEqual(1, self.run_cli(self.sources, "--into", self.brain)[0])

    def test_missing_arguments_exit_two(self):
        self.assertEqual(2, self.run_cli(self.sources)[0])
        self.assertEqual(2, self.run_cli("--into", self.brain)[0])


if __name__ == "__main__":
    unittest.main()
