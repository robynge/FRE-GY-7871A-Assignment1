"""Generate and execute the assignment notebook against the local full corpus.

Run after acquisition and market data are complete:
    python scripts/05_notebook.py

The default recomputes all exhibits and saves real cell outputs. --no-execute
writes an explicitly unexecuted notebook, useful for inspecting its source.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def build_notebook():
    markdown = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    cells = [
        markdown(r"""# Uncertainty and sentiment in annual and quarterly reports

FRE-GY 7871 A · Assignment 1 · Filing dates: January 2021 through September 9, 2026

This notebook computes dictionary-based negative sentiment and uncertainty,
constructs filing-event outcomes and controls, and presents six tables and one
figure. The course-period comparison covers January 2021 through December 2025.
Negative sentiment and uncertainty are analysed separately. The company
universe is derived from the supplied ARK holdings and resolved to SEC filers;
actual acquisition and sample counts appear below.

Run all cells after downloading the complete local filing corpus, lexicons,
prices, corporate actions and filing-specific share counts. The computation
requires local data excluded from the repository. Tables and the figure are
recomputed when the notebook runs. Saved outputs are aggregate results; the
notebook does not embed filing documents or the observation-level dataset.
"""),
        code("""from pathlib import Path
import sys
import json
import io
from contextlib import redirect_stdout
from collections import Counter

import numpy as np
import pandas as pd
from IPython.display import display, Markdown, Image, HTML

# Execution from the repository or its immediate project directory is supported.
ROOT = Path.cwd().resolve()
if not (ROOT / 'src' / 'analysis.py').is_file():
    if (ROOT / 'assignment' / 'src' / 'analysis.py').is_file():
        ROOT = ROOT / 'assignment'
    else:
        raise RuntimeError('Open this notebook with the assignment repository as the working directory.')
sys.path.insert(0, str(ROOT))
from src.analysis import run_analysis
from src.scoring import score_corpus
from src.config import OUTPUT_DIR, SAMPLE_START, SAMPLE_END, AS_OF_DATE
from src.report_math import format_number
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
"""),
        markdown(r"""## Tone measures

For dictionary category $c$, the proportional score is

$$P_{cj}=\frac{\sum_{i\in c}tf_{ij}}{W_j}.$$

Here $W_j$ is the number of tokens in filing $j$. Percentages in descriptive tables equal $100P_{cj}$; regressions
use the fraction in its original units.

The equation (1) weighted score is

$$T_{cj}=\sum_{i\in c:tf_{ij}>0}
\frac{1+\ln(tf_{ij})}{1+\ln(a_j)}\ln\left(\frac{N}{df_i}\right),
\qquad a_j=\frac{W_j}{V_j}.$$

