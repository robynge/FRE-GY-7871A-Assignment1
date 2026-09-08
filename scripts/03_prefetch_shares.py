"""Prefetch company facts while filing text downloads; both use cached metadata."""
import importlib.util
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import UNIVERSE_DIR, PRICE_DIR, SAMPLE_START, SAMPLE_END
from src.edgar import EdgarClient

if __name__ == "__main__":
    spec=importlib.util.spec_from_file_location("market_script",Path(__file__).with_name("03_get_market_data.py"))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    client=EdgarClient()
    universe=pd.read_csv(UNIVERSE_DIR/"universe.csv",dtype={"cik":str})
    frames=[client.list_filings(cik,["10-K","10-Q"],SAMPLE_START,SAMPLE_END)
            for cik in universe.loc[universe.status.eq("domestic_filer"),"cik"]]
    meta=pd.concat(frames,ignore_index=True)
    shares=module.get_shares(client,meta)
    shares.to_csv(PRICE_DIR/"shares.csv",index=False)
    shares[shares.shares_status.ne("matched")].to_csv(PRICE_DIR/"shares_missing.csv",index=False)
