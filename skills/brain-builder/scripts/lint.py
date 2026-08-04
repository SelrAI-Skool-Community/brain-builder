#!/usr/bin/env python3
"""Lint a folder against the brain contract (spec.md §2).

    python3 lint.py <brain-dir>

Exit 0 when the folder is a valid brain, 1 when it is not. Warnings never
change the exit code — they mark the parts of the skeleton a brain is allowed
to ship without (`raw/`, `log.md`, `CHANGELOG.md`).

What is checked:

  skeleton     `SKILL.md` + `index.md` + `wiki/` mandatory; `raw/`, `log.md`,
               `CHANGELOG.md` warn; `index.md` carries `## Known gaps`;
               folders the contract has never heard of are ignored, not errors.
  frontmatter  OKF conformance — every routed page carries frontmatter with a
               `type`; the reserved names `index.md` and `log.md` carry their
               reserved type and are not reused inside `wiki/`. Overlay pages
               (`persona/`, `standing/`) are loaded whole rather than routed, so
               the page rules do not bind them.
  freshness    `as_of` / `volatility` / `canonical` are optional, and validated
               only where present.
  links        every relative markdown link resolves, and stays inside the brain.

Stdlib only.
"""
import os
import sys

from brain_contract import (
    MANDATORY_DIRS,
    MANDATORY_FILES,
    OPTIONAL_DIRS,
    OPTIONAL_FILES,
    RESERVED_TYPES,
    VOLATILITY_VALUES,
    contract_pages,
    is_iso_date,
    read_page,
)

KNOWN_GAPS_HEADING = "## Known gaps"


class Report(object):
    """What the lint found: failures, and things it merely wants to mention."""

    def __init__(self, root):
        self.root = root
        self.errors = []
        self.warnings = []

    @property
    def ok(self):
        return not self.errors

    def error(self, message):
        self.errors.append(message)

    def warn(self, message):
        self.warnings.append(message)

    def render(self):
        lines = ["ERROR  " + message for message in self.errors]
        lines += ["WARN   " + message for message in self.warnings]
        lines.append("{}: {} — {} error(s), {} warning(s)".format(
            self.root, "valid brain" if self.ok else "not a valid brain",
            len(self.errors), len(self.warnings)))
        return "\n".join(lines)


def lint_brain(root):
    """Check `root` against the brain contract and return a `Report`."""
    root = os.path.abspath(os.path.expanduser(root))
    report = Report(root)
    if not os.path.isdir(root):
        report.error("{}: not a directory".format(root))
        return report

    _check_skeleton(root, report)
    if report.errors:
        return report

    _check_router(root, report)
    _check_index(root, report)

    pages = contract_pages(root)
    for page in pages:
        _check_frontmatter(page, report)
        _check_freshness(page, report)
        _check_links(root, page, report)
    return report


def _check_skeleton(root, report):
    for name in MANDATORY_FILES:
        if not os.path.isfile(os.path.join(root, name)):
            report.error("{} is missing — every brain needs one".format(name))
    for name in MANDATORY_DIRS:
        if not os.path.isdir(os.path.join(root, name)):
            report.error("{}/ is missing — every brain needs one".format(name))
    for name in OPTIONAL_FILES:
        if not os.path.isfile(os.path.join(root, name)):
            report.warn("{} is missing".format(name))
    for name in OPTIONAL_DIRS:
        if not os.path.isdir(os.path.join(root, name)):
            report.warn("{}/ is missing — provenance and re-distillation lose their source".format(name))


def _check_router(root, report):
    router = read_page(root, "SKILL.md")
    if not router.has_frontmatter:
        report.error("SKILL.md has no frontmatter — regenerate it with gen_router.py")
        return
    for field in ("name", "description"):
        if not router.frontmatter.get(field):
            report.error("SKILL.md frontmatter has no {} — the router cannot fire "
                         "without one; regenerate it with gen_router.py".format(field))


def _check_index(root, report):
    if KNOWN_GAPS_HEADING not in read_page(root, "index.md").body:
        report.error("index.md has no `{}` section — honest refusal depends on it"
                     .format(KNOWN_GAPS_HEADING))


def _check_frontmatter(page, report):
    if page.in_overlay:
        return  # overlays are loaded whole, not routed as OKF pages (spec §4)
    if not page.has_frontmatter:
        report.error("{}: no frontmatter — every page carries OKF frontmatter"
                     .format(page.relpath))
        return
    if not page.type:
        report.error("{}: frontmatter has no `type` field".format(page.relpath))

    name = os.path.basename(page.relpath)
    reserved = RESERVED_TYPES.get(name)
    if reserved is None:
        return
    at_root = page.relpath == name
    if not at_root:
        report.error("{}: `{}` is a reserved OKF name and belongs at the brain "
                     "root only".format(page.relpath, name))
    elif page.type and page.type != reserved:
        report.error("{}: reserved file must be `type: {}`, found `{}`"
                     .format(page.relpath, reserved, page.type))


def _check_freshness(page, report):
    frontmatter = page.frontmatter
    as_of = frontmatter.get("as_of")
    volatility = frontmatter.get("volatility")

    if "as_of" in frontmatter and not is_iso_date(as_of):
        report.error("{}: `as_of: {}` is not an ISO date (YYYY-MM-DD)"
                     .format(page.relpath, as_of))
    if "volatility" in frontmatter and volatility not in VOLATILITY_VALUES:
        report.error("{}: `volatility: {}` is not one of {}"
                     .format(page.relpath, volatility, "/".join(VOLATILITY_VALUES)))
    if volatility == "fast" and not as_of:
        report.warn("{}: `volatility: fast` with no `as_of` — the router answers "
                    "fast facts with their date attached, and has none to attach"
                    .format(page.relpath))
    if "canonical" in frontmatter and not str(frontmatter.get("canonical") or "").strip():
        report.error("{}: `canonical` is empty — say where the live truth lives, "
                     "or drop the field".format(page.relpath))


def _check_links(root, page, report):
    base = os.path.dirname(os.path.join(root, page.relpath))
    for target in page.links():
        path = target.split("#", 1)[0]
        if not path:
            continue
        resolved = os.path.normpath(os.path.join(base, path))
        if os.path.relpath(resolved, root).startswith(os.pardir):
            report.error("{}: link `{}` points outside the brain".format(page.relpath, target))
        elif not os.path.exists(resolved):
            report.error("{}: link `{}` does not resolve".format(page.relpath, target))


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: lint.py <brain-dir>\n")
        return 2
    report = lint_brain(argv[1])
    print(report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
