"""Retrieve the six dated snapshots defining the current-holdings study."""
from pathlib import Path
import sys
import subprocess
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.config import ARK_FUNDS,AS_OF_DATE
if __name__=='__main__':
 folder=ROOT/'data/current_holdings';folder.mkdir(exist_ok=True)
 frames=[]
 for fund in ARK_FUNDS:
  name=f'{fund}_Holdings_{AS_OF_DATE}.csv';path=folder/name
  if not path.exists():
   remote=f'repos/robynge/ark-routine/contents/data/holdings/{AS_OF_DATE[:4]}/{AS_OF_DATE}/{name}?ref=main'
   path.write_bytes(subprocess.check_output(['gh','api',remote,'-H','Accept: application/vnd.github.raw+json']))
  frame=pd.read_csv(path);dates=pd.to_datetime(frame.date,format='%m/%d/%Y',errors='coerce')
  assert set(dates.dropna().dt.strftime('%Y-%m-%d'))=={AS_OF_DATE},'Source date differs from requested holdings date'
  assert frame.loc[dates.notna(),'fund'].eq(fund).all()
  frames.append(frame.loc[dates.notna()])
 pd.concat(frames,ignore_index=True).to_csv(ROOT/'data/universe/ark_holdings_raw.csv',index=False)
 print(f'Six holdings snapshots dated {AS_OF_DATE} saved.')
