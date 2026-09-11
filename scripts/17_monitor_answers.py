"""Four monitoring answers from the same quarterly observations used in Excel."""
import json
from pathlib import Path
from statistics import mean

out = Path('outputs/company_monitor')
data = json.loads((out / 'data.json').read_text())
display = json.loads((out / 'quarterly_display.json').read_text())
matrix = {r['ticker']: r for r in display['companies']}
companies = {r['ticker']: r for r in data['quarterly']}
base, end = '2025Q2', '2026Q2'
years = [f'{y}Q2' for y in range(2021, 2027)]
paired = [t for t in companies if all(matrix[t][f].get(q) is not None for f in ['negative_pct', 'uncertainty_pct'] for q in [base, end])]
balanced = [t for t in paired if all(matrix[t]['uncertainty_pct'].get(q) is not None for q in years)]

def record(t, field):
    return {'ticker': t, 'company': companies[t]['company'], 'base_pct': matrix[t][field][base], 'end_pct': matrix[t][field][end]}

def comparison(field):
    return {'companies': len(paired), 'increased': sum(matrix[t][field][end] > matrix[t][field][base] for t in paired),
            'decreased': sum(matrix[t][field][end] < matrix[t][field][base] for t in paired),
            'base_company_average_pct': mean(matrix[t][field][base] for t in paired),
            'end_company_average_pct': mean(matrix[t][field][end] for t in paired)}

def ranking(field, rising=False):
    tickers = [t for t in paired if (matrix[t][field][end] > matrix[t][field][base] if rising else matrix[t][field][end] < matrix[t][field][base])]
    return [record(t, field) for t in sorted(tickers, key=lambda t: ((-1 if rising else 1) * (matrix[t][field][end] - matrix[t][field][base]), t))[:5]]

latest = sorted((r for r in companies.values() if r['fresh']), key=lambda r: (-r['latest_uncertainty_pct'], r['ticker']))[:5]
answers = {'base_quarter': base, 'end_quarter': end, 'holdings_date': data['metadata']['holdings_date'],
           'filing_companies': len(companies), 'paired_tickers': sorted(paired),
           'negative': comparison('negative_pct'), 'uncertainty': comparison('uncertainty_pct'),
           'negative_declines': ranking('negative_pct'), 'uncertainty_increases': ranking('uncertainty_pct', True),
           'uncertainty_declines': ranking('uncertainty_pct'),
           'highest_latest_uncertainty': [{'ticker': r['ticker'], 'company': r['company'], 'report_date': r['latest_report_date'], 'uncertainty_pct': r['latest_uncertainty_pct'], 'source': r['latest_doc_url']} for r in latest],
           'long_term': {'companies': len(balanced), 'tickers': sorted(balanced), 'quarters': years,
                         'company_average_pct': [mean(matrix[t]['uncertainty_pct'][q] for t in balanced) for q in years]}}
without_kdk = [t for t in paired if t != 'KDK']
answers['uncertainty_excluding_kdk'] = {'companies': len(without_kdk), 'base_company_average_pct': mean(matrix[t]['uncertainty_pct'][base] for t in without_kdk), 'end_company_average_pct': mean(matrix[t]['uncertainty_pct'][end] for t in without_kdk)}
assert len(set(paired)) == len(paired)
for field in ['negative', 'uncertainty']:
    assert answers[field]['increased'] + answers[field]['decreased'] <= len(paired)
for t in paired:
    for q in [base, end]:
        filings = matrix[t]['filings_by_quarter'][q]
        assert len(filings) == 1, 'Reassess quarter comparisons if multiple filings map to one quarter'
(out / 'research_answers.json').write_text(json.dumps(answers, indent=2))
print(f'Monitoring answers: {len(paired)} annual comparisons; {len(balanced)} companies across six Q2 observations.')
