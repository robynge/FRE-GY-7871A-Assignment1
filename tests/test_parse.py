"""Parser and filing-manifest regressions using synthetic, offline filings."""
import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.parse import html_to_text, tokenize


def test_visible_inline_xbrl_narrative_survives():
    html = '''<html><body><ix:nonNumeric name="acme:RiskDisclosureTextBlock">
    A material <b>LOSS</b> remains <ix:exclude>possible</ix:exclude>.
    </ix:nonNumeric><ix:continuation>Uncertainty increased.</ix:continuation>
    <ix:nonFraction>123</ix:nonFraction></body></html>'''
    assert tokenize(html_to_text(html)) == ["MATERIAL", "LOSS", "REMAINS", "POSSIBLE", "UNCERTAINTY", "INCREASED"]
    assert "123" in html_to_text(html)


def test_hidden_scaffolding_does_not_enter_corpus():
    html = '''<body><ix:header><ix:hidden><ix:nonNumeric>HiddenRisk</ix:nonNumeric></ix:hidden></ix:header>
    <xbrli:context><xbrldi:explicitMember>TaxonomyNoise</xbrldi:explicitMember></xbrli:context>
    <p style="DISPLAY: \n NONE !important">HiddenLoss</p><p hidden>MoreNoise</p>
    <div style="visibility: hidden">Invisible</div><script>ScriptNoise</script>
    <p>Visible risk.</p></body>'''
    assert tokenize(html_to_text(html)) == ["VISIBLE", "RISK"]


def test_numeric_tables_removed_after_visible_fact_unwrap():
    html = '''<table><tr><td>Revenue</td><td><ix:nonFraction>123456789</ix:nonFraction></td></tr></table>
    <table><tr><td>Material uncertainty and risk remain.</td></tr></table>'''
    assert tokenize(html_to_text(html)) == ["MATERIAL", "UNCERTAINTY", "AND", "RISK", "REMAIN"]
    assert "Revenue" in html_to_text(html, drop_numeric_tables=False)


