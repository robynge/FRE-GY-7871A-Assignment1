"""Use the six dated current holdings snapshots as the analysis selection."""
from pathlib import Path
import importlib.util
import json
import shutil
import sys
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import ROOT,UNIVERSE_DIR,INTERIM_DIR,AS_OF_DATE
from src.edgar import EdgarClient
spec=importlib.util.spec_from_file_location('universe_builder',ROOT/'scripts/01_build_universe.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
folder=ROOT/'data/current_holdings'
archive=folder/'previous_selection';archive.mkdir(exist_ok=True)
for path in [*UNIVERSE_DIR.glob('*.csv'),INTERIM_DIR/'filings_manifest.csv',INTERIM_DIR/'filings_meta.csv']:
 if path.exists() and not (archive/path.name).exists():shutil.copy2(path,archive/path.name)
raw=pd.concat([pd.read_csv(folder/f'{fund}_Holdings_{AS_OF_DATE}.csv') for fund in builder.ARK_FUNDS],ignore_index=True)
assert set(pd.to_datetime(raw['date'],format='%m/%d/%Y',errors='coerce').dropna().dt.strftime('%Y-%m-%d'))=={AS_OF_DATE}
raw=builder.comparison_positions(raw)
client=EdgarClient();cik_map=client.ticker_to_cik()
# SEC source-confirmed identifiers absent from the exchange ticker mapping.
cik_map.update(builder.CIK_OVERRIDES)
candidates=builder.build_candidates(raw,cik_map)
universe=builder.build_universe(candidates,client)
if universe.status.eq('lookup_error').any():raise RuntimeError('Resolve issuer lookup failures before changing the sample')
for _,row in universe.iterrows():
 mask=candidates.cik.eq(row.cik)
 for col in ['status','exclusion_reason','no10x_reason']:
  candidates.loc[mask,col]=row.get(col,'')
new_path=ROOT/'outputs/current_holdings/new_filing_scores.csv'
new=pd.read_csv(new_path,dtype={'cik':str})
manifest=pd.read_csv(archive/'filings_manifest.csv',dtype={'cik':str})
manifest=manifest[manifest.cik.isin(universe.loc[universe.status.eq('domestic_filer'),'cik'])].copy()
new['status']='parsed';new['error']=''
manifest=pd.concat([manifest,new],ignore_index=True).drop_duplicates('accession',keep='last')
names=universe.set_index('cik').ticker.to_dict();manifest['ticker']=manifest.cik.map(names)
expected=int(universe.loc[universe.status.eq('domestic_filer'),['n_10k','n_10q']].sum().sum())
actual=int(manifest.form.isin(['10-K','10-Q']).sum())
assert actual==expected,(actual,expected)
assert manifest.loc[manifest.form.isin(['10-K','10-Q']),'status'].eq('parsed').all()
for name,frame in [('ark_holdings_raw.csv',raw),('holdings_positions.csv',raw),('holdings_candidates.csv',candidates),('universe.csv',universe),('holdings_exclusions.csv',candidates[~candidates.status.eq('domestic_filer')])]:frame.to_csv(UNIVERSE_DIR/name,index=False)
manifest.to_csv(INTERIM_DIR/'filings_manifest.csv',index=False)
manifest[manifest.status.eq('parsed')].drop(columns=['status','error'],errors='ignore').to_csv(INTERIM_DIR/'filings_meta.csv',index=False)
(folder/'selection.json').write_text(json.dumps({'as_of_date':AS_OF_DATE,'source':'https://github.com/robynge/ark-routine/tree/main/data/holdings/2026/'+AS_OF_DATE,'current_raw_identifiers':len(candidates),'domestic_companies':int(universe.status.eq('domestic_filer').sum()),'original_filings':actual},indent=2))
print(candidates.groupby('status').size().to_dict(), 'domestic companies',int(universe.status.eq('domestic_filer').sum()),'original filings',actual)
