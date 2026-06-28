"""Shared cleanup for Claude-generated AI Advisory markdown text.

Claude's advisory output uses lightweight markdown (## headings, **bold**,
"- " bullets). Both the PDF and Excel report builders need the same
structural parsing and the same residual-symbol cleanup so neither output
leaks raw markdown characters (##, **, '') into the reader-facing text.
"""
from __future__ import annotations

import re

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_HASH_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$")
_BOLD_HEADING_RE = re.compile(r"^\*\*(.+?)\*\*:?$")
_DOUBLE_SINGLE_QUOTE_RE = re.compile(r"''(.+?)''")
_BACKTICK_RE = re.compile(r"`([^`]+)`")
_DIVIDER_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
_NUMBERED_RE = re.compile(r"^\d+[.)]\s+(.+)$")

# Canonical top-level section titles the advisory prompts are asked to emit,
# in report order. Matching is case-insensitive and ignores a leading "#"
# heading level, so the same splitter works whether Claude emits "##" or "#".
SECTION_TITLES = [
    "Executive Bottom Line",
    "Key Data Insights",
    "AI Advisory",
    "Modelling & Analytics Readiness",
    "Top Priority Actions",
    "Bottom Line Summary",
]


def strip_residual_markdown(text: str) -> str:
    """Removes leftover markdown artefacts (stray **, '', `code`, etc.) from text."""
    text = _DOUBLE_SINGLE_QUOTE_RE.sub(r'"\1"', text)
    text = text.replace("''", '"')
    text = _BACKTICK_RE.sub(r"\1", text)
    text = re.sub(r"\*{2,}", "", text)
    return text


def clean_heading_text(text: str) -> str:
    text = text.strip().strip("*").strip().rstrip(":")
    return _BACKTICK_RE.sub(r"\1", text)


def to_plain_text(text: str) -> str:
    """Strips all markdown emphasis markers, returning plain readable text."""
    text = _BOLD_RE.sub(r"\1", text)
    return strip_residual_markdown(text)


def parse_advisory_blocks(text: str) -> list[tuple[str, str]]:
    """Parses Claude's advisory markdown into (kind, content) tuples.

    kind is one of "heading", "bullet", "body". Content still carries any
    inline **bold** markers — callers decide whether to render or strip them.
    """
    blocks: list[tuple[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or _DIVIDER_RE.match(line):
            continue

        hash_match = _HASH_HEADING_RE.match(line)
        if hash_match:
            blocks.append(("heading", clean_heading_text(hash_match.group(1))))
            continue

        bold_heading_match = _BOLD_HEADING_RE.match(line)
        if bold_heading_match:
            blocks.append(("heading", clean_heading_text(bold_heading_match.group(1))))
        elif line.startswith(("- ", "* ")):
            blocks.append(("bullet", line[2:].strip()))
        elif _NUMBERED_RE.match(line):
            blocks.append(("bullet", _NUMBERED_RE.match(line).group(1).strip()))
        else:
            blocks.append(("body", line))
    return blocks


def split_advisory_sections(text: str) -> dict[str, str]:
    """Splits a single advisory markdown blob into named top-level sections.

    Splits on any heading line (## or **bold**) whose text matches one of
    SECTION_TITLES (case-insensitive). Content before the first recognised
    heading, if any, is discarded. Unrecognised headings stay nested inside
    whichever recognised section precedes them (e.g. the "### A./B./C."
    sub-headings under "AI Advisory").
    """
    sections: dict[str, list[str]] = {}
    current: str | None = None
    titles_lower = {t.lower(): t for t in SECTION_TITLES}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        hash_match = _HASH_HEADING_RE.match(line)
        bold_match = _BOLD_HEADING_RE.match(line)
        heading_text = None
        if hash_match and line.startswith("##") and not line.startswith("###"):
            heading_text = clean_heading_text(hash_match.group(1))
        elif bold_match:
            heading_text = clean_heading_text(bold_match.group(1))

        if heading_text and heading_text.lower() in titles_lower:
            current = titles_lower[heading_text.lower()]
            sections.setdefault(current, [])
            continue

        if current is not None:
            sections[current].append(raw_line)

    return {name: "\n".join(lines).strip() for name, lines in sections.items()}
