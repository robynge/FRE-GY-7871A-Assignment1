"""Conservative cover-page share counts from explicitly tagged inline XBRL.

Only EntityCommonStockSharesOutstanding is eligible. A total takes precedence
on the selected date; otherwise uniquely identified stock classes are summed
only when their latest observations share that date. Ambiguity remains missing.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

SHARES_TAG = "dei:EntityCommonStockSharesOutstanding"


def _date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _local(name):
    return (name or "").rsplit(":", 1)[-1].lower()


def _context(node):
    instants = node.find_all(lambda t: _local(t.name) == "instant")
    if len(instants) != 1 or node.find(lambda t: _local(t.name) in {"startdate", "enddate", "typedmember"}):
        return None
    as_of = _date(instants[0].get_text(strip=True))
    dimensions = node.find_all(lambda t: _local(t.name) == "explicitmember")
    if len(dimensions) > 1 or any(
        _local(d.get("dimension")) != "statementclassofstockaxis" for d in dimensions
    ):
        return None
    stock_class = dimensions[0].get_text(strip=True) if dimensions else None
    if as_of is None or (dimensions and not stock_class):
        return None
    return as_of, stock_class


def _number(fact):
    """Apply supported inline numeric transformations, scale and sign exactly."""
    if str(fact.get("xsi:nil", "false")).lower() in {"true", "1"}:
        return None
    fmt = _local(fact.get("format")).replace("-", "")
    if fmt not in {"", "numdotdecimal", "numcommadecimal", "numspacedot", "numspacecomma", "numdash", "zerodash"}:
        return None
    # ix:exclude is explicitly excluded from the fact's numeric value.
    text = "".join(str(s) for s in fact.find_all(string=True)
                   if not any(_local(p.name) == "exclude" for p in s.parents))
    text = re.sub(r"\s+", "", text).replace("−", "-")
    if fmt in {"numdash", "zerodash"}:
        text = "0" if text in {"-", "–", "—"} else text
    elif fmt in {"numcommadecimal", "numspacecomma"}:
        if not re.fullmatch(r"[+\-]?(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?", text):
            return None
        text = text.replace(".", "").replace(",", ".")
    else:
        if not re.fullmatch(r"[+\-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", text):
            return None
        text = text.replace(",", "")
    try:
        scale = int(fact.get("scale", "0"))
        if abs(scale) > 20 or fact.get("sign", "") not in {"", "-", "+"}:
            return None
        value = Decimal(text) * (Decimal(10) ** scale)
        if fact.get("sign") == "-":
            value = -value
        if not value.is_finite() or value <= 0 or value != value.to_integral_value():
            return None
        return value
    except (ValueError, InvalidOperation, OverflowError):
        return None


def extract_cover_shares(raw_html, filing_date):
    """Return an audited count, as-of date, status, tag and stock-class list.

    Missing or conflicting facts return NaN rather than a guessed or partial
    count. Future observations and unsupported dimensions are ineligible.
    """
    absent = {"shares_outstanding": float("nan"), "shares_as_of": None,
              "shares_status": "missing_cover_page_fact", "shares_tag": SHARES_TAG,
              "share_classes": []}
    cutoff = _date(filing_date)
    if cutoff is None:
        return dict(absent, shares_status="invalid_filing_date")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(raw_html, "lxml")
    contexts = {}
    for node in soup.find_all(lambda t: _local(t.name) == "context"):
        context_id = node.get("id")
        parsed = _context(node)
        if context_id in contexts and contexts[context_id] != parsed:
            contexts[context_id] = None
        else:
            contexts[context_id] = parsed
    facts = []
    invalid_context = False
    for fact in soup.find_all("ix:nonfraction"):
        if fact.get("name", "").lower() != SHARES_TAG.lower():
            continue
        context = contexts.get(fact.get("contextref"))
        if context is None:
            invalid_context = True
            continue
        as_of, stock_class = context
        if as_of <= cutoff:
            facts.append((as_of, stock_class, _number(fact)))
    if not facts:
        return dict(absent, shares_status="unsupported_or_missing_context" if invalid_context else "missing_cover_page_fact")
    latest = max(as_of for as_of, _, _ in facts)
    base = dict(absent, shares_as_of=latest.isoformat())
    current = {(stock_class, value) for as_of, stock_class, value in facts if as_of == latest}
    totals = {value for stock_class, value in current if stock_class is None}
    if totals:
        if len(totals) != 1 or None in totals:
            return dict(base, shares_status="ambiguous_cover_page_fact")
        return dict(base, shares_outstanding=int(totals.pop()), shares_status="matched_html_aggregate")
    classes = sorted({stock_class for _, stock_class, _ in facts if stock_class is not None})
    base["share_classes"] = classes
    if invalid_context:
        return dict(base, shares_status="unsupported_or_missing_context")
    counts = []
    for stock_class in classes:
        class_latest = max(as_of for as_of, cls, _ in facts if cls == stock_class)
        if class_latest != latest:
            return dict(base, shares_status="inconsistent_class_dates")
        values = {value for cls, value in current if cls == stock_class}
        if len(values) != 1 or None in values:
            return dict(base, shares_status="ambiguous_cover_page_fact")
        counts.append(values.pop())
    if not counts:
        return base
    return dict(base, shares_outstanding=int(sum(counts)), shares_status="matched_html_classes")
