"""Locate Item 1A and classify how the filer chose to disclose risk factors.

A dictionary score is a property of the words a filer chose to print. A 10-Q
that replaces its risk factors with a pointer to the annual report prints far
fewer uncertainty words without the business having become any more certain.
This module separates the two so that a score change can be attributed to
either a change in what was written or a change in how much was written.

Three disclosure modes are distinguished, because the middle one is real and
common:

    full             the risk factors are restated in the filing
    partial_update   no material changes are claimed, except for stated updates
    reference_only   no material changes are claimed and nothing is restated

The section boundary is found on the parsed visible text, which is whitespace
collapsed to single spaces. Every rule here was written against filings in this
corpus, not from a specification; `scripts/18_risk_sections.py` re-checks the
hit rate and the mode distribution whenever the corpus changes.
"""

from __future__ import annotations

import re

from .parse import tokenize

# "Item 1A" alone matches cross-references such as "in Part I, Item 1A of our
# Annual Report". Requiring the title immediately after removes those. Filers
# separate the number from the title with a period, a colon, a hyphen or an
# em/en dash; Costco uses "Item 1A—Risk Factors". A closing quotation mark is
# consumed with the title so that what follows is the filer's own next word.
_HEADER = re.compile(
    r"Item\s*1A\s*[.:\-–—]?\s*[.:]?\s*[\"'“”]?\s*Risk\s+Factors\s*[\"'“”]?",
    re.I,
)

# A heading is preceded by the end of the previous section. A cross-reference is
# preceded by the grammar that introduces it.
_REFERENCE_CUE = re.compile(
    r"(?:\bpart\s+i+\s*,?|\bsee|\bin|\bunder|\bof|\bto|\band|\bfrom|\bwithin|\btitled"
    r"|\bour|\bthe|\bdescribed|\bset\s+forth|\bincluded|\brefer)\s*[\"'“”]?\s*$",
    re.I,
)

# Item headings that can legitimately follow Item 1A, with their titles. The
# title is required: "Item 2" on its own occurs inside risk-factor prose. A bare
# "SIGNATURES" is deliberately absent; case-insensitively it also matches
# "Signature Bank" and "electronic signature", which truncated bank and lender
# risk factors at the first mention of either.
_SECTION_END = re.compile(
    r"Item\s*(?:1B\s*[.:]?\s*Unresolved"
    r"|2\s*[.:]?\s*(?:Unregistered|Propert)"
    r"|3\s*[.:]?\s*(?:Defaults|Legal|Quantitative)"
    r"|4\s*[.:]?\s*(?:Mine|Controls|Submission)"
    r"|5\s*[.:]?\s*Other\s+Information"
    r"|6\s*[.:]?\s*Exhibit)",
    re.I,
)

# A contents line reaches the next item across nothing but a page number. Intel
# closes its 10-K with a cross-reference index whose entries read
# "Item 1A. Risk Factors Pages 48 - 62 Item 1B. Unresolved Staff Comments None",
# so a "Pages n - m" run counts as the same kind of filler.
_TOC_LOOKAHEAD = 90
_CONTENTS_LINE = re.compile(r"^[\s.\d]*(?:Pages?[\s\d\-–—]*)?Item\s*\d", re.I)

# A heading is followed by the first sentence of the section. A cross-reference
# is followed by the rest of the sentence that contains it: "… Item 1A of our
# Annual Report", "… Risk Factors ” and elsewhere in this report". One trailing
# full stop is allowed, because "Item 1A. Risk Factors. There have been …" is a
# heading with a period after the title.
_OPENS_A_SENTENCE = re.compile(r"^\s*[.:]?\s*[A-Z]")

_NO_CHANGE = re.compile(
    r"(?:there\s+(?:have|has)\s+been\s+no\s+material\s+change"
    r"|there\s+(?:are|were)\s+no\s+material\s+change"
    r"|no\s+material\s+change(?:s)?\s+(?:to|from|in)\s+(?:the\s+|our\s+|these\s+)?risk\s+factor"
    r"|risk\s+factors?\s+(?:have|has)\s+not\s+materially\s+changed)",
    re.I,
)

