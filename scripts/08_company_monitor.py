"""Create company-level monitoring data from the existing filing scores."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.company_monitor import build_monitor, save_monitor
from src.config import AS_OF_DATE, OUTPUT_DIR, UNIVERSE_DIR

if __name__ == "__main__":
    scores = pd.read_csv(OUTPUT_DIR / "all_filing_scores.csv", dtype={"cik": str})
    universe = pd.read_csv(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    data = build_monitor(scores, universe, AS_OF_DATE)
    save_monitor(data, OUTPUT_DIR / "company_monitor")
    print(data["metadata"])
    for form in ("quarterly", "annual"):
        result = data["summary"][form]
        print(form, {k: v for k, v in result.items() if not isinstance(v, list)})

    # Company rows describe today's holdings; missing filing coverage stays visible.
    import json
    import re
    from src.company_monitor import _clean
    holdings_dir = UNIVERSE_DIR.parent / 'current_holdings'
    files = sorted(holdings_dir.glob('*_Holdings_' + AS_OF_DATE + '.csv'))
    if files:
        candidates = pd.read_csv(UNIVERSE_DIR / 'holdings_candidates.csv', dtype={'cik':str}).fillna('')
        # The Tokyo listing and US ADR are the same Komatsu issuer.
        candidates.loc[candidates.raw_ticker.eq('6301'), ['cik','ticker']] = ['0000056594','6301']
        current = []
        for key, rows in candidates[~candidates.status.eq('non_company_security')].groupby(candidates.cik.where(candidates.cik.ne(''), 'TICKER:' + candidates.ticker.where(candidates.ticker.ne(''), candidates.raw_ticker))):
            r = rows.iloc[0]
            current.append({'ticker':r.ticker or r.raw_ticker,'company':r.ark_name,'cik':r.cik or None,
                            'funds':'|'.join(sorted({f for fs in rows.funds for f in fs.split('|')})),
                            'coverage_status':r.status,'coverage_reason':r.exclusion_reason,
                            'tickers':'|'.join(sorted(set(rows.ticker)-{''}))})
        raw = pd.concat([pd.read_csv(p).fillna('') for p in files])
        for name, rows in raw[raw.ticker.eq('')].groupby('company'):
            if not name.strip() or re.search(r'ETF|TRSY|TREASURY|\bWTS\b|CASH',name,re.I):continue
            current.append({'ticker':'','company':name,'cik':None,'funds':'|'.join(sorted(set(rows.fund))),
                            'coverage_status':'No matched filing identifier','coverage_reason':'No exchange ticker supplied in the holdings file; no language score assigned','tickers':''})
        data['current_companies']=current
        data['metadata']['holdings_date']=AS_OF_DATE
        data['metadata']['selection']='Only companies held by at least one of the six ETFs on '+AS_OF_DATE
        data['metadata']['word_share_unit']='Category-word occurrences as a percentage of all retained words; 1 means one occurrence per 100 words'
        (OUTPUT_DIR/'company_monitor'/'data.json').write_text(json.dumps(_clean(data),indent=2,allow_nan=False))
