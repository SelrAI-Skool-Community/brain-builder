"""The PDF/EPUB arm: books and papers become attributed `raw/` pages.

PyMuPDF4LLM and EbookLib do the reading (spec.md §6) and are imported inside the
arm, so this suite runs on a machine with neither. What is held here is the part
that is the kit's own: which files it refuses on rights grounds, what a scanned
PDF with no text layer becomes, and what a missing library says.
"""
import contextlib
import io
import json
import os
import unittest
import zipfile

from brainkit import BrainOnDisk

import ingest_docs
from brain_contract import parse_frontmatter
from scaffold import scaffold_brain

BOOK = "Hydration is the ratio of water to flour by weight. " * 20


class DocsArm(BrainOnDisk):
    """A brain, a source folder, and readers that never touch a real parser."""

    def setUp(self):
        super(DocsArm, self).setUp()
        self.brain = scaffold_brain(title="Test Brain", at=self.tmp)
        self.sources = os.path.join(self.tmp, "sources")
        os.makedirs(self.sources)
        self.texts = {}

    def source(self, name, text=BOOK, payload=b"%PDF-1.7\n"):
        path = os.path.join(self.sources, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(payload)
        self.texts[path] = text
        return path

    def reader(self, path):
        return self.texts.get(path, ""), {"title": "The Book", "author": "A Baker"}

    def ingest(self, *paths, **kwargs):
        kwargs.setdefault("readers", {"pdf": self.reader, "epub": self.reader})
        return ingest_docs.ingest(list(paths) or [self.sources], self.brain, **kwargs)

    def raw_pages(self):
        return sorted(name for name in os.listdir(os.path.join(self.brain, "raw"))
                      if name.endswith(".md"))

    def raw_text(self, name):
        with open(os.path.join(self.brain, "raw", name), encoding="utf-8") as handle:
            return handle.read()


class Documents(DocsArm):
    """The happy path for both readers."""

    def test_a_pdf_and_an_epub_each_land_as_one_page(self):
        self.source("paper.pdf")
        self.source("book.epub", text=BOOK + " And a second book.")
        manifest = self.ingest()
        self.assertEqual(2, len(manifest.ok))
        self.assertEqual(2, len(self.raw_pages()))

    def test_the_page_carries_its_path_format_title_and_author(self):
        path = self.source("paper.pdf")
        self.ingest()
        front, body, _ = parse_frontmatter(self.raw_text(self.raw_pages()[0]))
        self.assertEqual(path, front["source"])
        self.assertEqual("pdf", front["source_format"])
        self.assertEqual("The Book", front["title"])
        self.assertEqual("A Baker", front["author"])
        self.assertIn("Hydration is the ratio", body)

    def test_a_folder_of_documents_is_walked(self):
        self.source("papers/one.pdf")
        self.source("papers/two.pdf", text=BOOK + " Second paper.")
        self.assertEqual(2, len(self.ingest().ok))

    def test_the_same_book_twice_lands_once(self):
        self.source("book.epub")
        self.source("copies/book-again.epub")
        manifest = self.ingest()
        self.assertEqual(1, len(manifest.ok))
        self.assertEqual(1, len(manifest.duplicate))

    def test_a_file_type_this_arm_cannot_read_is_unsupported_not_failed(self):
        self.source("notes.md")
        manifest = self.ingest()
        self.assertEqual(1, len(manifest.unsupported))
        self.assertIn("ingest_local", manifest.unsupported[0].reason)


class ScannedAndBroken(DocsArm):
    """A PDF with no text layer is a real and common case, and must be loud."""

    def test_a_scanned_pdf_is_empty_and_says_ocr_is_not_shipped(self):
        self.source("scan.pdf", text="   ")
        manifest = self.ingest()
        self.assertEqual(1, len(manifest.empty))
        self.assertIn("ocr", manifest.empty[0].reason.lower())
        self.assertTrue(manifest.whole_corpus_failed)

    def test_a_reader_that_blows_up_is_a_record_not_an_exception(self):
        def reader(path):
            raise ValueError("corrupt xref table")

        self.source("broken.pdf")
        manifest = self.ingest(readers={"pdf": reader})
        self.assertEqual(1, len(manifest.failed))
        self.assertIn("corrupt xref", manifest.failed[0].reason)

    def test_a_missing_library_names_the_line_that_fixes_it(self):
        def reader(path):
            raise ImportError("No module named 'pymupdf4llm'")

        self.source("paper.pdf")
        manifest = self.ingest(readers={"pdf": reader})
        self.assertIn("pip install pymupdf4llm", manifest.failed[0].reason)


class Rights(DocsArm):
    """No DRM removal, ever — the file is refused unopened."""

    def test_kindle_and_audible_files_are_refused_before_any_reader_runs(self):
        self.source("book.azw3")
        manifest = self.ingest()
        self.assertEqual(1, len(manifest.failed))
        self.assertIn("DRM", manifest.failed[0].reason)

    def test_an_encrypted_epub_is_refused(self):
        path = os.path.join(self.sources, "locked.epub")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("META-INF/encryption.xml", "<encryption/>")
        manifest = self.ingest()
        self.assertEqual(1, len(manifest.failed))
        self.assertIn("DRM", manifest.failed[0].reason)

    def test_a_refused_file_is_named_in_the_log(self):
        self.source("book.azw3")
        self.ingest()
        with open(os.path.join(self.brain, "log.md"), encoding="utf-8") as handle:
            self.assertIn("book.azw3", handle.read())


class EpubText(unittest.TestCase):
    """An EPUB chapter is XHTML; the brain wants the prose out of it."""

    def test_tags_go_and_the_text_stays(self):
        text = ingest_docs.html_to_text(
            "<html><body><h1>Chapter 1</h1><p>Hydration decides the crumb.</p>"
            "<script>x=1</script></body></html>")
        self.assertIn("Chapter 1", text)
        self.assertIn("Hydration decides the crumb.", text)
        self.assertNotIn("x=1", text)

    def test_block_elements_keep_their_paragraph_breaks(self):
        text = ingest_docs.html_to_text("<p>First.</p><p>Second.</p>")
        self.assertIn("First.\n\nSecond.", text)

    def test_entities_are_decoded(self):
        self.assertIn("Baker's & Co", ingest_docs.html_to_text("<p>Baker&#39;s &amp; Co</p>"))


class CommandLine(DocsArm):
    """`python3 ingest_docs.py <path> --into <brain>`."""

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            return ingest_docs.main(["ingest_docs.py"] + list(args)), out.getvalue()

    def test_a_corpus_of_refused_files_exits_one(self):
        self.source("book.azw3")
        code, out = self.run_cli(self.sources, "--into", self.brain)
        self.assertEqual(1, code)
        self.assertIn("0 sources ingested", out)

    def test_json_output_gives_the_build_the_counts(self):
        self.source("book.azw3")
        code, out = self.run_cli(self.sources, "--into", self.brain, "--json")
        self.assertEqual(1, json.loads(out)["counts"]["failed"])

    def test_missing_arguments_exit_two(self):
        self.assertEqual(2, self.run_cli(self.sources)[0])
        self.assertEqual(2, self.run_cli("--into", self.brain)[0])


if __name__ == "__main__":
    unittest.main()
