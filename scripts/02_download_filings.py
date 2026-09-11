"""Download base filings and record every candidate, amendment, and failure.

Both CSVs are checkpointed after each firm. Amendments are recorded but never
parsed. Run --limit 3 first; nonzero exit means unresolved acquisition failures.
"""
from __future__ import annotations

import argparse
import gzip
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import (
    FILING_DIR, FORMS, INTERIM_DIR, SAMPLE_END, SAMPLE_START, SEC_USER_AGENT,
    UNIVERSE_DIR,
)
from src.edgar import EdgarClient
from src.parse import PARSER_VERSION, html_to_text, tokenize

ROOT = Path(__file__).resolve().parents[1]
TEXT_DIR = INTERIM_DIR / "text"
META_PATH = INTERIM_DIR / "filings_meta.csv"
MANIFEST_PATH = INTERIM_DIR / "filings_manifest.csv"
META_COLUMNS = [
    "ticker", "cik", "company", "sic", "sic_desc", "form", "filing_date",
    "report_date", "acceptance_datetime", "accession", "doc_url", "n_words",
    "n_distinct", "text_path", "parser_version",
]
MANIFEST_COLUMNS = META_COLUMNS + ["status", "error"]


def _load_records(path: Path) -> dict[str, dict]:
    if not path.exists() or not path.stat().st_size:
        return {}
    frame = pd.read_csv(path, dtype=str).fillna("")
    return {str(r["accession"]): r for r in frame.to_dict("records")}


def _write_records(path: Path, records: dict[str, dict], columns: list[str]) -> None:
    out = pd.DataFrame(list(records.values()), columns=columns)
    for col in ("company", "sic_desc", "error"):
        if col in out.columns:
            out[col] = out[col].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    out.to_csv(tmp, index=False, lineterminator="\n")
    tmp.replace(path)


def checkpoint(rows: dict[str, dict], manifest: dict[str, dict]) -> None:
    _write_records(META_PATH, rows, META_COLUMNS)
    _write_records(MANIFEST_PATH, manifest, MANIFEST_COLUMNS)