_UPDATE_MARKER = re.compile(
    r"(?:except\s+as\s+(?:set\s+forth|described|disclosed|otherwise|provided|follows)"
    r"|other\s+than\s+(?:as\s+)?(?:set\s+forth|described|disclosed)"
    r"|except\s+for\s+the\s+(?:risk|following)"
    r"|in\s+addition\s+to\s+the\s+risk\s+factor"
    r"|(?:we\s+are|we\s+have)\s+(?:supplement|updat|revis)"
    r"|the\s+following\s+(?:risk\s+factor|amended|revised))",
    re.I,
)

# Tesla points at the annual report without ever claiming that nothing changed:
# "Our operations and financial results are subject to various risks and
# uncertainties, including those described in Part I, Item 1A of our Annual
# Report". That is a reference, so a pointer counts alongside the no-change
# claim. Only the opening of a section is searched, because a full restatement
# running to tens of thousands of words will mention the annual report somewhere.
_ANNUAL_REPORT_POINTER = re.compile(
    r"(?:our|the|its)\s+(?:most\s+recent\s+)?Annual\s+Report"
    r"|Form\s+10-K\s+for\s+the\s+(?:fiscal\s+)?year"
    r"|incorporated\s+(?:herein\s+)?by\s+reference",
    re.I,
)

_OPENING_CHARS = 800

# Above this a section has restated risk factors whatever it says about them.
# Reference-only sections in this corpus cluster below 150 words; genuine
# partial updates start well above it.
REFERENCE_ONLY_MAX_WORDS = 400


def _cites_rather_than_opens(text: str, position: int) -> bool:
    """True when the grammar before this position introduces a cross-reference."""
    return bool(_REFERENCE_CUE.search(text[max(0, position - 60):position]))


def _is_heading(text: str, match: re.Match) -> bool:
    """True when this occurrence starts the section rather than citing it."""
    if _cites_rather_than_opens(text, match.start()):
        return False
    after = text[match.end():match.end() + _TOC_LOOKAHEAD]
    if _CONTENTS_LINE.match(after):
        return False
    return bool(_OPENS_A_SENTENCE.match(after))


def find_risk_section(text: str) -> tuple[int, int] | None:
    """Character span of the Item 1A section, or None when it is not present."""
    headings = [m for m in _HEADER.finditer(text) if _is_heading(text, m)]
    if not headings:
        return None
    start = headings[-1].end()
    end = len(text)
    for candidate in _SECTION_END.finditer(text, start):
        # "see Item 3. Legal Proceedings" inside a risk factor is a citation,
        # not the end of the section.
        if not _cites_rather_than_opens(text, candidate.start()):
            end = candidate.start()
            break
    return start, end


def extract_risk_section(text: str) -> str:
    span = find_risk_section(text)
    return text[span[0]:span[1]].strip() if span else ""


def classify_disclosure_mode(section: str) -> str:
    """Label how the risk factors were disclosed, given the section text.

    full            risk factors are restated in this filing
    partial_update  nothing material changed, except for the updates given here
    reference_only  nothing material changed, and the reader is sent elsewhere
    omitted         the section is present but says nothing, e.g. "Not applicable"
    not_found       no Item 1A heading was located
    """
    if not section.strip():
        return "not_found"
    n_words = len(tokenize(section))
    opening = section[:_OPENING_CHARS]
    claims_no_change = bool(_NO_CHANGE.search(opening))
    stated_updates = bool(_UPDATE_MARKER.search(opening))
    points_elsewhere = bool(_ANNUAL_REPORT_POINTER.search(opening))

    if n_words > REFERENCE_ONLY_MAX_WORDS:
        return "partial_update" if claims_no_change else "full"
    if stated_updates:
        return "partial_update"
    if claims_no_change or points_elsewhere:
        return "reference_only"
    return "omitted"


def describe_filing(text: str) -> dict:
    """Section span, length and disclosure mode for one parsed filing."""
    span = find_risk_section(text)
    section = text[span[0]:span[1]].strip() if span else ""
    body = (text[:span[0]] + " " + text[span[1]:]) if span else text
    return {
        "risk_found": span is not None,
        "risk_words": len(tokenize(section)),
        "body_words": len(tokenize(body)),
        "risk_mode": classify_disclosure_mode(section),
        "risk_start": span[0] if span else -1,
        "risk_end": span[1] if span else -1,
    }
