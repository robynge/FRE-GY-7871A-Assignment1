"""Acquire original filings for newly identified September 9, 2026 holdings.

Outputs are additions only. No existing universe, manifest or score file is changed.
Weighted scores are blank because they must be fitted in the final selected corpus.
"""
from collections import Counter
import gzip
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import SAMPLE_START, SAMPLE_END
from src.edgar import EdgarClient
from src.lexicons import lm_word_lists
from src.parse import PARSER_VERSION, html_to_text, tokenize

ISSUERS = {'CNTN':'0001861657', 'HONA':'0002089271', 'PAYP':'0002080845', 'SECZ':'0002094496'}
OUT = ROOT / 'outputs/current_holdings'
TEXT = ROOT / 'data/interim/text'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    TEXT.mkdir(parents=True, exist_ok=True)
    existing = pd.read_csv(ROOT / 'outputs/all_filing_scores.csv', dtype={'cik':str})
    columns = list(existing.columns) + ['Negative_tokens', 'Uncertainty_tokens', 'acquisition']
    client = EdgarClient()
    original_get = client._get
    operations = {'metadata':0, 'documents':0}
    def bounded_get(url, timeout=60):
        kind = 'metadata' if url.endswith('.json') else 'documents'
        operations[kind] += 1
        if operations[kind] > (18 if kind == 'metadata' else 35):
            raise RuntimeError(f'{kind} acquisition ceiling reached')
        return original_get(url, timeout)
    client._get = bounded_get
    lex = lm_word_lists()
    rows, coverage = [], []
    failures = 0
    def checkpoint():
        pd.DataFrame(rows, columns=columns).to_csv(OUT / 'new_filing_scores.csv', index=False)
        pd.DataFrame(coverage).to_csv(OUT / 'new_issuer_coverage.csv', index=False)
    for ticker, cik in ISSUERS.items():
        payload = client.submissions(cik)
        all_forms = payload['_filings']
        scope = all_forms[all_forms.filingDate.between(SAMPLE_START,SAMPLE_END)]
        candidates = scope[scope.form.isin(['10-K','10-Q'])].sort_values('filingDate')
        foreign = scope[scope.form.isin(['20-F','40-F'])]
        record = dict(ticker=ticker,cik=cik,company=payload.get('name'),
                      status='domestic_filer' if len(candidates) else ('foreign_reporting_forms' if len(foreign) else 'no_original_10K_Q_in_window'),
                      original_10K=int(candidates.form.eq('10-K').sum()), original_10Q=int(candidates.form.eq('10-Q').sum()),
                      original_20F_40F=len(foreign), parsed=0, reused=0, failed=0,
                      first_filing=candidates.filingDate.min() if len(candidates) else '',
                      last_filing=candidates.filingDate.max() if len(candidates) else '',
                      metadata_source=f'https://data.sec.gov/submissions/CIK{cik}.json',
                      foreign_filing_source='',note='')
        if len(foreign):
            f=foreign.sort_values('filingDate').iloc[-1]
            record['foreign_filing_source']=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{f.accessionNumber.replace('-','')}/{f.primaryDocument}"
        if not len(candidates):
            record['note']='Foreign annual-report form is outside the original 10-K/10-Q scope.' if len(foreign) else 'No original 10-K/10-Q filed by cutoff; no score is imputed.'
        elif len(candidates)==1:
            record['note']='Only one original quarterly filing by cutoff; current level available, no same-company prior-year comparison.'
        if ticker == 'CNTN':
            record['note']='SEC former names include Tharimmune and Hillstream BioPharma. CIK continuity does not establish stable business or disclosure composition across years.'
        coverage.append(record)
        for _, filing in candidates.iterrows():
            accession = filing.accessionNumber
            reused = existing[(existing.cik==cik)&(existing.accession==accession)]
            if len(reused):
                row=reused.iloc[0].to_dict();row.update(ticker=ticker,acquisition='reused_existing_CIK_accession')
                rows.append(row);record['reused']+=1;checkpoint();continue
            url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-','')}/{filing.primaryDocument}"
            text_path=TEXT/f"{accession.replace('-','')}.txt.gz"
            try:
                raw=client.fetch_document(url,accession)
                text=html_to_text(raw)
                tokens=tokenize(text)
                if not tokens:raise ValueError('No parsed tokens')
                with gzip.open(text_path,'wt',encoding='utf-8') as fh:fh.write(text)
                counts=Counter(tokens)
                hits={k:sum(counts[w] for w in lex[k]) for k in ['Negative','Uncertainty']}
                row=dict(ticker=ticker,cik=cik,company=payload.get('name'),sic=payload.get('sic'),sic_desc=payload.get('sicDescription'),
                         form=filing.form,filing_date=filing.filingDate,report_date=filing.reportDate,
                         acceptance_datetime=str(pd.to_datetime(filing.acceptanceDateTime,utc=True)),accession=accession,doc_url=url,
                         n_words=len(tokens),n_distinct=len(counts),text_path=str(text_path.relative_to(ROOT)),parser_version=PARSER_VERSION,
                         status='parsed',error='',Negative_prop=hits['Negative']/len(tokens),Uncertainty_prop=hits['Uncertainty']/len(tokens),
                         Negative_tfidf=None,Uncertainty_tfidf=None,Negative_tokens=hits['Negative'],Uncertainty_tokens=hits['Uncertainty'],acquisition='newly_parsed')
                assert 0<=row['Negative_prop']<=1 and 0<=row['Uncertainty_prop']<=1
                rows.append(row);record['parsed']+=1;failures=0
                print(ticker,accession,len(tokens),'words',flush=True)
            except Exception as exc:
                failures+=1;record['failed']+=1
                record['note']+=(f' Acquisition failure for {accession}: {type(exc).__name__}.')
                print(ticker,accession,type(exc).__name__,flush=True)
            checkpoint()
            if failures>=2:
                raise RuntimeError('Two consecutive filing failures; stopped without imputing missing scores.')
        assert record['parsed']+record['reused']+record['failed']==len(candidates)
        checkpoint()
    frame=pd.DataFrame(rows)
    assert not frame.accession.duplicated().any()
    print(pd.DataFrame(coverage)[['ticker','status','original_10K','original_10Q','original_20F_40F','parsed','reused','failed']].to_string(index=False))
    print('Acquisition operations',operations)
    return int(any(r['failed'] for r in coverage))

if __name__=='__main__':
    raise SystemExit(main())