def _filing_record(firm: pd.Series, filing: pd.Series) -> dict:
    row = {col: filing.get(col, "") for col in META_COLUMNS}
    row.update(ticker=firm["ticker"], cik=firm["cik"], parser_version=PARSER_VERSION)
    for col in ("filing_date", "report_date"):
        row[col] = pd.Timestamp(row[col]).date() if pd.notna(row[col]) and row[col] != "" else ""
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only the first N filers")
    ap.add_argument("--drop-html", action="store_true", help="delete HTML after successful parsing")
    args = ap.parse_args()
    if args.limit is not None and args.limit < 1:
        ap.error("--limit must be positive")
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    universe = pd.read_csv(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    universe = universe[universe["status"] == "domestic_filer"]
    current_ciks = set(universe.cik.astype(str).str.zfill(10))
    if args.limit:
        universe = universe.head(args.limit)
    print(f"{len(universe)} filers")
    rows = _load_records(META_PATH)
    manifest = _load_records(MANIFEST_PATH)
    rows = {k:r for k,r in rows.items() if str(r.get("cik", "")).zfill(10) in current_ciks}
    manifest = {k:r for k,r in manifest.items() if str(r.get("cik", "")).zfill(10) in current_ciks}
    if universe.empty:
        checkpoint(rows, manifest)
        print("ERROR: no domestic filers; no corpus was acquired.", file=sys.stderr)
        return 1
    client = EdgarClient(SEC_USER_AGENT or None)
    failures = 0
    consecutive_network_failures = 0
    abort = False
    for i, (_, firm) in enumerate(universe.iterrows(), 1):
        listing_key = f"listing:{firm['cik']}"
        try:
            filings = client.list_filings(
                firm["cik"], FORMS, SAMPLE_START, SAMPLE_END, include_amendments=True,
            )
            manifest.pop(listing_key, None)
        except Exception as exc:
            failures += 1
            consecutive_network_failures += 1
            manifest[listing_key] = {
                "ticker": firm["ticker"], "cik": firm["cik"], "accession": listing_key,
                "status": "listing_failed", "error": str(exc),
            }
            checkpoint(rows, manifest)
            print(f"ERROR: {firm['ticker']} listing failed: {exc}", file=sys.stderr)
            if consecutive_network_failures >= 3:
                print("ERROR: repeated acquisition failures; stopping. Resume after fixing access.", file=sys.stderr)
                break
            continue
        # Retain the full candidate count even if downloads are stopped early.
        for _, filing in filings.iterrows():
            accn = str(filing["accession"])
            manifest.setdefault(accn, {
                **_filing_record(firm, filing),
                "status": "amendment" if str(filing["form"]).endswith("/A") else "not_attempted",
                "error": "",
            })
        for _, filing in filings.iterrows():
            accn = str(filing["accession"])
            record = _filing_record(firm, filing)
            if str(filing["form"]).endswith("/A"):
                rows.pop(accn, None)
                manifest[accn] = {**record, "status": "amendment", "error": ""}
                continue
            acc = accn.replace("-", "")
            text_path = TEXT_DIR / f"{acc}.txt.gz"
            stage = "parse"
            try:
                text = ""
                # A parser change invalidates old extracted text. A bad text
                # cache is recovered from the raw filing rather than trusted.
                if text_path.exists() and str(rows.get(accn, {}).get("parser_version", "")) == PARSER_VERSION:
                    try:
                        with gzip.open(text_path, "rt", encoding="utf-8") as fh:
                            text = fh.read()
                    except (OSError, EOFError, UnicodeError):
                        text = ""
                if not text.strip():
                    stage = "download"
                    raw = client.fetch_document(filing["doc_url"], accn)
                    if not raw.strip():
                        raise ValueError("Empty raw filing cache or response; remove the empty HTML cache and retry")
                    consecutive_network_failures = 0
                    stage = "parse"
                    text = html_to_text(raw)
                    if not text.strip():
                        raise ValueError("No visible text after parsing")
                    tmp = text_path.with_suffix(".tmp")
                    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
                        fh.write(text)
                    tmp.replace(text_path)
                tokens = tokenize(text)
                if not tokens:
                    raise ValueError("No alphabetic tokens after parsing")
                consecutive_network_failures = 0
            except Exception as exc:
                failures += 1
                rows.pop(accn, None)
                manifest[accn] = {**record, "status": f"{stage}_failed", "error": str(exc)}
                print(f"ERROR: {firm['ticker']} {accn} {stage} failed: {exc}", file=sys.stderr)
                if stage == "download":
                    consecutive_network_failures += 1
                    if consecutive_network_failures >= 5:
                        abort = True
                        break
                continue
            record.update(
                n_words=len(tokens), n_distinct=len(set(tokens)),
                text_path=str(text_path.relative_to(ROOT)),
            )
            rows[accn] = record
            manifest[accn] = {**record, "status": "parsed", "error": ""}
            if args.drop_html:
                try:
                    (FILING_DIR / f"{acc}.html").unlink(missing_ok=True)
                except OSError:
                    pass
        checkpoint(rows, manifest)
        print(f"[{i:3d}/{len(universe)}] {firm['ticker']} {len(filings)} candidates; {len(rows)} parsed in checkpoint")
        if abort:
            print("ERROR: five consecutive download failures; stopping. Resume after fixing access.", file=sys.stderr)
            break
    print(f"Saved {len(rows)} parsed filings and {len(manifest)} manifest records.")
    unresolved = sum(
        str(r.get("status", "")).endswith("_failed") or r.get("status") == "not_attempted"
        for r in manifest.values()
    )
    if failures or unresolved or not rows:
        print(f"ERROR: {failures} failures this run, {unresolved} unresolved manifest failures. Inspect {MANIFEST_PATH}.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
