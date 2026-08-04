"""The frontmatter subset a brain is allowed to use.

Deliberately a subset, not YAML: scalars, one level of nesting, `- item` lists,
and `>`/`|` block scalars. What matters is that everything inside the subset
round-trips — a field that parses to nothing is worse than a field that errors.
"""
import unittest

from brain_contract import parse_frontmatter


def front(text):
    frontmatter, _, _ = parse_frontmatter(text)
    return frontmatter


class Scalars(unittest.TestCase):

    def test_a_document_without_frontmatter_is_left_alone(self):
        mapping, body, present = parse_frontmatter("# Page\n\nProse.\n")
        self.assertFalse(present)
        self.assertEqual({}, mapping)
        self.assertEqual("# Page\n\nProse.\n", body)

    def test_frontmatter_is_split_off_the_body(self):
        mapping, body, present = parse_frontmatter("---\ntype: concept\n---\n\n# Page\n")
        self.assertTrue(present)
        self.assertEqual({"type": "concept"}, mapping)
        self.assertEqual("\n# Page\n", body)

    def test_empty_frontmatter_is_present_but_empty(self):
        mapping, _, present = parse_frontmatter("---\n---\n\n# Page\n")
        self.assertTrue(present, "an empty block is still a block, not a missing one")
        self.assertEqual({}, mapping)

    def test_quotes_are_stripped_and_colons_in_values_survive(self):
        self.assertEqual(
            {"title": "Pricing: the short version", "canonical": "https://example.com/x"},
            front('---\ntitle: "Pricing: the short version"\n'
                  "canonical: https://example.com/x\n---\n"))

    def test_comments_and_blank_lines_are_ignored(self):
        self.assertEqual({"type": "concept"},
                         front("---\n# a comment\n\ntype: concept\n---\n"))


class Lists(unittest.TestCase):
    """The multi-line form is what authors actually write — it must not vanish."""

    def test_an_indented_list(self):
        self.assertEqual({"sources": ["one", "two"]},
                         front("---\nsources:\n  - one\n  - two\n---\n"))

    def test_a_flush_list(self):
        self.assertEqual({"sources": ["one", "two"]},
                         front("---\nsources:\n- one\n- two\n---\n"))

    def test_an_inline_list(self):
        self.assertEqual({"overlays": ["persona", "standing"]},
                         front("---\noverlays: [persona, standing]\n---\n"))

    def test_an_empty_inline_list(self):
        self.assertEqual({"overlays": []}, front("---\noverlays: []\n---\n"))

    def test_a_list_does_not_swallow_the_field_after_it(self):
        self.assertEqual({"sources": ["one"], "type": "concept"},
                         front("---\nsources:\n  - one\ntype: concept\n---\n"))


class NestingAndBlocks(unittest.TestCase):

    def test_a_nested_mapping(self):
        self.assertEqual({"metadata": {"type": "brain-router", "kind": "subject"}},
                         front("---\nmetadata:\n  type: brain-router\n  kind: subject\n---\n"))

    def test_a_nested_mapping_does_not_swallow_the_field_after_it(self):
        self.assertEqual({"metadata": {"kind": "subject"}, "name": "kb"},
                         front("---\nmetadata:\n  kind: subject\nname: kb\n---\n"))

    def test_a_key_with_nothing_under_it_is_empty_not_a_phantom_mapping(self):
        self.assertEqual({"stance": "", "type": "concept"},
                         front("---\nstance:\ntype: concept\n---\n"))

    def test_a_folded_block_scalar(self):
        self.assertEqual(
            {"description": "One long line split across two.", "type": "concept"},
            front("---\ndescription: >\n  One long line\n  split across two.\n"
                  "type: concept\n---\n"))


if __name__ == "__main__":
    unittest.main()