Here $V_j$ is the number of distinct words in filing $j$, $N$ is the number
of documents in the estimation corpus and $df_i$ is document frequency.
All logarithms are natural. The weighted score is a sum, not a proportion.
Document frequencies are fitted independently for the text, volatility and
return samples and refitted within annual-report and quarterly-report samples.
The active categories in the 1993–2025 Master Dictionary (updated March 2026)
contain 2,345 negative words and 297 uncertainty words. Positive category years
identify active entries; negative years mark removals and are excluded.
[Official dictionary and documentation](https://sraf.nd.edu/loughranmcdonald-master-dictionary/).

The three constructed documents below provide a worked example of the formula.
"""),
        code("""example_documents = [Counter('LOSS LOSS RISK GAIN'.split()),
                     Counter('LOSS GAIN GAIN'.split()),
                     Counter('RISK RISK RISK GAIN'.split())]
equation_example = score_corpus(example_documents, {'Example': {'LOSS', 'RISK'}})
equation_example.index = ['d1', 'd2', 'd3']
equation_example['a_j'] = equation_example.n_words / equation_example.n_distinct
np.testing.assert_allclose(equation_example.Example_tfidf, [0.8480, 0.2885, 0.5026], atol=0.00005)
display(equation_example[['a_j', 'Example_prop', 'Example_tfidf']].style.format('{:.4f}'))
"""),
        markdown(r"""## Sample and event construction

Filters remove amendments and failed parses; require at least 2,000 words for
10-Ks or 1,000 for 10-Qs; and retain the earliest filing per company and
calendar quarter. These filters define the text sample for descriptive statistics
and trends. Outcome samples additionally require a usable event date, a preceding
close of at least \$3, sufficient price history, the relevant complete outcome
window, and filing-specific shares and controls. Table 1 reports separate text,
volatility and return sample waterfalls. Recent filings remain in text analysis
even when future return or volatility windows have not yet completed.

Acceptance timestamps are converted from UTC to Eastern time. Acceptance at or
after the NYSE session’s actual closing time, including an early close, shifts
its calendar date forward one day. Day 0 is the first NYSE trading day on or
after the later of this date and the filing date.

Total-return adjusted closes measure buy-and-hold excess returns against SPY
for days [0,+3], starting from the close on day −1. Realised volatility uses
returns over [−60,−6] before filing and [+4,+63] after filing, annualised by
$\sqrt{252}$. Market observations end with the last completed session before the analysis
cutoff. Missing future returns are not imputed. The final 2026 quarter is
incomplete; its filing counts and quarterly averages cover only the elapsed
portion of the quarter.

Historical nominal closes determine the \$3 filter and size. Share counts must
match the scored accession and use a valid cover-page instant no later than
filing; weighted-average shares are not a substitute. Historical nominal
volume times nominal close gives dollar volume. Corporate actions are retained
to undo subsequent splits in Yahoo's split-adjusted price and volume histories.
"""),
        code("""# This call checks acquisition completeness before constructing the sample.
# Its detailed progress text is suppressed; aggregate counts are displayed below.
with redirect_stdout(io.StringIO()):
    analysis_sample = run_analysis()
    course_sample = run_analysis(sample_end='2025-12-31', output_dir=OUTPUT_DIR / 'course_2021_2025')
audit = json.loads((OUTPUT_DIR / 'audit.json').read_text())
print(f"Filing dates: {audit['sample_start']} to {audit['sample_end']}; market observations through {audit['market_last_date']}.")
print(f"Text sample: {audit['final_filings']:,} filings from {audit['final_companies']:,} companies.")
print(f"Volatility sample: {audit['volatility_filings']:,}; return sample: {audit['return_filings']:,} filings.")
print(f"All scored original filings: {audit['all_scored_filings']:,}.")
print(f"Day-0 shifts before market filters: {audit['day0_moved_before_market_filters']:,}.")

print('Dictionary word counts:', audit['lexicon_counts'])
print('Words shared by the two dictionaries:', audit['lexicon_overlap'])

def show_table(number):
    table = pd.read_csv(OUTPUT_DIR / f'table{number}.csv')
    display(HTML(table.map(lambda value: format_number(value, digits=5, target='html')).to_html(index=False, escape=False)))
    return table
"""),
        markdown("## Table 1. Sample filters\n\nRemoval counts follow the stated order; additional complete-case restrictions are shown explicitly."),
        code("display(pd.read_csv(OUTPUT_DIR / 'table1_universe.csv'))\ntable1 = show_table(1)"),
        markdown("## Table 2. Tone by report type\n\nProportional scores are percentages. Weighted scores are in equation (1) units. Annual and quarterly reports are reported separately."),
        code("table2 = show_table(2)"),
        markdown("## Table 3. Frequent dictionary words\n\nCounts pool the text sample. Each share is the word's count divided by all observed tokens in its dictionary category."),
        code("table3 = show_table(3)\nprint('Top-ten shares of category tokens (%):', audit['top10_shares'])"),
        markdown("## Negative sentiment and uncertainty correlations\n\nPearson correlations are reported for proportional and weighted scores in the full sample and by report type. Weighted scores are refitted within each reported sample."),
        code("display(HTML(pd.DataFrame(audit['correlations']).map(lambda value: format_number(value, digits=4, target='html')).to_html(index=False, escape=False)))"),
        markdown("## Filing example\n\nThe example selects the largest difference between the negative-tone and uncertainty percentile ranks. This is a descriptive contrast, not a randomly selected or representative report."),
        code("""example = audit['example']
display(Markdown(f"**{example['ticker']} · {example['form']} · {example['filing_date']}**"))
print(f"Negative words: {example['negative_pct']:.3f}%; uncertainty words: {example['uncertainty_pct']:.3f}%.")
print(f"Percentile ranks: negative {100*example['negative_percentile']:.1f}, uncertainty {100*example['uncertainty_percentile']:.1f}.")
display(Markdown('> ' + example['sentence'].replace('\\n', ' ')))
display(Markdown(f"[SEC filing]({example['doc_url']}) · Accession {example['accession']}"))
"""),
        markdown(r"""## Trend specifications

For each tone measure, quarter-level means estimate

$$\bar T_q=\alpha+\beta\tau_q+\sum_{s=2}^4\delta_sD_{sq}+\varepsilon_q.$$

Time $\tau_q$ is elapsed years from the first sample quarter; $\beta$ is annual change.
Ordinary OLS inference and heteroskedasticity/autocorrelation-consistent
inference with four quarterly lags are both reported.

The filing-level model is

$$T_{iq}=\alpha_i+\beta\tau_q+\sum_{s=2}^4\delta_sD_{sq}
+\theta K_{iq}+\varepsilon_{iq},$$

where $\alpha_i$ is a firm effect and $K$ is a 10-K indicator. This model
controls company mean levels and report type; entry and exit selection may remain. A saturated calendar-quarter effect
would absorb the linear trend and is therefore excluded. The 10-K indicator
is omitted in samples containing only one report type.

Firm-clustered and two-way firm/calendar-quarter clustered inference are
reported. Two-way p-values and intervals use $\min(G_{firm},G_{quarter})-1$
degrees of freedom. Non-estimable or nonpositive-variance cases are labelled
rather than assigned a p-value.
"""),
        markdown("## Table 4. Tone trends\n\nThe same specifications are estimated for the full sample, 10-Ks and 10-Qs. Separate report-type samples refit weighted scores on their own documents."),
        code("table4 = show_table(4)"),
        markdown("## Figure 1. Quarterly tone and VIX\n\nReport types are shown separately with within-form tf.idf. Company-centered means reduce baseline composition differences, but entry/exit timing can still affect this unbalanced panel. Formal inference relies on Table 4. Gray dashed lines show quarterly VIX on the right axes. The latest quarter is partial. Annual-report quarterly counts can be very small and are shown below."),
        code("display(Image(filename=str(OUTPUT_DIR / 'figure1.png')))\ndisplay(pd.DataFrame(audit['quarter_counts']).pivot(index='quarter', columns='form', values='n').fillna(0).astype(int))"),
        markdown(r"""## Outcome specifications

Define the common controls as

$$\begin{aligned}
C_{iq}={}&\gamma_1\ln(\mathrm{Size}_{iq})+\gamma_2\ln(\mathrm{DollarVolume}_{iq})\\
&+\gamma_3R^{\mathrm{pre,excess}}_{iq}+\theta K_{iq}.
\end{aligned}$$

For uncertainty $U$, the volatility model is

$$\sigma^{\mathrm{post}}_{iq}=\alpha_i+\lambda_q+\beta U_{iq}
+C_{iq}+[\rho\sigma^{\mathrm{pre}}_{iq}]+\varepsilon_{iq}.$$

Both proportional and weighted uncertainty are estimated with and without
the bracketed pre-filing volatility control, using exactly the same complete
observations within each comparison. $\lambda_q$ is a calendar-quarter effect.
Dollar volume and prior excess return use [−60,−6]; size uses the day −1 price
and shares printed on the scored filing.

For negative sentiment $N$, the filing-return model is

$$R^{[0,3],\mathrm{excess}}_{iq}=\alpha_i+\lambda_q+\beta N_{iq}
+C_{iq}+\rho\sigma^{\mathrm{pre}}_{iq}+\varepsilon_{iq}.$$

Both tone versions use firm and quarter effects, all listed controls, and the
same two clustering alternatives. No winsorisation is applied. Coefficients
are per one unit of the original score. One-standard-deviation effects aid
comparison. The approximate 80% minimum detectable effect for a two-sided 5% test,
expressed in return percentage points per one tone standard deviation, is

$$\mathrm{MDE}^{\mathrm{pp}}_{80,1\mathrm{SD}}
=100\left(t_{0.975,\nu}+\Phi^{-1}(0.8)\right)
\mathrm{SE}(\hat\beta)\,s_{\mathrm{tone}}.$$

Here $\nu$ is the inference degrees of freedom. Statistical insignificance does not establish
that the association is zero, and these associations are not causal effects.
"""),
        markdown("## Table 5. Uncertainty and post-filing volatility"),
        code("table5 = show_table(5)"),
        markdown("## Table 6. Negative sentiment and filing-period excess return"),
        code("table6 = show_table(6)"),
        markdown("""## Course-period comparison: 2021–2025

The requested course window is retained alongside the expanded filing window.
Both periods use the same current active dictionary and sample definitions.
The comparison therefore separates the date coverage from dictionary choices.
[Course-period report](COURSE_REPORT.md) · [Course-period PDF](outputs/course_2021_2025/ARK_Holdings_Sentiment_and_Uncertainty_Report_2025-12-31.pdf).
"""),
        code("""course_audit = json.loads((OUTPUT_DIR / 'course_2021_2025' / 'audit.json').read_text())
comparison = pd.DataFrame([
    {'Filing period': 'Expanded', 'Start': audit['sample_start'], 'End': audit['sample_end'],
     'Text filings': audit['final_filings'], 'Volatility filings': audit['volatility_filings'], 'Return filings': audit['return_filings']},
    {'Filing period': 'Course', 'Start': course_audit['sample_start'], 'End': course_audit['sample_end'],
     'Text filings': course_audit['final_filings'], 'Volatility filings': course_audit['volatility_filings'], 'Return filings': course_audit['return_filings']}
])
display(comparison)
"""),
        markdown("""## AI assistance

OpenAI Codex generated analysis code, tests and notebook text and assisted with
data acquisition and execution. Numerical outputs are produced by running the
analysis on the acquired corpus; they are not supplied as invented examples.
This statement does not imply that the student independently wrote or reviewed
the generated code. The accompanying AI-use disclosure records the assistance.
"""),
    ]
    return nbformat.v4.new_notebook(cells=cells, metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-execute', action='store_true', help='Write source cells without outputs')
    parser.add_argument('--timeout', type=int, default=3600, help='Per-cell execution limit in seconds')
    args = parser.parse_args()
    notebook = build_notebook()
    nbformat.validate(notebook)
    if not args.no_execute:
        kernel_root = ROOT / 'data' / 'runtime_jupyter'
        kernel_dir = kernel_root / 'kernels' / 'assignment'
        kernel_dir.mkdir(parents=True, exist_ok=True)
        (kernel_dir / 'kernel.json').write_text(json.dumps({'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'], 'display_name': 'Assignment Python', 'language': 'python'}))
        os.environ['JUPYTER_PATH'] = str(kernel_root) + os.pathsep + os.environ.get('JUPYTER_PATH', '')
        NotebookClient(notebook, timeout=args.timeout, kernel_name='assignment',
                       resources={'metadata': {'path': str(ROOT)}},
                       allow_errors=False).execute()
    output = ROOT / 'analysis.ipynb'
    nbformat.write(notebook, output)
    print(f"{'Unexecuted' if args.no_execute else 'Executed'} notebook saved: {output}")


if __name__ == '__main__':
    main()