@pytest.fixture
def downloader(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / "scripts" / "02_download_filings.py"
    spec = importlib.util.spec_from_file_location("filing_downloader_test", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for attr, path in {
        "ROOT": tmp_path, "TEXT_DIR": tmp_path / "text", "FILING_DIR": tmp_path / "html",
        "UNIVERSE_DIR": tmp_path, "META_PATH": tmp_path / "meta.csv",
        "MANIFEST_PATH": tmp_path / "manifest.csv",
    }.items():
        monkeypatch.setattr(mod, attr, path)
    monkeypatch.setattr(sys, "argv", [str(script)])
    return mod


def make_universe(mod, tickers=("ABC",)):
    pd.DataFrame([
        {"ticker": ticker, "cik": str(i + 1).zfill(10), "status": "domestic_filer"}
        for i, ticker in enumerate(tickers)
    ], columns=["ticker", "cik", "status"]).to_csv(mod.UNIVERSE_DIR / "universe.csv", index=False)


def candidate(acc, form="10-K"):
    return {"accession": acc, "form": form, "filing_date": pd.Timestamp("2025-02-01"),
            "report_date": pd.Timestamp("2024-12-31"), "doc_url": "https://example.invalid/filing"}


def test_manifest_records_amendments_and_parse_failures(downloader, monkeypatch):
    mod = downloader
    make_universe(mod)
    fetched = []

    class Client:
        def __init__(self, *args):
            pass

        def list_filings(self, *args, **kwargs):
            assert kwargs["include_amendments"] is True
            return pd.DataFrame([candidate("001"), candidate("002", "10-K/A"), candidate("003")])

        def fetch_document(self, url, accession):
            fetched.append(accession)
            return "<p>Material risk exists.</p>" if accession == "001" else "<script>nothing</script>"

    monkeypatch.setattr(mod, "EdgarClient", Client)
    assert mod.main() == 1
    assert fetched == ["001", "003"]
    meta = pd.read_csv(mod.META_PATH, dtype=str)
    manifest = pd.read_csv(mod.MANIFEST_PATH, dtype=str).set_index("accession")
    assert meta["accession"].tolist() == ["001"]
    assert manifest["status"].to_dict() == {"001": "parsed", "002": "amendment", "003": "parse_failed"}
    assert meta.loc[0, "parser_version"] == "2"


def test_repeated_download_failure_keeps_unattempted_candidates(downloader, monkeypatch):
    mod = downloader
    make_universe(mod)

    class Client:
        def __init__(self, *args):
            pass

        def list_filings(self, *args, **kwargs):
            return pd.DataFrame([candidate(str(i)) for i in range(7)])

        def fetch_document(self, *args):
            raise ConnectionError("offline")

    monkeypatch.setattr(mod, "EdgarClient", Client)
    assert mod.main() == 1
    assert pd.read_csv(mod.META_PATH).empty
    statuses = pd.read_csv(mod.MANIFEST_PATH)["status"].value_counts().to_dict()
    assert statuses == {"download_failed": 5, "not_attempted": 2}


def test_checkpoint_survives_failure_on_later_firm(downloader, monkeypatch):
    mod = downloader
    make_universe(mod, ("ABC", "DEF"))

    class Client:
        def __init__(self, *args):
            pass

        def list_filings(self, cik, *args, **kwargs):
            if cik.endswith("2"):
                assert len(pd.read_csv(mod.META_PATH)) == 1
                raise KeyboardInterrupt("simulated interrupted run")
            return pd.DataFrame([candidate("001")])

        def fetch_document(self, *args):
            return "<p>Risk remains.</p>"

    monkeypatch.setattr(mod, "EdgarClient", Client)
    with pytest.raises(KeyboardInterrupt):
        mod.main()
    assert len(pd.read_csv(mod.META_PATH)) == 1
    assert pd.read_csv(mod.MANIFEST_PATH).loc[0, "status"] == "parsed"


def test_empty_universe_writes_readable_empty_outputs(downloader):
    mod = downloader
    make_universe(mod, ())
    assert mod.main() == 1
    assert pd.read_csv(mod.META_PATH).empty
    assert pd.read_csv(mod.MANIFEST_PATH).empty


def test_failed_listings_have_manifest_and_nonzero_exit(downloader, monkeypatch):
    mod = downloader
    make_universe(mod, ("ABC", "DEF", "GHI", "JKL"))

    class Client:
        def __init__(self, *args):
            pass

        def list_filings(self, *args, **kwargs):
            raise ConnectionError("offline")

    monkeypatch.setattr(mod, "EdgarClient", Client)
    assert mod.main() == 1
    manifest = pd.read_csv(mod.MANIFEST_PATH)
    assert len(manifest) == 3
    assert set(manifest["status"]) == {"listing_failed"}


def test_old_parser_cache_is_rebuilt_and_current_cache_resumes(downloader, monkeypatch):
    import gzip
    mod = downloader
    make_universe(mod)
    mod.TEXT_DIR.mkdir()
    with gzip.open(mod.TEXT_DIR / "001.txt.gz", "wt") as fh:
        fh.write("Obsolete text")
    mod._write_records(mod.META_PATH, {"001": {"accession": "001"}}, mod.META_COLUMNS)
    calls = []

    class Client:
        def __init__(self, *args):
            pass

        def list_filings(self, *args, **kwargs):
            return pd.DataFrame([candidate("001")])

        def fetch_document(self, *args):
            calls.append(1)
            return "<ix:nonNumeric>Risk loss uncertainty.</ix:nonNumeric>"

    monkeypatch.setattr(mod, "EdgarClient", Client)
    assert mod.main() == 0
    assert pd.read_csv(mod.META_PATH).loc[0, "n_words"] == 3
    assert mod.main() == 0
    assert len(calls) == 1
